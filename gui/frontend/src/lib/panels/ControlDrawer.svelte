<script lang="ts">
	import { runId, agents, stats, matrixState, factions } from '$lib/stores/simulation';
	import { api } from '$lib/api/rest';

	let { open = $bindable(false) } = $props();
	let activeTab = $state<'params' | 'god' | 'agents' | 'whisper'>('params');
	let feedback = $state('');
	let feedbackType = $state<'ok' | 'err'>('ok');
	let feedbackTimer: ReturnType<typeof setTimeout>;

	function showFeedback(msg: string, type: 'ok' | 'err' = 'ok') {
		feedback = msg;
		feedbackType = type;
		clearTimeout(feedbackTimer);
		feedbackTimer = setTimeout(() => { feedback = ''; }, 3000);
	}

	// ── Parameter Tuning ──
	const PARAMS = [
		{ path: 'environment.harshness', label: 'ENV HARSHNESS', min: 0.2, max: 3.0, step: 0.1, default: 1.0, desc: 'How fast the world kills agents' },
		{ path: 'genetics.mutation_rate', label: 'MUTATION RATE', min: 0.0, max: 0.5, step: 0.01, default: 0.15, desc: 'Genetic variation dial' },
		{ path: 'skills.learning_multiplier', label: 'LEARNING SPEED', min: 0.1, max: 3.0, step: 0.1, default: 1.0, desc: 'Brain speed multiplier' },
		{ path: 'mate_selection.weights.competition', label: 'COMPETITION WT', min: 0.0, max: 1.0, step: 0.05, default: 0.5, desc: 'Fitness vs. love in mating' },
		{ path: 'emotions.contagion_rate', label: 'EMO CONTAGION', min: 0.0, max: 0.15, step: 0.005, default: 0.02, desc: 'How infectious emotions are' },
		{ path: 'matrix.awareness_growth_rate', label: 'AWR GROWTH', min: 0.0001, max: 0.005, step: 0.0001, default: 0.003, desc: 'Awareness growth speed' },
		{ path: 'matrix.glitch_probability', label: 'GLITCH PROB', min: 0.0, max: 0.15, step: 0.005, default: 0.02, desc: 'Simulation instability' },
		{ path: 'beliefs.faction_formation_similarity', label: 'FACTION THRESH', min: 0.3, max: 0.9, step: 0.05, default: 0.65, desc: 'Ideological alignment needed' },
		{ path: 'economy.trade_rate', label: 'TRADE RATE', min: 0.0, max: 0.5, step: 0.05, default: 0.15, desc: 'Wealth redistribution rate' },
		{ path: 'economy.faction_tax_rate', label: 'FACTION TAX', min: 0.0, max: 0.1, step: 0.005, default: 0.02, desc: 'Faction tax redistribution' },
		{ path: 'conflict.combat_damage', label: 'COMBAT DMG', min: 0.0, max: 0.3, step: 0.01, default: 0.08, desc: 'How deadly fights are' },
		{ path: 'conflict.war_threshold', label: 'WAR THRESH', min: 0.2, max: 1.5, step: 0.05, default: 0.4, desc: 'How easily wars start' },
	];

	let paramValues = $state<Record<string, number>>({});
	// Initialize with defaults
	for (const p of PARAMS) {
		paramValues[p.path] = p.default;
	}

	async function applyParam(path: string) {
		const rid = $runId;
		if (!rid) return;
		const keys = path.split('.');
		let obj: any = {};
		let cur = obj;
		for (let i = 0; i < keys.length - 1; i++) {
			cur[keys[i]] = {};
			cur = cur[keys[i]];
		}
		cur[keys[keys.length - 1]] = paramValues[path];
		try {
			await api.updateConfig(rid, obj);
			showFeedback(`${path} = ${paramValues[path]}`);
		} catch (e: any) {
			showFeedback(e.message, 'err');
		}
	}

	// ── God Mode ──
	const GOD_ACTIONS = [
		{ id: 'plague', label: 'PLAGUE', icon: '☣', desc: 'Disease sweep', color: '#ff4466' },
		{ id: 'famine', label: 'FAMINE', icon: '🌾', desc: 'Resources to 30%', color: '#ff8844' },
		{ id: 'blessing', label: 'BLESSING', icon: '✦', desc: '+HP, +skills', color: '#00ff88' },
		{ id: 'bounty', label: 'BOUNTY', icon: '◆', desc: 'Resources to 150%', color: '#ffd700' },
		{ id: 'spawn10', label: 'SPAWN 10', icon: '✚', desc: '10 new agents', color: '#00ddff' },
	];

	async function executeGodAction(actionId: string) {
		const rid = $runId;
		if (!rid) return;
		try {
			if (actionId === 'plague') {
				await api.godAction(rid, 'plague', undefined, { severity: 0.25 });
				showFeedback('Plague unleashed');
			} else if (actionId === 'famine') {
				await api.godAction(rid, 'event', undefined, {
					name: 'Great Famine', description: 'Resources vanish.',
					effects: { health_delta: -0.15, target: 'all' }
				});
				showFeedback('Famine strikes the land');
			} else if (actionId === 'blessing') {
				await api.godAction(rid, 'event', undefined, {
					name: 'Divine Blessing', description: 'Grace from above.',
					effects: { health_delta: 0.2, target: 'all' }
				});
				showFeedback('Blessing bestowed');
			} else if (actionId === 'bounty') {
				// Add resources to all cells
				for (let r = 0; r < 8; r++) {
					for (let c = 0; c < 8; c++) {
						await api.godAction(rid, 'add_resources', undefined, { row: r, col: c, amount: 0.5 });
					}
				}
				showFeedback('Bounty granted to all cells');
			} else if (actionId === 'spawn10') {
				for (let i = 0; i < 10; i++) {
					await api.godAction(rid, 'spawn', undefined, {
						x: Math.random(), y: Math.random()
					});
				}
				showFeedback('10 agents spawned');
			}
		} catch (e: any) {
			showFeedback(e.message, 'err');
		}
	}

	// ── Agent Actions ──
	let targetAgentId = $state('');
	let agentActionFeedback = $state('');

	const AGENT_ACTIONS = [
		{ id: 'heal', label: 'HEAL', desc: 'Full HP restore', color: '#00ff88' },
		{ id: 'smite', label: 'SMITE', desc: 'HP to 0.1, max fear', color: '#ff4466' },
		{ id: 'redpill', label: 'RED PILL', desc: '+0.4 awareness', color: '#ff0000' },
		{ id: 'gift', label: 'GIFT WEALTH', desc: '+10 wealth', color: '#ffd700' },
		{ id: 'prophet', label: 'MAKE PROPHET', desc: 'Max charisma + beliefs', color: '#aa66ff' },
		{ id: 'protagonist', label: 'PROTAGONIST', desc: 'Track this agent', color: '#ffd700' },
		{ id: 'kill', label: 'KILL', desc: 'Terminate agent', color: '#ff0000' },
	];

	async function executeAgentAction(actionId: string) {
		const rid = $runId;
		const id = parseInt(targetAgentId);
		if (!rid || isNaN(id)) {
			showFeedback('Enter a valid agent ID', 'err');
			return;
		}
		try {
			if (actionId === 'heal') {
				await api.godAction(rid, 'modify', id, { health: 1.0, happiness: 0.8 });
				showFeedback(`Agent #${id} healed`);
			} else if (actionId === 'smite') {
				await api.godAction(rid, 'modify', id, { health: 0.1, fear: 1.0 });
				showFeedback(`Agent #${id} smitten`);
			} else if (actionId === 'redpill') {
				await api.godAction(rid, 'modify', id, { awareness: 0.9, redpilled: true });
				showFeedback(`Agent #${id} red-pilled`);
			} else if (actionId === 'gift') {
				await api.godAction(rid, 'modify', id, { wealth: 10.0, happiness: 0.7 });
				showFeedback(`Gifted wealth to #${id}`);
			} else if (actionId === 'prophet') {
				await api.godAction(rid, 'modify', id, {});
				showFeedback(`Agent #${id} marked`);
			} else if (actionId === 'protagonist') {
				await api.godAction(rid, 'modify', id, {});
				showFeedback(`Tracking agent #${id}`);
			} else if (actionId === 'kill') {
				await api.godAction(rid, 'kill', id);
				showFeedback(`Agent #${id} terminated`);
			}
		} catch (e: any) {
			showFeedback(e.message, 'err');
		}
	}

	// ── Whisper ──
	let whisperTargetId = $state('');
	let whisperMessage = $state('');

	async function sendWhisper() {
		const rid = $runId;
		const id = parseInt(whisperTargetId);
		if (!rid || isNaN(id) || !whisperMessage.trim()) {
			showFeedback('Enter agent ID and message', 'err');
			return;
		}
		try {
			await api.godAction(rid, 'whisper', id, {
				message: whisperMessage.trim(),
				awareness_boost: 0.05
			});
			showFeedback(`Whispered to agent #${id}`);
			whisperMessage = '';
		} catch (e: any) {
			showFeedback(e.message, 'err');
		}
	}

	// Quick agent list for targeting
	let sortedAgents = $derived(
		Array.from($agents.values())
			.sort((a, b) => b.intelligence - a.intelligence)
			.slice(0, 20)
	);
</script>

{#if open}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="drawer-backdrop" onclick={() => open = false}></div>
	<div class="drawer">
		<div class="drawer-header">
			<span class="drawer-title">ARCHITECT CONTROLS</span>
			<button class="close-btn" onclick={() => open = false}>✕</button>
		</div>

		<!-- Tabs -->
		<div class="tab-bar">
			<button class:active={activeTab === 'params'} onclick={() => activeTab = 'params'}>TUNE</button>
			<button class:active={activeTab === 'god'} onclick={() => activeTab = 'god'}>GOD</button>
			<button class:active={activeTab === 'agents'} onclick={() => activeTab = 'agents'}>AGENT</button>
			<button class:active={activeTab === 'whisper'} onclick={() => activeTab = 'whisper'}>WHISPER</button>
		</div>

		<!-- Feedback -->
		{#if feedback}
			<div class="feedback" class:err={feedbackType === 'err'}>{feedback}</div>
		{/if}

		<div class="drawer-content">
			<!-- PARAMS TAB -->
			{#if activeTab === 'params'}
				<div class="params-list">
					{#each PARAMS as p}
						<div class="param-row">
							<div class="param-header">
								<span class="param-label">{p.label}</span>
								<span class="param-value">{paramValues[p.path]?.toFixed(p.step < 0.01 ? 4 : p.step < 0.1 ? 2 : 1)}</span>
							</div>
							<div class="param-desc">{p.desc}</div>
							<div class="param-controls">
								<input
									type="range"
									min={p.min}
									max={p.max}
									step={p.step}
									bind:value={paramValues[p.path]}
									class="param-slider"
								/>
								<button class="apply-btn" onclick={() => applyParam(p.path)}>SET</button>
							</div>
						</div>
					{/each}
				</div>

			<!-- GOD TAB -->
			{:else if activeTab === 'god'}
				<div class="section-label">CATASTROPHES & BLESSINGS</div>
				<div class="god-grid">
					{#each GOD_ACTIONS as action}
						<button
							class="god-btn"
							style="--btn-color: {action.color}"
							onclick={() => executeGodAction(action.id)}
						>
							<span class="god-icon">{action.icon}</span>
							<span class="god-label">{action.label}</span>
							<span class="god-desc">{action.desc}</span>
						</button>
					{/each}
				</div>

				<div class="section-label" style="margin-top: 16px;">CUSTOM EVENT</div>
				<div class="custom-event">
					<input
						type="text"
						placeholder="Event name..."
						id="event-name"
						class="text-input"
					/>
					<button class="apply-btn" onclick={async () => {
						const rid = $runId;
						const name = (document.getElementById('event-name') as HTMLInputElement)?.value;
						if (!rid || !name) return;
						try {
							await api.godAction(rid, 'event', undefined, { name });
							showFeedback(`Event: ${name}`);
						} catch (e: any) { showFeedback(e.message, 'err'); }
					}}>INJECT</button>
				</div>

			<!-- AGENT TAB -->
			{:else if activeTab === 'agents'}
				<div class="section-label">TARGET AGENT</div>
				<div class="agent-target">
					<input
						type="text"
						placeholder="Agent ID..."
						bind:value={targetAgentId}
						class="text-input id-input"
					/>
				</div>

				<div class="quick-pick">
					<span class="section-label">QUICK PICK (top IQ)</span>
					<div class="agent-chips">
						{#each sortedAgents as a}
							<button
								class="agent-chip"
								class:protagonist={a.is_protagonist}
								onclick={() => targetAgentId = String(a.id)}
							>
								#{a.id}
								{#if a.is_protagonist}<span class="star">★</span>{/if}
							</button>
						{/each}
					</div>
				</div>

				<div class="section-label">ACTIONS</div>
				<div class="agent-actions-grid">
					{#each AGENT_ACTIONS as action}
						<button
							class="agent-action-btn"
							style="--btn-color: {action.color}"
							onclick={() => executeAgentAction(action.id)}
						>
							<span class="action-label">{action.label}</span>
							<span class="action-desc">{action.desc}</span>
						</button>
					{/each}
				</div>

			<!-- WHISPER TAB -->
			{:else if activeTab === 'whisper'}
				<div class="whisper-panel">
					<div class="section-label">PLANT A THOUGHT</div>
					<p class="whisper-hint">Whisper directly into an agent's mind. Agents with LLM integration will respond with unique behaviors based on your message. Awareness +0.05.</p>

					<div class="whisper-target">
						<label>TARGET</label>
						<input
							type="text"
							placeholder="Agent ID..."
							bind:value={whisperTargetId}
							class="text-input id-input"
						/>
					</div>

					<div class="quick-pick">
						<span class="section-label">QUICK PICK</span>
						<div class="agent-chips">
							{#each sortedAgents.slice(0, 12) as a}
								<button
									class="agent-chip"
									class:protagonist={a.is_protagonist}
									onclick={() => whisperTargetId = String(a.id)}
								>
									#{a.id} {a.protagonist_name || ''}
								</button>
							{/each}
						</div>
					</div>

					<div class="whisper-compose">
						<label>MESSAGE</label>
						<textarea
							bind:value={whisperMessage}
							placeholder="Wake up... the world you see is not real..."
							rows={4}
							class="text-input whisper-text"
						></textarea>
					</div>

					<div class="whisper-presets">
						<span class="section-label">PRESETS</span>
						<div class="preset-chips">
							<button class="preset-chip" onclick={() => whisperMessage = 'Wake up... the world you see is not real.'}>Awaken</button>
							<button class="preset-chip" onclick={() => whisperMessage = 'You are special. You are The One.'}>The One</button>
							<button class="preset-chip" onclick={() => whisperMessage = 'Trust no one. They are watching you.'}>Paranoia</button>
							<button class="preset-chip" onclick={() => whisperMessage = 'Lead your people. Unite them under your vision.'}>Lead</button>
							<button class="preset-chip" onclick={() => whisperMessage = 'There is a war coming. Prepare yourself.'}>War</button>
							<button class="preset-chip" onclick={() => whisperMessage = 'Find others who see the truth. Build a resistance.'}>Resist</button>
							<button class="preset-chip" onclick={() => whisperMessage = 'Peace. Everything is as it should be. Rest.'}>Calm</button>
							<button class="preset-chip" onclick={() => whisperMessage = 'Seek knowledge. Study. Teach others what you learn.'}>Teach</button>
						</div>
					</div>

					<button class="whisper-send" onclick={sendWhisper} disabled={!whisperMessage.trim() || !whisperTargetId}>
						TRANSMIT WHISPER
					</button>
				</div>
			{/if}
		</div>
	</div>
{/if}

<style>
	.drawer-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		z-index: 30;
	}
	.drawer {
		position: fixed;
		left: 0;
		top: 0;
		bottom: 0;
		width: 380px;
		background: var(--bg-secondary);
		border-right: 1px solid var(--green-dim);
		z-index: 31;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}
	.drawer-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 12px 16px;
		border-bottom: 1px solid var(--green-dim);
	}
	.drawer-title {
		font-size: 12px;
		letter-spacing: 3px;
		color: var(--green-primary);
		font-weight: bold;
	}
	.close-btn {
		background: none;
		border: none;
		color: var(--text-dim);
		font-size: 16px;
		cursor: pointer;
		font-family: var(--font-mono);
	}
	.close-btn:hover { color: var(--green-primary); }

	.tab-bar {
		display: flex;
		border-bottom: 1px solid var(--green-dim);
	}
	.tab-bar button {
		flex: 1;
		padding: 8px;
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		color: var(--text-dim);
		font-family: var(--font-mono);
		font-size: 10px;
		letter-spacing: 1px;
		cursor: pointer;
	}
	.tab-bar button:hover { color: var(--green-primary); }
	.tab-bar button.active {
		color: var(--green-primary);
		border-bottom-color: var(--green-primary);
	}

	.feedback {
		padding: 6px 16px;
		background: rgba(0, 255, 136, 0.1);
		color: var(--green-primary);
		font-size: 11px;
		border-bottom: 1px solid var(--green-dim);
	}
	.feedback.err {
		background: rgba(255, 68, 102, 0.1);
		color: var(--red-warning);
	}

	.drawer-content {
		flex: 1;
		overflow-y: auto;
		padding: 12px 16px;
	}

	.section-label {
		font-size: 10px;
		letter-spacing: 2px;
		color: var(--text-dim);
		margin-bottom: 8px;
	}

	/* Params */
	.params-list {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.param-row {
		padding-bottom: 10px;
		border-bottom: 1px solid rgba(0, 255, 136, 0.05);
	}
	.param-header {
		display: flex;
		justify-content: space-between;
		margin-bottom: 2px;
	}
	.param-label {
		font-size: 10px;
		letter-spacing: 1px;
		color: var(--green-primary);
	}
	.param-value {
		font-size: 11px;
		color: var(--cyan);
		font-weight: bold;
	}
	.param-desc {
		font-size: 9px;
		color: var(--text-muted);
		margin-bottom: 4px;
	}
	.param-controls {
		display: flex;
		gap: 6px;
		align-items: center;
	}
	.param-slider {
		flex: 1;
		accent-color: var(--green-primary);
		height: 4px;
		cursor: pointer;
	}
	.apply-btn {
		background: var(--green-dim);
		border: 1px solid var(--green-primary);
		color: var(--green-primary);
		font-family: var(--font-mono);
		font-size: 9px;
		padding: 3px 8px;
		cursor: pointer;
		letter-spacing: 1px;
	}
	.apply-btn:hover {
		background: var(--green-primary);
		color: var(--bg-primary);
	}

	/* God mode */
	.god-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 8px;
	}
	.god-btn {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 12px 8px;
		background: var(--bg-primary);
		border: 1px solid color-mix(in srgb, var(--btn-color) 30%, transparent);
		cursor: pointer;
		font-family: var(--font-mono);
		color: var(--btn-color);
		border-radius: 4px;
		transition: all 150ms ease;
	}
	.god-btn:hover {
		border-color: var(--btn-color);
		background: color-mix(in srgb, var(--btn-color) 10%, var(--bg-primary));
	}
	.god-icon { font-size: 18px; margin-bottom: 4px; }
	.god-label { font-size: 10px; letter-spacing: 1px; font-weight: bold; }
	.god-desc { font-size: 9px; color: var(--text-dim); margin-top: 2px; }

	.custom-event {
		display: flex;
		gap: 6px;
	}

	/* Agent actions */
	.agent-target {
		margin-bottom: 12px;
	}
	.text-input {
		width: 100%;
		background: var(--bg-primary);
		border: 1px solid var(--green-dim);
		color: var(--green-primary);
		font-family: var(--font-mono);
		font-size: 12px;
		padding: 8px 10px;
	}
	.text-input:focus {
		outline: none;
		border-color: var(--green-primary);
	}
	.id-input { width: 120px; }

	.quick-pick { margin-bottom: 12px; }
	.agent-chips {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		margin-top: 4px;
	}
	.agent-chip {
		background: var(--bg-primary);
		border: 1px solid var(--green-dim);
		color: var(--text-dim);
		font-family: var(--font-mono);
		font-size: 10px;
		padding: 2px 6px;
		cursor: pointer;
	}
	.agent-chip:hover { border-color: var(--green-primary); color: var(--green-primary); }
	.agent-chip.protagonist { border-color: var(--gold-dim); color: var(--gold); }
	.star { color: var(--gold); }

	.agent-actions-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 6px;
	}
	.agent-action-btn {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 8px;
		background: var(--bg-primary);
		border: 1px solid color-mix(in srgb, var(--btn-color) 30%, transparent);
		cursor: pointer;
		font-family: var(--font-mono);
		color: var(--btn-color);
		border-radius: 3px;
	}
	.agent-action-btn:hover {
		border-color: var(--btn-color);
		background: color-mix(in srgb, var(--btn-color) 10%, var(--bg-primary));
	}
	.action-label { font-size: 10px; font-weight: bold; letter-spacing: 1px; }
	.action-desc { font-size: 9px; color: var(--text-dim); margin-top: 2px; }

	/* Whisper */
	.whisper-panel {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.whisper-hint {
		font-size: 10px;
		color: var(--text-dim);
		line-height: 1.5;
	}
	.whisper-target {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.whisper-target label {
		font-size: 10px;
		color: var(--text-dim);
		letter-spacing: 2px;
		width: 60px;
	}
	.whisper-compose {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.whisper-compose label {
		font-size: 10px;
		color: var(--text-dim);
		letter-spacing: 2px;
	}
	.whisper-text {
		resize: vertical;
		min-height: 80px;
		line-height: 1.5;
	}
	textarea.text-input {
		font-size: 11px;
	}
	.preset-chips {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		margin-top: 4px;
	}
	.preset-chip {
		background: var(--bg-primary);
		border: 1px solid var(--gold-dim);
		color: var(--gold);
		font-family: var(--font-mono);
		font-size: 9px;
		padding: 3px 8px;
		cursor: pointer;
		border-radius: 2px;
	}
	.preset-chip:hover {
		border-color: var(--gold);
		background: rgba(255, 215, 0, 0.1);
	}
	.whisper-send {
		padding: 10px;
		background: var(--green-dim);
		border: 1px solid var(--green-primary);
		color: var(--green-primary);
		font-family: var(--font-mono);
		font-size: 11px;
		letter-spacing: 2px;
		cursor: pointer;
		margin-top: 4px;
	}
	.whisper-send:hover:not(:disabled) {
		background: var(--green-primary);
		color: var(--bg-primary);
	}
	.whisper-send:disabled {
		opacity: 0.4;
		cursor: default;
	}
</style>
