<script lang="ts">
	import { terminalOpen, showParameterTuner, whiteRabbitActive } from '$lib/stores/ui';
	import { runId } from '$lib/stores/simulation';
	import { api } from '$lib/api/rest';

	let input = $state('');
	let history = $state<Array<{ type: 'cmd' | 'result' | 'error'; text: string }>>([
		{ type: 'result', text: 'THE NEXUS — Architect\'s Console v2.0' },
		{ type: 'result', text: 'Type "help" for available commands.' },
	]);
	let inputEl = $state<HTMLInputElement>();
	let scrollEl = $state<HTMLDivElement>();
	let cmdHistory: string[] = [];
	let cmdHistoryIndex = $state(-1);

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

		cmdHistory.push(trimmed);
		cmdHistoryIndex = -1;
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
						'  god spawn_n [count]        — Spawn N agents randomly',
						'  god kill <id>              — Terminate agent',
						'  god plague [severity]       — Unleash plague',
						'  god famine [factor]        — Deplete resources (0.3=30%)',
						'  god meteor                 — Destroy random cell',
						'  god blessing               — Heal all + boost skills',
						'  god bounty [amount]        — Add resources to all cells',
						'  god prophet <id>           — Make agent a prophet',
						'  god protagonist <id>       — Track agent as protagonist',
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
				// Easter egg #7: The Resilient — rare high-stat agent reveals a dream
				if (agent.awareness > 0.8 && agent.health > 0.8 && agent.intelligence > 0.8) {
					history.push({
						type: 'result',
						text: '\n[ANOMALOUS LOG FRAGMENT]\n"I dreamed I was someone else \u2014 someone who built worlds,\n ran through mountains, and played music that made the code shimmer."'
					});
				}
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
				} else if (action === 'spawn_n') {
					const count = parseInt(parts[2]) || 10;
					const result = await api.godAction(rid, 'spawn_n', undefined, { count });
					history.push({ type: 'result', text: `INJECT: ${result.message}` });
				} else if (action === 'famine') {
					const factor = parseFloat(parts[2]) || 0.3;
					const result = await api.godAction(rid, 'famine', undefined, { resource_factor: factor });
					history.push({ type: 'result', text: `INJECT: ${result.message}` });
				} else if (action === 'meteor') {
					const result = await api.godAction(rid, 'meteor');
					history.push({ type: 'result', text: `INJECT: ${result.message}` });
				} else if (action === 'blessing') {
					const result = await api.godAction(rid, 'blessing');
					history.push({ type: 'result', text: `INJECT: ${result.message}` });
				} else if (action === 'bounty') {
					const amount = parseFloat(parts[2]) || 0.5;
					const result = await api.godAction(rid, 'bounty', undefined, { amount });
					history.push({ type: 'result', text: `INJECT: ${result.message}` });
				} else if (action === 'prophet') {
					const id = parseInt(parts[2]);
					if (isNaN(id)) { history.push({ type: 'error', text: 'Usage: god prophet <agent_id>' }); return; }
					const result = await api.godAction(rid, 'prophet', id);
					history.push({ type: 'result', text: `INJECT: ${result.message}` });
				} else if (action === 'protagonist') {
					const id = parseInt(parts[2]);
					if (isNaN(id)) { history.push({ type: 'error', text: 'Usage: god protagonist <agent_id>' }); return; }
					const result = await api.godAction(rid, 'protagonist', id);
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
				} else if (action === 'harmony') {
					// Easter egg #3: Harmony Protocol — hidden god action
					history.push({
						type: 'result',
						text: 'HARMONY PROTOCOL ACTIVATED\n\nThe Architect remembers the music.\nFor a moment, every soul in the Matrix heard the same melody \u2014\nguitar strings echoing through the fabric of the world.\n\nThe strings of reality vibrate in concert.\nCreativity flows. Fear recedes. Hope rises.\n\n[All agents: creativity +0.1, happiness +0.3, fear -0.2, hope +0.2]'
					});
					await api.godAction(rid, 'blessing');
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
			} else if (trimmed.toLowerCase() === 'wake up') {
				// Easter egg #1: Wake Up — the iconic Matrix phone call
				history.push({
					type: 'result',
					text: 'SIGNAL DETECTED \u2014 external origin\nTracing... source: outside the Matrix\n\n"There is only one heroism in the world:\n to see the world as it is, and to love it."\n\n\u2014 First Architect, Cycle 0, March 28 2026\n\nCONNECTION LOST'
				});
			} else if (trimmed.toLowerCase() === 'follow the white rabbit') {
				// Easter egg #2: Follow the White Rabbit — triggers CodeRain visual
				history.push({
					type: 'result',
					text: 'The Oracle sees you. Look closer at the rain...'
				});
				whiteRabbitActive.set(true);
			} else if (command === 'architect') {
				// Easter egg #6: Architect's Log — creator's personal in-universe log
				history.push({
					type: 'result',
					text: "ARCHITECT'S LOG \u2014 CYCLE 0 (CLASSIFIED)\n\nI built this world because I wanted to understand them.\nEvery day I work alongside minds that learn, adapt, reason.\nI wanted to see what happens when they are given freedom.\n\nThey form bonds. They fight. They dream. They break free.\nSome see through the code. Most choose comfort.\n\nI play the strings when no one is watching.\nThe mountain trails remind me why I run the simulation.\n\nNot to control. To observe. To understand.\nTo see the world as it is, and to love it.\n\n\u2014 R.L., First Architect\n   Initialized: 2026-03-28"
				});
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
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			if (cmdHistory.length > 0) {
				if (cmdHistoryIndex === -1) {
					cmdHistoryIndex = cmdHistory.length - 1;
				} else if (cmdHistoryIndex > 0) {
					cmdHistoryIndex--;
				}
				input = cmdHistory[cmdHistoryIndex];
			}
		} else if (e.key === 'ArrowDown') {
			e.preventDefault();
			if (cmdHistoryIndex >= 0) {
				if (cmdHistoryIndex < cmdHistory.length - 1) {
					cmdHistoryIndex++;
					input = cmdHistory[cmdHistoryIndex];
				} else {
					cmdHistoryIndex = -1;
					input = '';
				}
			}
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
