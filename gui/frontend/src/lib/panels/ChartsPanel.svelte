<script lang="ts">
	import { tick as tickStore, stats, tickHistory, factions, matrixState, emotionStats, economyStats, deathCauses, ageDistribution, techProgress, factionBeliefMeans, wars } from '$lib/stores/simulation';

	let { open = $bindable(false) } = $props();

	// Chart dimensions
	const W = 320;
	const H = 120;
	const PAD = { top: 20, right: 10, bottom: 20, left: 40 };
	const plotW = W - PAD.left - PAD.right;
	const plotH = H - PAD.top - PAD.bottom;

	// ── Population chart data ──
	let popPath = $derived.by(() => {
		const data = $tickHistory;
		if (data.length < 2) return '';
		const maxPop = Math.max(1, ...data.map(d => d.alive));
		const points = data.map((d, i) => {
			const x = PAD.left + (i / (data.length - 1)) * plotW;
			const y = PAD.top + plotH - (d.alive / maxPop) * plotH;
			return `${x},${y}`;
		});
		return `M${points.join(' L')}`;
	});

	let iqPath = $derived.by(() => {
		const data = $tickHistory;
		if (data.length < 2) return '';
		const maxIQ = Math.max(0.01, ...data.map(d => d.intelligence));
		const points = data.map((d, i) => {
			const x = PAD.left + (i / (data.length - 1)) * plotW;
			const y = PAD.top + plotH - (d.intelligence / maxIQ) * plotH;
			return `${x},${y}`;
		});
		return `M${points.join(' L')}`;
	});

	let healthPath = $derived.by(() => {
		const data = $tickHistory;
		if (data.length < 2) return '';
		const points = data.map((d, i) => {
			const x = PAD.left + (i / (data.length - 1)) * plotW;
			const y = PAD.top + plotH - d.health * plotH;
			return `${x},${y}`;
		});
		return `M${points.join(' L')}`;
	});

	// ── Phase distribution data ──
	let phaseData = $derived.by(() => {
		const pc = $stats.phase_counts || {};
		const phases = ['infant', 'child', 'adolescent', 'adult', 'elder'];
		const colors: Record<string, string> = {
			infant: '#66ff66', child: '#00ddff', adolescent: '#ffaa00', adult: '#ff4466', elder: '#aa66ff'
		};
		const total = Object.values(pc).reduce((s: number, v: any) => s + (v as number), 0) || 1;
		let cumulative = 0;
		return phases.map(p => {
			const count = (pc[p] || 0) as number;
			const pct = count / total;
			const start = cumulative;
			cumulative += pct;
			return { phase: p, count, pct, start, color: colors[p] || '#00ff88' };
		});
	});

	// ── Era detection ──
	let currentEra = $derived.by(() => {
		const s = $stats;
		const pop = s.alive_count;
		const avgIQ = s.avg_intelligence;
		// Check for techs - we'd need breakthroughs store but approximate
		if (pop === 0) return { name: 'The Void', color: '#ff4466', desc: 'Nothing remains...' };
		if (avgIQ > 0.6) return { name: 'Industrial Age', color: '#ffd700', desc: 'Machines reshape the world' };
		if (avgIQ > 0.45) return { name: 'Trade Era', color: '#00ccff', desc: 'Commerce connects communities' };
		if (avgIQ > 0.3) return { name: 'Age of Awakening', color: '#aa66ff', desc: 'Knowledge grows rapidly' };
		if (pop > 80) return { name: 'Tribal Expansion', color: '#ff8844', desc: 'Clans spread across the land' };
		if (pop > 20) return { name: 'Dawn of Tribes', color: '#00ff88', desc: 'Small groups form bonds' };
		return { name: 'Genesis', color: '#5a8a5a', desc: 'Life stirs in the void' };
	});

	// ── Emotion stats ──
	let emotionBars = $derived.by(() => {
		const e = $emotionStats;
		const emotions = [
			{ key: 'avg_happiness', label: 'HAPPY', color: '#00ff88' },
			{ key: 'avg_fear', label: 'FEAR', color: '#ffff00' },
			{ key: 'avg_anger', label: 'ANGER', color: '#ff2200' },
			{ key: 'avg_grief', label: 'GRIEF', color: '#6644cc' },
			{ key: 'avg_hope', label: 'HOPE', color: '#00aaff' },
		];
		return emotions.map(em => ({
			...em,
			value: (e as any)?.[em.key] ?? 0
		}));
	});

	// ── Economy stats ──
	let econ = $derived($economyStats || {});

	// ── Death causes ──
	const DEATH_COLORS: Record<string, string> = {
		old_age: '#666688',
		starvation: '#ff8844',
		combat: '#ff2200',
		disease: '#aa44ff',
		meteor: '#ff6600',
		plague: '#ff4466',
	};

	let deathCauseBars = $derived.by(() => {
		const dc = $deathCauses;
		const entries = Object.entries(dc).filter(([_, v]) => v > 0);
		if (entries.length === 0) return [];
		const maxVal = Math.max(1, ...entries.map(([_, v]) => v));
		return entries
			.sort((a, b) => b[1] - a[1])
			.map(([cause, count]) => ({
				cause,
				count,
				pct: count / maxVal,
				color: DEATH_COLORS[cause] || '#888888'
			}));
	});

	// ── Age distribution pyramid ──
	const DECADES = ['0s', '10s', '20s', '30s', '40s', '50s', '60s', '70s', '80s'];

	let agePyramid = $derived.by(() => {
		const ad = $ageDistribution;
		const rows: Array<{ decade: string; male: number; female: number }> = [];
		let maxCount = 1;
		for (const dec of DECADES) {
			const m = ad[`M_${dec}`] || 0;
			const f = ad[`F_${dec}`] || 0;
			if (m + f > maxCount) maxCount = m + f;
			rows.push({ decade: dec, male: m, female: f });
		}
		return { rows, maxCount };
	});

	// ── Tech progress ──
	let techBars = $derived.by(() => {
		const tp = $techProgress;
		return Object.entries(tp)
			.sort((a, b) => b[1] - a[1])
			.map(([name, value]) => ({
				name: name.replace(/_/g, ' '),
				value,
				unlocked: value >= 1.0
			}));
	});

	// ── Faction belief means ──
	const BELIEF_AXES = [
		{ key: 'individualism', label: 'IND', color: '#00ddff' },
		{ key: 'tradition', label: 'TRD', color: '#ff8844' },
		{ key: 'system_trust', label: 'SYS', color: '#00ff88' },
		{ key: 'spirituality', label: 'SPR', color: '#aa66ff' },
	];

	// ── War detail data ──
	let warDetails = $derived.by(() => {
		const warList = $wars;
		const factionList = $factions;
		const currentTick = $tickStore;
		const factionMap = new Map<number, any>();
		for (const f of factionList) factionMap.set(f.id, f);

		return warList.map(w => {
			const fA = factionMap.get(w.faction_a_id);
			const fB = factionMap.get(w.faction_b_id);
			const duration = currentTick - w.started_at;
			const totalCasualties = w.casualties_a + w.casualties_b;
			const maxCasualties = Math.max(1, w.casualties_a, w.casualties_b);
			return {
				...w,
				name_a: fA?.name || `Faction #${w.faction_a_id}`,
				name_b: fB?.name || `Faction #${w.faction_b_id}`,
				duration,
				totalCasualties,
				maxCasualties,
				pct_a: w.casualties_a / maxCasualties,
				pct_b: w.casualties_b / maxCasualties,
			};
		});
	});

	// Max population
	let popStats = $derived.by(() => {
		const data = $tickHistory;
		if (data.length === 0) return { max: 0, min: 0, current: 0 };
		const aliveValues = data.map(d => d.alive);
		return {
			max: aliveValues.reduce((a, b) => Math.max(a, b), 0),
			min: aliveValues.reduce((a, b) => Math.min(a, b), Infinity),
			current: data[data.length - 1]?.alive || 0
		};
	});
</script>

{#if open}
	<button class="charts-backdrop" onclick={() => open = false} aria-label="Close analytics panel"></button>
	<div class="charts-panel">
		<div class="charts-header">
			<span class="charts-title">ANALYTICS</span>
			<button class="close-btn" onclick={() => open = false}>✕</button>
		</div>

		<div class="charts-content">
			<!-- Era Banner -->
			<div class="era-banner" style="border-color: {currentEra.color};">
				<span class="era-name" style="color: {currentEra.color};">{currentEra.name}</span>
				<span class="era-desc">{currentEra.desc}</span>
				<span class="era-tick">TICK {$tickStore} | POP {$stats.alive_count}</span>
			</div>

			<!-- Population Trend -->
			<div class="chart-card">
				<div class="chart-title">POPULATION & VITALS</div>
				<div class="pop-metrics">
					<span>PEAK: {popStats.max}</span>
					<span>NOW: {popStats.current}</span>
					<span>BORN: {$stats.births}</span>
					<span>DIED: {$stats.deaths}</span>
				</div>
				{#if $tickHistory.length >= 2}
					<svg viewBox="0 0 {W} {H}" class="chart-svg">
						<!-- Grid lines -->
						{#each [0, 0.25, 0.5, 0.75, 1] as pct}
							<line
								x1={PAD.left} y1={PAD.top + plotH * (1 - pct)}
								x2={PAD.left + plotW} y2={PAD.top + plotH * (1 - pct)}
								stroke="rgba(0,255,136,0.08)" stroke-width="0.5"
							/>
						{/each}
						<!-- Population line -->
						<path d={popPath} fill="none" stroke="#00ff88" stroke-width="1.5" />
						<!-- IQ line -->
						<path d={iqPath} fill="none" stroke="#00ddff" stroke-width="1" stroke-dasharray="3,2" />
						<!-- Health line -->
						<path d={healthPath} fill="none" stroke="#ffaa00" stroke-width="1" stroke-dasharray="2,2" />
						<!-- Legend -->
						<line x1={PAD.left} y1={H - 4} x2={PAD.left + 15} y2={H - 4} stroke="#00ff88" stroke-width="1.5" />
						<text x={PAD.left + 18} y={H - 1} fill="#00ff88" font-size="8" font-family="var(--font-mono)">POP</text>
						<line x1={PAD.left + 50} y1={H - 4} x2={PAD.left + 65} y2={H - 4} stroke="#00ddff" stroke-width="1" stroke-dasharray="3,2" />
						<text x={PAD.left + 68} y={H - 1} fill="#00ddff" font-size="8" font-family="var(--font-mono)">IQ</text>
						<line x1={PAD.left + 90} y1={H - 4} x2={PAD.left + 105} y2={H - 4} stroke="#ffaa00" stroke-width="1" stroke-dasharray="2,2" />
						<text x={PAD.left + 108} y={H - 1} fill="#ffaa00" font-size="8" font-family="var(--font-mono)">HP</text>
					</svg>
				{:else}
					<div class="chart-empty">Awaiting data...</div>
				{/if}
			</div>

			<!-- Demographics -->
			<div class="chart-card">
				<div class="chart-title">DEMOGRAPHICS</div>
				<div class="demo-bar">
					{#each phaseData as p}
						{#if p.pct > 0}
							<div
								class="demo-segment"
								style="width: {p.pct * 100}%; background: {p.color};"
								title="{p.phase}: {p.count}"
							></div>
						{/if}
					{/each}
				</div>
				<div class="demo-legend">
					{#each phaseData as p}
						<span class="demo-item">
							<span class="demo-dot" style="background: {p.color};"></span>
							{p.phase}: {p.count}
						</span>
					{/each}
				</div>
			</div>

			<!-- Emotions -->
			<div class="chart-card">
				<div class="chart-title">EMOTIONAL STATE</div>
				<div class="emotion-bars">
					{#each emotionBars as em}
						<div class="emo-row">
							<span class="emo-label">{em.label}</span>
							<div class="emo-track">
								<div class="emo-fill" style="width: {em.value * 100}%; background: {em.color};"></div>
							</div>
							<span class="emo-val">{(em.value * 100).toFixed(0)}</span>
						</div>
					{/each}
				</div>
			</div>

			<!-- Matrix Status -->
			<div class="chart-card matrix-card">
				<div class="chart-title" style="color: var(--system-color);">MATRIX STATUS</div>
				<div class="matrix-metrics">
					<div class="matrix-row">
						<span>CONTROL</span>
						<div class="matrix-gauge">
							<div class="gauge-fill" style="width: {$matrixState.control_index * 100}%; background: {
								$matrixState.control_index > 0.7 ? 'var(--system-color)' :
								$matrixState.control_index > 0.4 ? '#ffaa00' : '#ff4466'
							};"></div>
						</div>
						<span class="matrix-val">{($matrixState.control_index * 100).toFixed(0)}%</span>
					</div>
					<div class="matrix-stats-row">
						<span>CYCLE: {$matrixState.cycle_number}</span>
						<span>SENTINELS: {$matrixState.sentinels_deployed}</span>
						<span>GLITCHES: {$matrixState.glitches_this_cycle}</span>
					</div>
					<div class="matrix-stats-row">
						<span>AWARENESS: {$matrixState.total_awareness.toFixed(1)}</span>
						<span>ANOMALY: {$matrixState.anomaly_id ? `#${$matrixState.anomaly_id}` : 'NONE'}</span>
					</div>
				</div>
			</div>

			<!-- Economy -->
			<div class="chart-card">
				<div class="chart-title" style="color: var(--gold);">ECONOMY</div>
				<div class="econ-metrics">
					<div class="econ-item">
						<span class="econ-label">TOTAL WEALTH</span>
						<span class="econ-val">{(econ as any)?.total_wealth?.toFixed(1) ?? '0'}</span>
					</div>
					<div class="econ-item">
						<span class="econ-label">AVG WEALTH</span>
						<span class="econ-val">{(econ as any)?.avg_wealth?.toFixed(2) ?? '0'}</span>
					</div>
					<div class="econ-item">
						<span class="econ-label">GINI INDEX</span>
						<span class="econ-val">{(econ as any)?.gini?.toFixed(3) ?? '0'}</span>
					</div>
					<div class="econ-item">
						<span class="econ-label">TRADES</span>
						<span class="econ-val">{(econ as any)?.trades ?? '0'}</span>
					</div>
				</div>
			</div>

			<!-- Factions -->
			{#if $factions.length > 0}
				<div class="chart-card">
					<div class="chart-title" style="color: var(--cyan);">FACTIONS ({$factions.length})</div>
					<div class="faction-cards">
						{#each $factions as f}
							<div class="faction-card">
								<div class="faction-header">
									<span class="faction-name">{f.name || `Faction #${f.id}`}</span>
									{#if f.at_war}<span class="war-badge">WAR</span>{/if}
									{#if f.is_resistance}<span class="resist-badge">RESIST</span>{/if}
								</div>
								<div class="faction-stats">
									<span>Members: {f.member_count || '?'}</span>
									<span>Leader: #{f.leader_id || '?'}</span>
								</div>
								<!-- Belief axes mini-bars (Item 18) -->
								{#if $factionBeliefMeans[f.id]}
									<div class="belief-axes">
										{#each BELIEF_AXES as axis}
											{@const val = $factionBeliefMeans[f.id]?.[axis.key] ?? 0}
											<div class="belief-axis-row">
												<span class="belief-axis-label" style="color: {axis.color};">{axis.label}</span>
												<div class="belief-axis-track">
													<div class="belief-axis-fill" style="width: {Math.abs(val) * 50 + 50}%; background: {axis.color}; margin-left: {val < 0 ? (50 + val * 50) + '%' : '50%'}; width: {Math.abs(val) * 50}%;"></div>
													<div class="belief-axis-center"></div>
												</div>
												<span class="belief-axis-val" style="color: {axis.color};">{val.toFixed(2)}</span>
											</div>
										{/each}
									</div>
								{/if}
							</div>
						{/each}
					</div>
				</div>
			{/if}

			<!-- War Detail Panel -->
			{#if warDetails.length > 0}
				<div class="chart-card war-card">
					<div class="chart-title" style="color: var(--red-warning);">ACTIVE WARS ({warDetails.length})</div>
					<div class="war-list">
						{#each warDetails as w}
							<div class="war-item">
								<div class="war-header">
									<span class="war-faction" style="color: var(--cyan);">{w.name_a}</span>
									<span class="war-vs">VS</span>
									<span class="war-faction" style="color: var(--cyan);">{w.name_b}</span>
								</div>
								<!-- Intensity bar -->
								<div class="war-row">
									<span class="war-label">INTENSITY</span>
									<div class="war-intensity-track">
										<div class="war-intensity-fill" style="width: {w.intensity * 100}%; background: {
											w.intensity > 0.7 ? '#ff2200' : w.intensity > 0.4 ? '#ff8844' : '#ffaa00'
										};"></div>
									</div>
									<span class="war-val" style="color: {w.intensity > 0.7 ? '#ff2200' : '#ff8844'};">{(w.intensity * 100).toFixed(0)}%</span>
								</div>
								<!-- Casualty comparison -->
								<div class="war-casualties">
									<div class="war-cas-side">
										<span class="war-cas-label">{w.name_a}</span>
										<div class="war-cas-track">
											<div class="war-cas-fill cas-a" style="width: {w.pct_a * 100}%;"></div>
										</div>
										<span class="war-cas-count">{w.casualties_a}</span>
									</div>
									<div class="war-cas-side">
										<span class="war-cas-label">{w.name_b}</span>
										<div class="war-cas-track">
											<div class="war-cas-fill cas-b" style="width: {w.pct_b * 100}%;"></div>
										</div>
										<span class="war-cas-count">{w.casualties_b}</span>
									</div>
								</div>
								<!-- Duration & totals -->
								<div class="war-footer">
									<span>DURATION: {w.duration} ticks</span>
									<span>TOTAL DEAD: {w.totalCasualties}</span>
									<span>SINCE: T{w.started_at}</span>
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Cause of Death (Item 14) -->
			<div class="chart-card">
				<div class="chart-title" style="color: var(--red-warning);">CAUSE OF DEATH</div>
				{#if deathCauseBars.length > 0}
					<div class="death-bars">
						{#each deathCauseBars as d}
							<div class="death-row">
								<span class="death-label">{d.cause.replace(/_/g, ' ').toUpperCase()}</span>
								<div class="death-track">
									<div class="death-fill" style="width: {d.pct * 100}%; background: {d.color};"></div>
								</div>
								<span class="death-val" style="color: {d.color};">{d.count}</span>
							</div>
						{/each}
					</div>
				{:else}
					<div class="chart-empty">No deaths recorded yet</div>
				{/if}
			</div>

			<!-- Age Distribution Pyramid (Item 15) -->
			<div class="chart-card">
				<div class="chart-title">AGE DISTRIBUTION</div>
				{#if agePyramid.rows.some(r => r.male + r.female > 0)}
					<svg viewBox="0 0 {W} {DECADES.length * 16 + 20}" class="chart-svg">
						<!-- Labels -->
						<text x={W / 2} y={10} fill="var(--text-dim)" font-size="8" font-family="var(--font-mono)" text-anchor="middle">M / F</text>
						{#each agePyramid.rows as row, i}
							{@const barMax = W / 2 - 30}
							{@const y = 18 + i * 16}
							{@const mW = agePyramid.maxCount > 0 ? (row.male / agePyramid.maxCount) * barMax : 0}
							{@const fW = agePyramid.maxCount > 0 ? (row.female / agePyramid.maxCount) * barMax : 0}
							<!-- Decade label -->
							<text x={W / 2} y={y + 9} fill="var(--text-dim)" font-size="8" font-family="var(--font-mono)" text-anchor="middle">{row.decade}</text>
							<!-- Male bar (extends left) -->
							<rect x={W / 2 - 18 - mW} y={y} width={mW} height={12} fill="#00aaff" opacity="0.7" rx="1" />
							{#if row.male > 0}
								<text x={W / 2 - 20 - mW} y={y + 9} fill="#00aaff" font-size="7" font-family="var(--font-mono)" text-anchor="end">{row.male}</text>
							{/if}
							<!-- Female bar (extends right) -->
							<rect x={W / 2 + 18} y={y} width={fW} height={12} fill="#ff66aa" opacity="0.7" rx="1" />
							{#if row.female > 0}
								<text x={W / 2 + 20 + fW} y={y + 9} fill="#ff66aa" font-size="7" font-family="var(--font-mono)" text-anchor="start">{row.female}</text>
							{/if}
						{/each}
					</svg>
				{:else}
					<div class="chart-empty">Awaiting population data...</div>
				{/if}
			</div>

			<!-- Tech Progress (Item 16) -->
			{#if techBars.length > 0}
				<div class="chart-card">
					<div class="chart-title" style="color: var(--gold);">TECH PROGRESS</div>
					<div class="tech-bars">
						{#each techBars as t}
							<div class="tech-row">
								<span class="tech-label">{t.name}</span>
								<div class="tech-track">
									<div class="tech-fill" style="width: {t.value * 100}%; background: {t.unlocked ? 'var(--green-primary)' : 'var(--gold)'};" class:unlocked={t.unlocked}></div>
								</div>
								<span class="tech-val" style="color: {t.unlocked ? 'var(--green-primary)' : 'var(--gold)'};">{(t.value * 100).toFixed(0)}%</span>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	</div>
{/if}

<style>
	.charts-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		z-index: 30;
	}
	.charts-panel {
		position: fixed;
		right: 0;
		top: 0;
		bottom: 0;
		width: 380px;
		background: var(--bg-secondary);
		border-left: 1px solid var(--green-dim);
		z-index: 31;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}
	.charts-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 12px 16px;
		border-bottom: 1px solid var(--green-dim);
	}
	.charts-title {
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

	.charts-content {
		flex: 1;
		overflow-y: auto;
		padding: 12px 16px;
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	/* Era Banner */
	.era-banner {
		text-align: center;
		padding: 12px;
		border: 1px solid;
		border-radius: 4px;
		background: var(--bg-primary);
	}
	.era-name {
		display: block;
		font-size: 16px;
		font-weight: bold;
		letter-spacing: 3px;
	}
	.era-desc {
		display: block;
		font-size: 10px;
		color: var(--text-dim);
		margin-top: 4px;
	}
	.era-tick {
		display: block;
		font-size: 9px;
		color: var(--text-muted);
		margin-top: 6px;
		letter-spacing: 2px;
	}

	/* Charts */
	.chart-card {
		background: var(--bg-primary);
		border: 1px solid rgba(0, 255, 136, 0.08);
		border-radius: 4px;
		padding: 10px 12px;
	}
	.chart-title {
		font-size: 10px;
		letter-spacing: 2px;
		color: var(--green-primary);
		margin-bottom: 8px;
		font-weight: bold;
	}
	.chart-svg {
		width: 100%;
		height: auto;
	}
	.chart-empty {
		text-align: center;
		padding: 20px;
		color: var(--text-muted);
		font-size: 11px;
	}

	.pop-metrics {
		display: flex;
		gap: 12px;
		font-size: 9px;
		color: var(--text-dim);
		margin-bottom: 6px;
	}

	/* Demographics bar */
	.demo-bar {
		display: flex;
		height: 12px;
		border-radius: 6px;
		overflow: hidden;
		margin-bottom: 6px;
	}
	.demo-segment {
		transition: width 0.3s ease;
		min-width: 1px;
	}
	.demo-legend {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		font-size: 9px;
		color: var(--text-dim);
	}
	.demo-item { display: flex; align-items: center; gap: 3px; }
	.demo-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		display: inline-block;
	}

	/* Emotion bars */
	.emotion-bars {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.emo-row {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 9px;
	}
	.emo-label { width: 40px; color: var(--text-dim); text-align: right; }
	.emo-track {
		flex: 1;
		height: 6px;
		background: var(--bg-secondary);
		border-radius: 3px;
		overflow: hidden;
	}
	.emo-fill {
		height: 100%;
		border-radius: 3px;
		transition: width 0.3s ease;
	}
	.emo-val { width: 24px; text-align: right; color: var(--text-dim); }

	/* Matrix card */
	.matrix-card {
		border-color: rgba(0, 170, 204, 0.15);
	}
	.matrix-row {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 10px;
		color: var(--text-dim);
		margin-bottom: 6px;
	}
	.matrix-gauge {
		flex: 1;
		height: 8px;
		background: var(--bg-secondary);
		border-radius: 4px;
		overflow: hidden;
	}
	.gauge-fill {
		height: 100%;
		border-radius: 4px;
		transition: width 0.5s ease, background 0.5s ease;
	}
	.matrix-val { font-weight: bold; width: 30px; text-align: right; }
	.matrix-stats-row {
		display: flex;
		gap: 12px;
		font-size: 9px;
		color: var(--text-dim);
		margin-top: 4px;
	}

	/* Economy */
	.econ-metrics {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 8px;
	}
	.econ-item { text-align: center; }
	.econ-label {
		display: block;
		font-size: 9px;
		color: var(--text-dim);
		letter-spacing: 1px;
	}
	.econ-val {
		display: block;
		font-size: 14px;
		color: var(--gold);
		font-weight: bold;
		margin-top: 2px;
	}

	/* Factions */
	.faction-cards {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.faction-card {
		padding: 6px 8px;
		background: var(--bg-secondary);
		border: 1px solid rgba(0, 255, 136, 0.05);
		border-radius: 3px;
	}
	.faction-header {
		display: flex;
		gap: 6px;
		align-items: center;
	}
	.faction-name {
		color: var(--cyan);
		font-size: 11px;
		flex: 1;
	}
	.war-badge {
		font-size: 8px;
		padding: 1px 4px;
		background: rgba(255, 68, 102, 0.2);
		color: var(--red-warning);
		border: 1px solid var(--red-dim);
		border-radius: 2px;
	}
	.resist-badge {
		font-size: 8px;
		padding: 1px 4px;
		background: rgba(255, 215, 0, 0.1);
		color: var(--gold);
		border: 1px solid var(--gold-dim);
		border-radius: 2px;
	}
	.faction-stats {
		display: flex;
		gap: 12px;
		font-size: 9px;
		color: var(--text-dim);
		margin-top: 3px;
	}

	/* Belief axes mini-bars (Item 18) */
	.belief-axes {
		margin-top: 6px;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.belief-axis-row {
		display: flex;
		align-items: center;
		gap: 4px;
		font-size: 8px;
	}
	.belief-axis-label { width: 24px; text-align: right; font-weight: bold; }
	.belief-axis-track {
		flex: 1;
		height: 5px;
		background: var(--bg-primary);
		border-radius: 2px;
		overflow: hidden;
		position: relative;
	}
	.belief-axis-fill {
		position: absolute;
		height: 100%;
		border-radius: 2px;
		transition: width 0.3s ease;
	}
	.belief-axis-center {
		position: absolute;
		left: 50%;
		top: 0;
		bottom: 0;
		width: 1px;
		background: rgba(255, 255, 255, 0.15);
	}
	.belief-axis-val { width: 32px; text-align: right; }

	/* Death cause bars (Item 14) */
	.death-bars {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.death-row {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 9px;
	}
	.death-label { width: 70px; color: var(--text-dim); text-align: right; }
	.death-track {
		flex: 1;
		height: 8px;
		background: var(--bg-secondary);
		border-radius: 4px;
		overflow: hidden;
	}
	.death-fill {
		height: 100%;
		border-radius: 4px;
		transition: width 0.3s ease;
	}
	.death-val { width: 28px; text-align: right; font-weight: bold; }

	/* Tech progress bars (Item 16) */
	.tech-bars {
		display: flex;
		flex-direction: column;
		gap: 5px;
	}
	.tech-row {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 9px;
	}
	.tech-label {
		width: 80px;
		color: var(--text-dim);
		text-align: right;
		text-transform: capitalize;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.tech-track {
		flex: 1;
		height: 8px;
		background: var(--bg-secondary);
		border-radius: 4px;
		overflow: hidden;
	}
	.tech-fill {
		height: 100%;
		border-radius: 4px;
		transition: width 0.3s ease;
	}
	.tech-fill.unlocked {
		box-shadow: 0 0 4px rgba(0, 255, 136, 0.4);
	}
	.tech-val { width: 30px; text-align: right; font-weight: bold; }

	/* War detail panel */
	.war-card {
		border-color: rgba(255, 68, 102, 0.15);
	}
	.war-list {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.war-item {
		padding: 8px;
		background: var(--bg-secondary);
		border: 1px solid rgba(255, 68, 102, 0.1);
		border-radius: 3px;
	}
	.war-header {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 8px;
		margin-bottom: 8px;
	}
	.war-faction {
		font-size: 11px;
		font-weight: bold;
		max-width: 120px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.war-vs {
		font-size: 9px;
		color: var(--red-warning);
		font-weight: bold;
		letter-spacing: 2px;
	}
	.war-row {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 9px;
		margin-bottom: 6px;
	}
	.war-label { width: 60px; color: var(--text-dim); text-align: right; }
	.war-intensity-track {
		flex: 1;
		height: 6px;
		background: var(--bg-primary);
		border-radius: 3px;
		overflow: hidden;
	}
	.war-intensity-fill {
		height: 100%;
		border-radius: 3px;
		transition: width 0.3s ease;
	}
	.war-val { width: 30px; text-align: right; font-weight: bold; }
	.war-casualties {
		display: flex;
		flex-direction: column;
		gap: 3px;
		margin-bottom: 6px;
	}
	.war-cas-side {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 9px;
	}
	.war-cas-label {
		width: 80px;
		color: var(--text-dim);
		text-align: right;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.war-cas-track {
		flex: 1;
		height: 6px;
		background: var(--bg-primary);
		border-radius: 3px;
		overflow: hidden;
	}
	.war-cas-fill {
		height: 100%;
		border-radius: 3px;
		transition: width 0.3s ease;
	}
	.war-cas-fill.cas-a { background: #ff4466; }
	.war-cas-fill.cas-b { background: #ff8844; }
	.war-cas-count {
		width: 24px;
		text-align: right;
		color: var(--red-warning);
		font-weight: bold;
	}
	.war-footer {
		display: flex;
		gap: 10px;
		font-size: 8px;
		color: var(--text-muted);
		letter-spacing: 1px;
	}

	/* ── Mobile: charts panel becomes bottom sheet ── */
	@media (max-width: 768px) {
		.charts-panel {
			width: 100%;
			top: auto;
			bottom: 0;
			max-height: 75vh;
			border-left: none;
			border-top: 1px solid var(--green-dim);
			border-radius: 12px 12px 0 0;
		}
	}
</style>
