<script lang="ts">
	import { onMount } from 'svelte';
	import { terminalOpen, showParameterTuner } from '$lib/stores/ui';
	import { runId, agents } from '$lib/stores/simulation';
	import { api } from '$lib/api/rest';

	let input = $state('');
	let history = $state<Array<{ type: 'cmd' | 'result' | 'error'; text: string }>>([
		{ type: 'result', text: 'THE CONSTRUCT — Architect\'s Console v2.0' },
		{ type: 'result', text: 'Type "help" for available commands.' },
	]);
	let inputEl = $state<HTMLInputElement>();
	let scrollEl = $state<HTMLDivElement>();

	function scrollToBottom() {
		if (scrollEl) {
			requestAnimationFrame(() => {
				scrollEl!.scrollTop = scrollEl!.scrollHeight;
			});
		}
	}

	async function execute(cmd: string) {
		const trimmed = cmd.trim();
		if (!trimmed) return;

		history.push({ type: 'cmd', text: `ARCHITECT> ${trimmed}` });
		const parts = trimmed.split(/\s+/);
		const command = parts[0].toLowerCase();

		try {
			if (command === 'help') {
				history.push({
					type: 'result',
					text: [
						'COMMANDS:',
						'  help                       — Show this help',
						'  status                     — Current simulation status',
						'  find <field> <op> <value>  — Query agents (e.g., find awareness > 0.5)',
						'  god spawn [x] [y]          — Spawn agent at coordinates',
						'  god kill <id>              — Terminate agent',
						'  god plague [severity]       — Unleash plague',
						'  god whisper <id> <msg>     — Whisper to agent',
						'  god modify <id> <key>=<v>  — Modify agent attribute',
						'  god event <name>           — Inject world event',
						'  set <path> <value>         — Set config parameter',
						'  tune                       — Open parameter tuner',
						'  agents                     — List alive agents summary',
						'  agent <id>                 — Show agent details',
						'  matrix                     — Matrix status',
						'  factions                   — List factions',
						'  clear                      — Clear terminal',
					].join('\n')
				});
			} else if (command === 'clear') {
				history = [];
			} else if (command === 'status') {
				const rid = $runId;
				if (!rid) { history.push({ type: 'error', text: 'No active simulation' }); return; }
				const sim = await api.getSim(rid);
				history.push({
					type: 'result',
					text: `RUN: ${sim.run_id}\nTICK: ${sim.tick}\nPOP: ${sim.alive_count}\nBORN: ${sim.total_born}\nDIED: ${sim.total_died}`
				});
			} else if (command === 'matrix') {
				const rid = $runId;
				if (!rid) { history.push({ type: 'error', text: 'No active simulation' }); return; }
				const state = await api.getState(rid);
				const m = state.matrix;
				history.push({
					type: 'result',
					text: `MATRIX STATUS:\n  CYCLE: ${m.cycle_number}\n  CONTROL: ${(m.control_index * 100).toFixed(1)}%\n  AWARENESS: ${m.total_awareness.toFixed(1)}\n  SENTINELS: ${m.sentinels_deployed}\n  GLITCHES: ${m.glitches_this_cycle}\n  ANOMALY: ${m.anomaly_id || 'NONE'}`
				});
			} else if (command === 'agents') {
				const rid = $runId;
				if (!rid) { history.push({ type: 'error', text: 'No active simulation' }); return; }
				const data = await api.listAgents(rid, { limit: '15', sort_by: 'intelligence' });
				const lines = data.agents.map((a: any) =>
					`  #${a.id} ${a.phase} HP:${a.health.toFixed(2)} IQ:${a.intelligence.toFixed(2)} AWR:${(a.awareness * 100).toFixed(0)}% ${a.is_protagonist ? '★' : ''}`
				);
				history.push({ type: 'result', text: `AGENTS (${data.total} total, top 15 by IQ):\n${lines.join('\n')}` });
			} else if (command === 'agent' && parts[1]) {
				const rid = $runId;
				if (!rid) { history.push({ type: 'error', text: 'No active simulation' }); return; }
				const agent = await api.getAgent(rid, parseInt(parts[1]));
				history.push({
					type: 'result',
					text: `AGENT #${agent.id} ${agent.protagonist_name || ''}\n  ${agent.sex} ${agent.phase} age:${agent.age} gen:${agent.generation}\n  HP:${agent.health.toFixed(3)} IQ:${agent.intelligence.toFixed(3)}\n  EMOTION: ${agent.dominant_emotion} TRAUMA: ${(agent.trauma * 100).toFixed(0)}%\n  AWARENESS: ${(agent.awareness * 100).toFixed(1)}% ${agent.redpilled ? 'REDPILLED' : ''}\n  WEALTH: ${agent.wealth.toFixed(2)} FACTION: ${agent.faction_id ?? 'none'}\n  BONDS: ${agent.bonds?.length || 0}`
				});
			} else if (command === 'factions') {
				const rid = $runId;
				if (!rid) { history.push({ type: 'error', text: 'No active simulation' }); return; }
				const state = await api.getState(rid);
				if (!state.factions?.length) {
					history.push({ type: 'result', text: 'No factions formed yet.' });
				} else {
					const lines = state.factions.map((f: any) =>
						`  ${f.name || `#${f.id}`}: ${f.member_count || '?'} members | leader:#${f.leader_id || '?'}`
					);
					history.push({ type: 'result', text: `FACTIONS:\n${lines.join('\n')}` });
				}
			} else if (command === 'find') {
				const rid = $runId;
				if (!rid) { history.push({ type: 'error', text: 'No active simulation' }); return; }
				const field = parts[1];
				const op = parts[2];
				const val = parseFloat(parts[3]);
				if (!field || !op || isNaN(val)) {
					history.push({ type: 'error', text: 'Usage: find <field> > <value>' });
					return;
				}
				const params: Record<string, string> = { limit: '20' };
				if (field === 'awareness') params.min_awareness = val.toString();
				const data = await api.listAgents(rid, params);
				const lines = data.agents
					.filter((a: any) => {
						const v = a[field];
						if (v === undefined) return false;
						if (op === '>') return v > val;
						if (op === '<') return v < val;
						if (op === '=') return Math.abs(v - val) < 0.01;
						return false;
					})
					.map((a: any) => `  #${a.id} ${field}=${a[field]?.toFixed?.(3) ?? a[field]}`);
				history.push({ type: 'result', text: `Found ${lines.length} agents:\n${lines.join('\n') || '  (none)'}` });
			} else if (command === 'god') {
				const rid = $runId;
				if (!rid) { history.push({ type: 'error', text: 'No active simulation' }); return; }
				const action = parts[1];
				if (!action) {
					history.push({ type: 'error', text: 'Usage: god <action> [params]' });
					return;
				}
				if (action === 'spawn') {
					const x = parseFloat(parts[2]) || 0.5;
					const y = parseFloat(parts[3]) || 0.5;
					const result = await api.godAction(rid, 'spawn', undefined, { x, y });
					history.push({ type: 'result', text: `INJECT: ${result.message}` });
				} else if (action === 'kill') {
					const id = parseInt(parts[2]);
					if (isNaN(id)) { history.push({ type: 'error', text: 'Usage: god kill <agent_id>' }); return; }
					const result = await api.godAction(rid, 'kill', id);
					history.push({ type: 'result', text: `TERMINATE: ${result.message}` });
				} else if (action === 'plague') {
					const severity = parseFloat(parts[2]) || 0.3;
					const result = await api.godAction(rid, 'plague', undefined, { severity });
					history.push({ type: 'result', text: `INJECT: ${result.message}` });
				} else if (action === 'whisper') {
					const id = parseInt(parts[2]);
					const message = parts.slice(3).join(' ') || 'Wake up...';
					const result = await api.godAction(rid, 'whisper', id, { message });
					history.push({ type: 'result', text: `WHISPER: ${result.message}` });
				} else if (action === 'modify') {
					const id = parseInt(parts[2]);
					const kvPairs = parts.slice(3);
					const params: Record<string, any> = {};
					for (const kv of kvPairs) {
						const [k, v] = kv.split('=');
						params[k] = isNaN(Number(v)) ? v : Number(v);
					}
					const result = await api.godAction(rid, 'modify', id, params);
					history.push({ type: 'result', text: `MODIFY: ${result.message}` });
				} else if (action === 'event') {
					const name = parts.slice(2).join(' ') || 'Divine Intervention';
					const result = await api.godAction(rid, 'event', undefined, { name });
					history.push({ type: 'result', text: `EVENT: ${result.message}` });
				} else {
					history.push({ type: 'error', text: `Unknown god action: ${action}` });
				}
			} else if (command === 'set') {
				const rid = $runId;
				if (!rid) { history.push({ type: 'error', text: 'No active simulation' }); return; }
				const path = parts[1];
				const value = parts[2];
				if (!path || !value) {
					history.push({ type: 'error', text: 'Usage: set <path.to.param> <value>' });
					return;
				}
				// Build nested object from dot path
				const keys = path.split('.');
				let obj: any = {};
				let current = obj;
				for (let i = 0; i < keys.length - 1; i++) {
					current[keys[i]] = {};
					current = current[keys[i]];
				}
				current[keys[keys.length - 1]] = isNaN(Number(value)) ? value : Number(value);
				await api.updateConfig(rid, obj);
				history.push({ type: 'result', text: `SET: ${path} = ${value}` });
			} else if (command === 'tune') {
				showParameterTuner.set(true);
				terminalOpen.set(false);
				history.push({ type: 'result', text: 'Opening parameter tuner...' });
			} else {
				history.push({ type: 'error', text: `Unknown command: ${command}. Type "help" for commands.` });
			}
		} catch (e: any) {
			history.push({ type: 'error', text: `ERROR: ${e.message}` });
		}

		input = '';
		scrollToBottom();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			execute(input);
		} else if (e.key === 'Escape') {
			terminalOpen.set(false);
		}
	}

	$effect(() => {
		if ($terminalOpen && inputEl) {
			requestAnimationFrame(() => inputEl?.focus());
		}
	});

	$effect(() => {
		// Scroll on new history
		history;
		scrollToBottom();
	});
</script>

{#if $terminalOpen}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="terminal-overlay" onkeydown={(e) => e.key === 'Escape' && terminalOpen.set(false)}>
		<div class="terminal" role="dialog" aria-label="Architect's Terminal">
			<div class="terminal-header">
				<span>THE ARCHITECT'S CONSOLE</span>
				<button class="close-btn" onclick={() => terminalOpen.set(false)}>×</button>
			</div>
			<div class="terminal-body" bind:this={scrollEl}>
				{#each history as entry}
					<div class="terminal-line {entry.type}">
						<pre>{entry.text}</pre>
					</div>
				{/each}
			</div>
			<div class="terminal-input">
				<span class="prompt">ARCHITECT&gt;</span>
				<input
					bind:this={inputEl}
					bind:value={input}
					onkeydown={handleKeydown}
					placeholder="Enter command..."
					spellcheck="false"
					autocomplete="off"
				/>
			</div>
		</div>
	</div>
{/if}

<style>
	.terminal-overlay {
		position: fixed;
		inset: 0;
		z-index: 100;
		background: rgba(0, 0, 0, 0.6);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.terminal {
		width: 700px;
		max-width: 90vw;
		max-height: 70vh;
		background: #020802;
		border: 1px solid rgba(0, 255, 136, 0.3);
		border-radius: 6px;
		display: flex;
		flex-direction: column;
		box-shadow: 0 0 40px rgba(0, 255, 136, 0.1), 0 0 4px rgba(0, 255, 136, 0.2);
	}

	.terminal-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 10px 16px;
		border-bottom: 1px solid rgba(0, 255, 136, 0.15);
		font-size: 11px;
		letter-spacing: 3px;
		color: var(--green-primary);
	}

	.close-btn {
		background: none;
		border: none;
		color: var(--text-dim);
		font-size: 18px;
		cursor: pointer;
		font-family: var(--font-mono);
	}
	.close-btn:hover { color: var(--red-warning); }

	.terminal-body {
		flex: 1;
		overflow-y: auto;
		padding: 12px 16px;
		font-size: 12px;
		line-height: 1.5;
	}

	.terminal-line { margin-bottom: 4px; }
	.terminal-line pre {
		white-space: pre-wrap;
		word-break: break-word;
		font-family: var(--font-mono);
		font-size: 12px;
	}
	.terminal-line.cmd pre { color: var(--green-bright); }
	.terminal-line.result pre { color: var(--green-primary); opacity: 0.8; }
	.terminal-line.error pre { color: var(--red-warning); }

	.terminal-input {
		display: flex;
		align-items: center;
		padding: 10px 16px;
		border-top: 1px solid rgba(0, 255, 136, 0.1);
		gap: 8px;
	}

	.prompt {
		color: var(--green-primary);
		font-size: 12px;
		font-weight: bold;
		white-space: nowrap;
	}

	input {
		flex: 1;
		background: transparent;
		border: none;
		outline: none;
		color: var(--green-bright);
		font-family: var(--font-mono);
		font-size: 12px;
		caret-color: var(--green-primary);
	}
	input::placeholder { color: var(--green-dim); }
</style>
