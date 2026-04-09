<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { api } from '$lib/api/rest';
	import { SimWebSocket, type WSMessage, type TickMessage } from '$lib/api/websocket';
	import {
		runId,
		tick,
		agents,
		matrixState,
		factions as factionsStore,
		loadFullState,
		applyTickMessage,
		isRunning
	} from '$lib/stores/simulation';
	import {
		zoomLevel,
		terminalOpen,
		mousePosition,
		bondConstellationMode,
		toggleOverlay,
		focusCell,
		focusAgentId,
		autoSpeed
	} from '$lib/stores/ui';

	import CodeRain from '$lib/canvas/CodeRain.svelte';
	import WorldMap from '$lib/canvas/WorldMap.svelte';
	import CellView from '$lib/canvas/CellView.svelte';
	import SoulView from '$lib/canvas/SoulView.svelte';
	import EdgePanels from '$lib/panels/EdgePanels.svelte';
	import Terminal from '$lib/terminal/Terminal.svelte';
	import ControlDrawer from '$lib/panels/ControlDrawer.svelte';
	import ChartsPanel from '$lib/panels/ChartsPanel.svelte';
	import EraBanner from '$lib/panels/EraBanner.svelte';

	let ws: SimWebSocket | null = null;
	let showLanding = $state(true);
	let eras = $state<any[]>([]);
	let scenarios = $state<any[]>([]);
	let runs = $state<any[]>([]);
	let selectedEra = $state('');
	let selectedScenario = $state('');
	let creating = $state(false);
	let controlDrawerOpen = $state(false);
	let chartsPanelOpen = $state(false);

	async function loadMeta() {
		try {
			const [eraData, scenarioData, runData] = await Promise.all([
				api.listEras(),
				api.listScenarios(),
				api.listRuns()
			]);
			eras = eraData.eras || [];
			scenarios = scenarioData.scenarios || [];
			runs = runData.runs || [];
		} catch (e) {
			console.error('Failed to connect to backend:', e);
		}
	}

	async function createSim() {
		creating = true;
		try {
			const result = await api.createSim(
				selectedEra || undefined,
				selectedScenario || undefined
			);
			await connectToSim(result.run_id);
		} catch (e: any) {
			console.error('Failed to create simulation:', e);
			alert(`Failed: ${e.message}`);
		}
		creating = false;
	}

	async function loadSim(rid: string) {
		await connectToSim(rid);
	}

	async function connectToSim(rid: string) {
		runId.set(rid);

		// Load full state
		const state = await api.getState(rid);
		loadFullState(state);

		// Connect WebSocket
		ws = new SimWebSocket(rid);
		await ws.connect();
		ws.onMessage(handleWSMessage);
		showLanding = false;

		// Request initial state sync
		ws.requestState();
	}

	function handleWSMessage(msg: WSMessage) {
		if (msg.type === 'tick') {
			applyTickMessage(msg as TickMessage);
		} else if (msg.type === 'state_sync') {
			// Full state sync
			const agentMap = new Map();
			for (const a of msg.agents || []) {
				agentMap.set(a.id, a);
			}
			agents.set(agentMap);
			tick.set(msg.tick);
			if (msg.matrix) {
				matrixState.set(msg.matrix);
			}
			if (msg.factions) {
				factionsStore.set(msg.factions);
			}
		} else if (msg.type === 'stopped') {
			isRunning.set(false);
		} else if (msg.type === 'auto_started') {
			isRunning.set(true);
		} else if (msg.type === 'extinction') {
			isRunning.set(false);
		}
	}

	function doTick(count = 1) {
		ws?.requestTick(count);
	}

	function toggleAutoRun() {
		if ($isRunning) {
			ws?.stop();
			isRunning.set(false);
		} else {
			ws?.startAuto($autoSpeed);
			isRunning.set(true);
		}
	}

	function handleWheel(e: WheelEvent) {
		if ($terminalOpen) return;

		const current = $zoomLevel;
		if (e.deltaY > 0) {
			// Zoom in
			if (current === 0) zoomLevel.set(1);
			// Level 1→2 and 2→3 require clicking a cell/agent
		} else {
			// Zoom out
			if (current === 3) {
				focusAgentId.set(null);
				if ($focusCell) zoomLevel.set(2);
				else zoomLevel.set(1);
			} else if (current === 2) {
				focusCell.set(null);
				zoomLevel.set(1);
			} else if (current === 1) {
				zoomLevel.set(0);
			}
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		// Backtick toggles terminal
		if (e.key === '`') {
			e.preventDefault();
			terminalOpen.update((v) => !v);
			return;
		}

		if ($terminalOpen) return;

		// ESC to zoom out
		if (e.key === 'Escape') {
			const current = $zoomLevel;
			if (current === 3) {
				focusAgentId.set(null);
				zoomLevel.set($focusCell ? 2 : 1);
			} else if (current === 2) {
				focusCell.set(null);
				zoomLevel.set(1);
			} else if (current === 1) {
				zoomLevel.set(0);
			}
			return;
		}

		// Space = tick
		if (e.key === ' ' && !showLanding) {
			e.preventDefault();
			doTick(1);
			return;
		}

		// P = play/pause
		if (e.key === 'p' || e.key === 'P') {
			toggleAutoRun();
			return;
		}

		// B = bond constellation
		if (e.key === 'b' || e.key === 'B') {
			bondConstellationMode.update((v) => !v);
			return;
		}

		// Number keys for overlays
		const overlayKeys: Record<string, string> = {
			'1': 'emotions',
			'2': 'awareness',
			'3': 'wealth',
			'4': 'beliefs',
			'5': 'factions',
			'6': 'info_flow',
			'7': 'combat',
			'8': 'resources',
			'9': 'bond_density'
		};
		if (e.key in overlayKeys) {
			toggleOverlay(overlayKeys[e.key]);
			return;
		}
	}

	function handleMouseMove(e: MouseEvent) {
		mousePosition.set({ x: e.clientX, y: e.clientY });
	}

	onMount(() => {
		loadMeta();
	});

	onDestroy(() => {
		ws?.disconnect();
	});
</script>

<svelte:window onkeydown={handleKeydown} onwheel={handleWheel} onmousemove={handleMouseMove} />

{#if showLanding}
	<!-- Landing Screen -->
	<div class="landing matrix-texture">
		<div class="landing-content">
			<h1 class="title">THE NEXUS</h1>
			<p class="subtitle">Cognitive Matrix Civilization Simulator</p>

			<div class="landing-sections">
				<!-- New Simulation -->
				<div class="landing-section">
					<h2>NEW SIMULATION</h2>
					<div class="form-group">
						<label for="era-select">ERA</label>
						<select id="era-select" bind:value={selectedEra}>
							<option value="">Default</option>
							{#each eras as era}
								<option value={era.name}>{era.display_name || era.name}</option>
							{/each}
						</select>
					</div>
					<div class="form-group">
						<label for="scenario-select">SCENARIO</label>
						<select id="scenario-select" bind:value={selectedScenario}>
							<option value="">Default</option>
							{#each scenarios as s}
								<option value={s.name}>{s.name}</option>
							{/each}
						</select>
					</div>
					<button class="btn-primary" onclick={createSim} disabled={creating}>
						{creating ? 'INITIALIZING...' : 'ENTER THE MATRIX'}
					</button>
				</div>

				<!-- Load Existing -->
				{#if runs.length > 0}
					<div class="landing-section">
						<h2>LOAD SIMULATION</h2>
						<div class="runs-list">
							{#each runs.slice(0, 8) as run}
								<button class="run-item" onclick={() => loadSim(run.run_id)}>
									<span class="run-id">{run.run_id}</span>
									<span class="run-tick">tick {run.latest_tick}</span>
									<span class="run-date">{run.created_at?.slice(0, 10)}</span>
								</button>
							{/each}
						</div>
					</div>
				{/if}
			</div>

			<div class="landing-hint">
				Press <kbd>`</kbd> for terminal | <kbd>SPACE</kbd> to tick | <kbd>P</kbd> play/pause | Scroll to zoom
			</div>
		</div>
	</div>
{:else}
	<!-- Main Simulation View -->
	<CodeRain />
	<WorldMap />
	<CellView />
	<SoulView />
	<EdgePanels />
	<Terminal />
	<ControlDrawer bind:open={controlDrawerOpen} />
	<ChartsPanel bind:open={chartsPanelOpen} />
	<EraBanner />

	<!-- Floating Controls -->
	<div class="controls">
		<button class="ctrl-btn" onclick={() => controlDrawerOpen = !controlDrawerOpen} title="Architect Controls (Tune, God Mode, Whisper)">
			&#9881;
		</button>
		<button class="ctrl-btn" onclick={() => chartsPanelOpen = !chartsPanelOpen} title="Analytics & Charts">
			&#9776;
		</button>
		<span class="ctrl-sep"></span>
		<button class="ctrl-btn" onclick={() => doTick(1)} title="Advance 1 tick (Space)">&#9654; 1</button>
		<button class="ctrl-btn" onclick={() => doTick(10)} title="Advance 10 ticks">&#9654; 10</button>
		<button class="ctrl-btn" onclick={() => doTick(50)} title="Advance 50 ticks">&#9654; 50</button>
		<button class="ctrl-btn" class:active={$isRunning} onclick={toggleAutoRun} title="Auto-run (P)">
			{$isRunning ? '&#9646;&#9646;' : '&#9654;&#9654;'}
		</button>
		<input
			type="range"
			min="50"
			max="1000"
			step="50"
			bind:value={$autoSpeed}
			class="speed-slider"
			title="Speed: {$autoSpeed}ms/tick"
		/>
		<span class="tick-display">t={$tick}</span>
	</div>

	<!-- Zoom level indicator -->
	<div class="zoom-indicator">
		<button class:active={$zoomLevel === 0} onclick={() => zoomLevel.set(0)}>RAIN</button>
		<button class:active={$zoomLevel === 1} onclick={() => zoomLevel.set(1)}>GRID</button>
		<button class:active={$zoomLevel === 2} class:disabled={!$focusCell} onclick={() => {
			if (!$focusCell) {
				// Default to center cell
				focusCell.set({ row: 3, col: 3 });
			}
			zoomLevel.set(2);
		}}>CELL</button>
		<button class:active={$zoomLevel === 3} class:disabled={!$focusAgentId} onclick={() => {
			if (!$focusAgentId) {
				// Pick the first available agent
				const firstAgent = Array.from($agents.values())[0];
				if (firstAgent) {
					const row = Math.min(7, Math.floor(firstAgent.y * 8));
					const col = Math.min(7, Math.floor(firstAgent.x * 8));
					focusCell.set({ row, col });
					focusAgentId.set(firstAgent.id);
				}
			}
			zoomLevel.set(3);
		}}>SOUL</button>
	</div>
{/if}

<style>
	/* Landing */
	.landing {
		position: fixed;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--bg-primary);
		z-index: 50;
	}
	.landing-content {
		text-align: center;
		max-width: 800px;
		padding: 40px;
		position: relative;
		z-index: 1;
	}
	.title {
		font-size: 48px;
		font-weight: 300;
		letter-spacing: 12px;
		color: var(--green-primary);
		margin-bottom: 8px;
		text-shadow: 0 0 30px rgba(0, 255, 136, 0.3);
	}
	.subtitle {
		font-size: 13px;
		color: var(--text-dim);
		letter-spacing: 4px;
		margin-bottom: 40px;
	}
	.landing-sections {
		display: flex;
		gap: 40px;
		justify-content: center;
		flex-wrap: wrap;
	}
	.landing-section {
		text-align: left;
		min-width: 280px;
	}
	.landing-section h2 {
		font-size: 11px;
		letter-spacing: 3px;
		color: var(--text-dim);
		margin-bottom: 16px;
		border-bottom: 1px solid var(--green-dim);
		padding-bottom: 6px;
	}
	.form-group {
		margin-bottom: 12px;
	}
	.form-group label {
		display: block;
		font-size: 10px;
		color: var(--text-dim);
		letter-spacing: 2px;
		margin-bottom: 4px;
	}
	select {
		width: 100%;
		background: var(--bg-secondary);
		border: 1px solid var(--green-dim);
		color: var(--green-primary);
		font-family: var(--font-mono);
		font-size: 12px;
		padding: 8px 10px;
		cursor: pointer;
	}
	select:focus {
		outline: none;
		border-color: var(--green-primary);
	}
	option { background: var(--bg-secondary); }

	.btn-primary {
		width: 100%;
		padding: 12px;
		background: var(--green-dim);
		border: 1px solid var(--green-primary);
		color: var(--green-primary);
		font-family: var(--font-mono);
		font-size: 13px;
		letter-spacing: 2px;
		cursor: pointer;
		margin-top: 8px;
		transition: all var(--transition-fast);
	}
	.btn-primary:hover {
		background: var(--green-primary);
		color: var(--bg-primary);
	}
	.btn-primary:disabled {
		opacity: 0.5;
		cursor: wait;
	}

	.runs-list {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.run-item {
		display: flex;
		gap: 12px;
		padding: 8px 10px;
		background: var(--bg-secondary);
		border: 1px solid var(--green-dim);
		color: var(--green-primary);
		font-family: var(--font-mono);
		font-size: 11px;
		cursor: pointer;
		text-align: left;
	}
	.run-item:hover { border-color: var(--green-primary); background: var(--green-dim); }
	.run-id { flex: 1; }
	.run-tick { color: var(--cyan); }
	.run-date { color: var(--text-dim); }

	.landing-hint {
		margin-top: 40px;
		font-size: 11px;
		color: var(--text-muted);
	}
	kbd {
		padding: 2px 6px;
		background: var(--bg-secondary);
		border: 1px solid var(--green-dim);
		border-radius: 3px;
		font-size: 10px;
	}

	/* Floating Controls */
	.controls {
		position: fixed;
		bottom: 20px;
		right: 20px;
		display: flex;
		align-items: center;
		gap: 6px;
		background: var(--bg-panel);
		border: 1px solid rgba(0, 255, 136, 0.15);
		border-radius: 6px;
		padding: 6px 10px;
		z-index: 20;
		backdrop-filter: blur(8px);
	}
	.ctrl-btn {
		background: var(--bg-secondary);
		border: 1px solid var(--green-dim);
		color: var(--green-primary);
		font-family: var(--font-mono);
		font-size: 11px;
		padding: 4px 10px;
		cursor: pointer;
		border-radius: 3px;
	}
	.ctrl-btn:hover { border-color: var(--green-primary); }
	.ctrl-btn.active {
		background: var(--green-dim);
		border-color: var(--green-primary);
	}
	.ctrl-sep {
		width: 1px;
		height: 18px;
		background: var(--green-dim);
		margin: 0 2px;
	}
	.speed-slider {
		width: 80px;
		accent-color: var(--green-primary);
		cursor: pointer;
	}
	.tick-display {
		font-size: 11px;
		color: var(--text-dim);
		min-width: 60px;
		text-align: right;
	}

	/* Zoom indicator */
	.zoom-indicator {
		position: fixed;
		top: 20px;
		right: 20px;
		display: flex;
		gap: 2px;
		z-index: 20;
	}
	.zoom-indicator button {
		background: var(--bg-panel);
		border: 1px solid rgba(0, 255, 136, 0.1);
		color: var(--text-dim);
		font-family: var(--font-mono);
		font-size: 11px;
		letter-spacing: 1px;
		padding: 6px 12px;
		cursor: pointer;
		white-space: nowrap;
	}
	.zoom-indicator button.active {
		color: var(--green-primary);
		border-color: var(--green-primary);
		background: var(--green-dim);
	}
	.zoom-indicator button:hover { color: var(--green-primary); }
	.zoom-indicator button.disabled { opacity: 0.4; }
	.zoom-indicator button.disabled:hover { opacity: 0.7; }
</style>
