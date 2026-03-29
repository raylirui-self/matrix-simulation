<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { agents, runId } from '$lib/stores/simulation';
	import { zoomLevel, focusAgentId, focusCell } from '$lib/stores/ui';
	import { api } from '$lib/api/rest';

	let agentDetail = $state<any>(null);
	let loading = $state(false);

	const EMOTION_COLORS: Record<string, string> = {
		happiness: '#00ff88',
		fear: '#ffff00',
		anger: '#ff2200',
		grief: '#6644cc',
		hope: '#00aaff'
	};

	const BG_COLORS: Record<string, string> = {
		happiness: '#051a08',
		fear: '#1a1a05',
		anger: '#1a0505',
		grief: '#0a0520',
		hope: '#050a1a'
	};

	async function loadAgent(agentId: number) {
		const rid = $runId;
		if (!rid) return;
		loading = true;
		try {
			agentDetail = await api.getAgent(rid, agentId);
		} catch (e) {
			console.error('Failed to load agent:', e);
		}
		loading = false;
	}

	$effect(() => {
		const aid = $focusAgentId;
		if (aid !== null && $zoomLevel === 3) {
			loadAgent(aid);
		}
	});

	function goBack() {
		if ($focusCell) {
			zoomLevel.set(2);
		} else {
			zoomLevel.set(1);
		}
		focusAgentId.set(null);
	}

	function visitAgent(id: number) {
		focusAgentId.set(id);
	}
</script>

{#if $zoomLevel === 3}
	<div
		class="soul-view"
		style="background: {agentDetail ? BG_COLORS[agentDetail.dominant_emotion] || '#030d03' : '#030d03'};"
	>
		{#if loading}
			<div class="loading">ACCESSING NEURAL PATHWAY...</div>
		{:else if agentDetail}
			<button class="back-btn" onclick={goBack}>◄ BACK</button>

			<!-- Header -->
			<div class="soul-header">
				<div class="agent-id">
					SUBJECT #{agentDetail.id}
					{#if agentDetail.protagonist_name}
						<span class="name">"{agentDetail.protagonist_name}"</span>
					{/if}
				</div>
				<div class="agent-status">
					<span class="phase">{agentDetail.phase.toUpperCase()}</span>
					<span class="sex">{agentDetail.sex}</span>
					<span>AGE: {agentDetail.age}</span>
					<span>GEN: {agentDetail.generation}</span>
					{#if !agentDetail.alive}<span class="dead">DECEASED</span>{/if}
					{#if agentDetail.redpilled}<span class="redpilled">REDPILLED</span>{/if}
					{#if agentDetail.is_anomaly}<span class="anomaly">THE ONE</span>{/if}
					{#if agentDetail.is_sentinel}<span class="sentinel">SENTINEL</span>{/if}
				</div>
			</div>

			<div class="soul-grid">
				<!-- Left column: Traits + Skills -->
				<div class="soul-section">
					<h3>IDENTITY MATRIX</h3>
					<div class="stat-group">
						<div class="stat-bar">
							<span>HP</span>
							<div class="bar">
								<div class="bar-fill health" style="width: {agentDetail.health * 100}%"></div>
							</div>
							<span>{agentDetail.health.toFixed(2)}</span>
						</div>
						<div class="stat-bar">
							<span>IQ</span>
							<div class="bar">
								<div class="bar-fill iq" style="width: {agentDetail.intelligence * 100}%"></div>
							</div>
							<span>{agentDetail.intelligence.toFixed(2)}</span>
						</div>
						<div class="stat-bar">
							<span>AWR</span>
							<div class="bar">
								<div class="bar-fill awareness" style="width: {agentDetail.awareness * 100}%"></div>
							</div>
							<span>{(agentDetail.awareness * 100).toFixed(0)}%</span>
						</div>
						<div class="stat-bar">
							<span>WEALTH</span>
							<div class="bar">
								<div class="bar-fill wealth" style="width: {Math.min(100, agentDetail.wealth * 10)}%"></div>
							</div>
							<span>{agentDetail.wealth.toFixed(1)}</span>
						</div>
					</div>

					<h3>TRAITS</h3>
					<div class="stat-group">
						{#each Object.entries(agentDetail.traits) as [key, val]}
							{#if key !== 'max_age'}
								<div class="stat-bar">
									<span>{key.replace('_', ' ').toUpperCase().slice(0, 8)}</span>
									<div class="bar">
										<div class="bar-fill trait" style="width: {Number(val) * 100}%"></div>
									</div>
									<span>{Number(val).toFixed(2)}</span>
								</div>
							{/if}
						{/each}
					</div>

					<h3>SKILLS</h3>
					<div class="stat-group">
						{#each Object.entries(agentDetail.skills) as [key, val]}
							<div class="stat-bar">
								<span>{key.toUpperCase()}</span>
								<div class="bar">
									<div class="bar-fill skill" style="width: {Number(val) * 100}%"></div>
								</div>
								<span>{Number(val).toFixed(2)}</span>
							</div>
						{/each}
					</div>
				</div>

				<!-- Center column: Emotions + Beliefs -->
				<div class="soul-section">
					<h3>EMOTIONAL STATE</h3>
					<div class="emotions-grid">
						{#each Object.entries(agentDetail.emotions) as [emo, val]}
							<div class="emotion-gauge">
								<div
									class="emotion-ring"
									style="--color: {EMOTION_COLORS[emo] || '#00ff88'}; --pct: {Number(val) * 100}%"
								>
									<span class="emotion-val">{(Number(val) * 100).toFixed(0)}</span>
								</div>
								<span class="emotion-label">{emo}</span>
							</div>
						{/each}
					</div>
					<div class="stat-bar">
						<span>TRAUMA</span>
						<div class="bar">
							<div class="bar-fill trauma" style="width: {agentDetail.trauma * 100}%"></div>
						</div>
						<span>{(agentDetail.trauma * 100).toFixed(0)}%</span>
					</div>
					<div class="dominant-emotion">
						DOMINANT: <span style="color: {EMOTION_COLORS[agentDetail.dominant_emotion]}">{agentDetail.dominant_emotion?.toUpperCase()}</span>
					</div>

					<h3>BELIEF COMPASS</h3>
					<div class="beliefs-grid">
						{#each Object.entries(agentDetail.beliefs) as [axis, val]}
							<div class="belief-axis">
								<span class="belief-label">{axis.replace('_', ' ')}</span>
								<div class="belief-bar">
									<div class="belief-marker" style="left: {(Number(val) + 1) * 50}%"></div>
								</div>
								<span class="belief-val">{Number(val).toFixed(2)}</span>
							</div>
						{/each}
					</div>
					{#if agentDetail.faction_id !== null}
						<div class="faction-badge">FACTION: #{agentDetail.faction_id}</div>
					{/if}
				</div>

				<!-- Right column: Bonds + Memory -->
				<div class="soul-section">
					<h3>BOND WEB ({agentDetail.bonds_resolved?.length || 0})</h3>
					<div class="bonds-list">
						{#each agentDetail.bonds_resolved || [] as bond}
							<button
								class="bond-item"
								class:dead={!bond.target_alive}
								onclick={() => bond.target_alive && visitAgent(bond.target_id)}
							>
								<span class="bond-type" style="color: {
									bond.bond_type === 'family' ? '#00ff88' :
									bond.bond_type === 'friend' ? '#00ddff' :
									bond.bond_type === 'rival' ? '#ff4466' :
									bond.bond_type === 'mate' ? '#ffa500' :
									bond.bond_type === 'enemy' ? '#ff0000' : '#00ff88'
								}">{bond.bond_type}</span>
								<span>→ #{bond.target_id} {bond.target_name || ''}</span>
								<span class="bond-strength">{bond.strength.toFixed(2)}</span>
							</button>
						{/each}
					</div>

					<h3>FAMILY</h3>
					<div class="family-tree">
						{#if agentDetail.family?.parents?.length}
							<div class="family-group">
								<span class="text-dim">Parents:</span>
								{#each agentDetail.family.parents as p}
									<button class="family-link" onclick={() => visitAgent(p.id)}>
										#{p.id} {p.name || ''} {p.alive ? '' : '†'}
									</button>
								{/each}
							</div>
						{/if}
						{#if agentDetail.family?.children?.length}
							<div class="family-group">
								<span class="text-dim">Children ({agentDetail.family.children.length}):</span>
								{#each agentDetail.family.children.slice(0, 8) as c}
									<button class="family-link" onclick={() => visitAgent(c.id)}>
										#{c.id} age:{c.age} {c.alive ? '' : '†'}
									</button>
								{/each}
							</div>
						{/if}
					</div>

					<h3>MEMORY STREAM</h3>
					<div class="memory-stream">
						{#if agentDetail.memory_summary}
							<div class="memory-summary">{agentDetail.memory_summary}</div>
						{/if}
						{#each (agentDetail.memory || []).slice().reverse() as mem}
							<div class="memory-entry">
								<span class="mem-tick">t={mem.tick}</span>
								<span>{mem.event}</span>
							</div>
						{/each}
					</div>

					{#if agentDetail.inner_monologue?.length}
						<h3>INNER MONOLOGUE</h3>
						<div class="monologue">
							{#each agentDetail.inner_monologue.slice(-3) as thought}
								<div class="thought">
									<span class="thought-tick">t={thought.tick}</span>
									<p>{thought.text || thought.thought || JSON.stringify(thought)}</p>
								</div>
							{/each}
						</div>
					{/if}
				</div>
			</div>
		{:else}
			<div class="loading">NO AGENT SELECTED</div>
		{/if}
	</div>
{/if}

<style>
	.soul-view {
		position: fixed;
		inset: 0;
		z-index: 3;
		overflow-y: auto;
		padding: 20px;
		transition: background 0.6s ease;
	}

	.loading {
		text-align: center;
		padding-top: 40vh;
		color: var(--green-dim);
		font-size: 18px;
	}

	.back-btn {
		position: fixed;
		top: 15px;
		left: 15px;
		background: var(--bg-panel);
		border: 1px solid var(--green-dim);
		color: var(--green-primary);
		font-family: var(--font-mono);
		font-size: 12px;
		padding: 6px 14px;
		cursor: pointer;
		z-index: 10;
	}
	.back-btn:hover {
		border-color: var(--green-primary);
		background: var(--green-dim);
	}

	.soul-header {
		text-align: center;
		margin-bottom: 20px;
		padding-top: 10px;
	}
	.agent-id {
		font-size: 20px;
		font-weight: bold;
		letter-spacing: 2px;
	}
	.name { color: var(--gold); margin-left: 8px; }
	.agent-status {
		margin-top: 8px;
		display: flex;
		gap: 12px;
		justify-content: center;
		color: var(--text-dim);
		font-size: 12px;
	}
	.phase { color: var(--cyan); }
	.dead { color: var(--red-warning); }
	.redpilled { color: var(--red-warning); font-weight: bold; }
	.anomaly { color: var(--gold); font-weight: bold; }
	.sentinel { color: #ff0000; font-weight: bold; }

	.soul-grid {
		display: grid;
		grid-template-columns: 1fr 1fr 1fr;
		gap: 20px;
		max-width: 1400px;
		margin: 0 auto;
	}

	.soul-section {
		background: rgba(6, 18, 6, 0.6);
		border: 1px solid var(--green-dim);
		border-radius: 4px;
		padding: 16px;
	}

	h3 {
		font-size: 11px;
		letter-spacing: 2px;
		color: var(--text-dim);
		margin: 16px 0 10px;
		border-bottom: 1px solid var(--green-dim);
		padding-bottom: 4px;
	}
	h3:first-child { margin-top: 0; }

	.stat-group { display: flex; flex-direction: column; gap: 6px; }
	.stat-bar {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 10px;
	}
	.stat-bar span:first-child { width: 70px; color: var(--text-dim); text-align: right; }
	.stat-bar span:last-child { width: 40px; text-align: right; }
	.bar {
		flex: 1;
		height: 6px;
		background: var(--bg-primary);
		border-radius: 3px;
		overflow: hidden;
	}
	.bar-fill {
		height: 100%;
		border-radius: 3px;
		transition: width 0.3s ease;
	}
	.bar-fill.health { background: var(--green-primary); }
	.bar-fill.iq { background: var(--cyan); }
	.bar-fill.awareness { background: var(--white-pure); }
	.bar-fill.wealth { background: var(--gold); }
	.bar-fill.trait { background: var(--green-muted); }
	.bar-fill.skill { background: var(--cyan-dim); }
	.bar-fill.trauma { background: var(--red-warning); }

	.emotions-grid {
		display: grid;
		grid-template-columns: repeat(5, 1fr);
		gap: 8px;
		margin-bottom: 12px;
	}
	.emotion-gauge { text-align: center; }
	.emotion-ring {
		width: 48px;
		height: 48px;
		border-radius: 50%;
		margin: 0 auto;
		display: flex;
		align-items: center;
		justify-content: center;
		background: conic-gradient(var(--color) var(--pct), var(--bg-primary) var(--pct));
		position: relative;
	}
	.emotion-ring::before {
		content: '';
		position: absolute;
		inset: 6px;
		border-radius: 50%;
		background: var(--bg-secondary);
	}
	.emotion-val {
		position: relative;
		z-index: 1;
		font-size: 10px;
		font-weight: bold;
	}
	.emotion-label {
		font-size: 9px;
		color: var(--text-dim);
		margin-top: 4px;
		display: block;
	}
	.dominant-emotion {
		text-align: center;
		margin: 8px 0;
		font-size: 12px;
	}

	.beliefs-grid { display: flex; flex-direction: column; gap: 8px; }
	.belief-axis {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 10px;
	}
	.belief-label { width: 80px; color: var(--text-dim); text-align: right; text-transform: uppercase; }
	.belief-bar {
		flex: 1;
		height: 8px;
		background: linear-gradient(to right, var(--red-dim), var(--bg-primary), var(--green-dim));
		border-radius: 4px;
		position: relative;
	}
	.belief-marker {
		position: absolute;
		top: -2px;
		width: 4px;
		height: 12px;
		background: var(--white-pure);
		border-radius: 2px;
		transform: translateX(-50%);
	}
	.belief-val { width: 40px; text-align: right; }
	.faction-badge {
		text-align: center;
		margin-top: 10px;
		padding: 4px 12px;
		border: 1px solid var(--green-dim);
		border-radius: 3px;
		font-size: 11px;
		display: inline-block;
	}

	.bonds-list {
		display: flex;
		flex-direction: column;
		gap: 3px;
		max-height: 200px;
		overflow-y: auto;
	}
	.bond-item {
		display: flex;
		gap: 8px;
		font-size: 11px;
		cursor: pointer;
		background: none;
		border: none;
		color: var(--green-primary);
		font-family: var(--font-mono);
		padding: 3px 6px;
		text-align: left;
	}
	.bond-item:hover { background: var(--green-dim); }
	.bond-item.dead { opacity: 0.5; cursor: default; }
	.bond-type { width: 70px; font-weight: bold; }
	.bond-strength { margin-left: auto; color: var(--text-dim); }

	.family-tree { font-size: 11px; }
	.family-group { margin-bottom: 8px; }
	.family-link {
		background: none;
		border: none;
		color: var(--cyan);
		font-family: var(--font-mono);
		font-size: 11px;
		cursor: pointer;
		padding: 1px 4px;
	}
	.family-link:hover { text-decoration: underline; }

	.memory-stream {
		max-height: 200px;
		overflow-y: auto;
		font-size: 11px;
	}
	.memory-summary {
		color: var(--text-dim);
		font-style: italic;
		margin-bottom: 8px;
		padding: 6px;
		background: var(--bg-primary);
		border-radius: 3px;
	}
	.memory-entry {
		padding: 2px 0;
		border-bottom: 1px solid rgba(0, 255, 136, 0.05);
	}
	.mem-tick { color: var(--text-dim); margin-right: 8px; }

	.monologue { font-size: 11px; }
	.thought {
		padding: 8px;
		margin-bottom: 6px;
		background: var(--bg-primary);
		border-left: 2px solid var(--gold-dim);
		border-radius: 0 3px 3px 0;
		font-style: italic;
		color: var(--white);
	}
	.thought-tick { color: var(--text-dim); font-size: 10px; display: block; margin-bottom: 4px; }
</style>
