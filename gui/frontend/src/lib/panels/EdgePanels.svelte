<script lang="ts">
	import {
		stats, matrixState, factions, economyStats,
		emotionStats, events, breakthroughs, tickHistory, population
	} from '$lib/stores/simulation';
	import { edgePanelVisibility, zoomLevel } from '$lib/stores/ui';
	import DemiurgeHUD from '$lib/panels/DemiurgeHUD.svelte';
	import ZoomSelector from '$lib/panels/ZoomSelector.svelte';

	// Derived values
	let historySparkline = $derived(
		$tickHistory.slice(-50).map((h) => h.alive)
	);

	// ── Virtual scrolling for feed ──
	const ITEM_HEIGHT = 24;
	const BUFFER = 4;
	let feedContainer = $state<HTMLDivElement | null>(null);
	let feedScrollTop = $state(0);

	// Events in reverse chronological order
	let allEvents = $derived($events.slice().reverse());

	let feedViewport = $derived.by(() => {
		const containerH = feedContainer?.clientHeight ?? 120;
		const total = allEvents.length;
		const visibleCount = Math.ceil(containerH / ITEM_HEIGHT) + BUFFER * 2;
		const startIdx = Math.max(0, Math.floor(feedScrollTop / ITEM_HEIGHT) - BUFFER);
		const endIdx = Math.min(total, startIdx + visibleCount);
		return {
			total,
			startIdx,
			endIdx,
			spacerTop: startIdx * ITEM_HEIGHT,
			spacerBottom: Math.max(0, (total - endIdx) * ITEM_HEIGHT),
			items: allEvents.slice(startIdx, endIdx)
		};
	});

	function onFeedScroll(e: Event) {
		feedScrollTop = (e.target as HTMLDivElement).scrollTop;
	}
</script>

{#if $zoomLevel === 1}
	<!-- LEFT: Society Panel -->
	<div class="edge-panel left" class:visible={$edgePanelVisibility.left}>
		<div class="panel-header">SOCIETY</div>

		<div class="panel-section">
			<div class="metric-row">
				<span class="label">POPULATION</span>
				<span class="value">{$stats.alive_count}</span>
			</div>
			<div class="metric-row">
				<span class="label">AVG GEN</span>
				<span class="value">{$stats.avg_generation.toFixed(1)}</span>
			</div>
			{#each Object.entries($stats.phase_counts || {}) as [phase, count]}
				<div class="metric-row sub">
					<span class="label">{phase}</span>
					<span class="value dim">{count}</span>
				</div>
			{/each}
		</div>

		<div class="panel-section">
			<div class="section-title">FACTIONS ({$factions.length})</div>
			{#each $factions.slice(0, 5) as faction}
				<div class="faction-item">
					<span class="faction-name">{faction.name || `Faction #${faction.id}`}</span>
					<span class="dim">x{faction.member_count || '?'}</span>
					{#if faction.at_war}<span class="text-red">WAR</span>{/if}
				</div>
			{/each}
		</div>

		<div class="panel-section">
			<div class="section-title">TECH</div>
			{#each $breakthroughs.slice(-5) as bt}
				<div class="tech-item">{bt}</div>
			{/each}
			{#if $breakthroughs.length === 0}
				<span class="dim">No breakthroughs yet</span>
			{/if}
		</div>
	</div>

	<!-- RIGHT: Matrix Panel -->
	<div class="edge-panel right" class:visible={$edgePanelVisibility.right}>
		<div class="panel-header" style="color: var(--system-color);">THE MATRIX</div>

		<div class="panel-section">
			<div class="section-title">ZOOM</div>
			<ZoomSelector />
		</div>

		<div class="panel-section">
			<div class="control-gauge">
				<div class="gauge-label">CONTROL INDEX</div>
				<div class="gauge-bar">
					<div
						class="gauge-fill"
						style="width: {$matrixState.control_index * 100}%; background: {
							$matrixState.control_index > 0.7 ? 'var(--system-color)' :
							$matrixState.control_index > 0.4 ? '#ffaa00' : 'var(--red-warning)'
						};"
					></div>
				</div>
				<div class="gauge-value">{($matrixState.control_index * 100).toFixed(1)}%</div>
			</div>
		</div>

		<div class="panel-section">
			<div class="metric-row">
				<span class="label">CYCLE</span>
				<span class="value">{$matrixState.cycle_number}</span>
			</div>
			<div class="metric-row">
				<span class="label">SENTINELS</span>
				<span class="value" style="color: #ff0000;">{$matrixState.sentinels_deployed}</span>
			</div>
			<div class="metric-row">
				<span class="label">GLITCHES</span>
				<span class="value">{$matrixState.glitches_this_cycle}</span>
			</div>
			<div class="metric-row">
				<span class="label">ANOMALY</span>
				<span class="value" style="color: var(--gold);">
					{$matrixState.anomaly_id ? `#${$matrixState.anomaly_id}` : 'NONE'}
				</span>
			</div>
		</div>

		<div class="panel-section">
			<div class="section-title">AWARENESS</div>
			<div class="metric-row">
				<span class="label">TOTAL</span>
				<span class="value">{$matrixState.total_awareness.toFixed(1)}</span>
			</div>
		</div>
	</div>

	<!-- TOP: Knowledge + Architect Panel -->
	<div class="edge-panel top" class:visible={$edgePanelVisibility.top}>
		<div class="top-row">
			<div class="top-col">
				<div class="panel-header">KNOWLEDGE</div>
				<div class="panel-section horizontal">
					<div class="metric-col">
						<span class="label">AVG IQ</span>
						<span class="value large">{$stats.avg_intelligence.toFixed(3)}</span>
					</div>
					<div class="metric-col">
						<span class="label">AVG HP</span>
						<span class="value large">{$stats.avg_health.toFixed(3)}</span>
					</div>
					<div class="metric-col">
						<span class="label">BIRTHS</span>
						<span class="value large">{$stats.births}</span>
					</div>
					<div class="metric-col">
						<span class="label">DEATHS</span>
						<span class="value large">{$stats.deaths}</span>
					</div>
				</div>
			</div>
			<div class="top-col architect">
				<div class="panel-header">ARCHITECT</div>
				<DemiurgeHUD />
			</div>
		</div>
	</div>

	<!-- BOTTOM: Feed Panel (virtual scrolled) -->
	<div class="edge-panel bottom" class:visible={$edgePanelVisibility.bottom}>
		<div class="feed-scroll" bind:this={feedContainer} onscroll={onFeedScroll}>
			{#if allEvents.length === 0}
				<span class="dim" style="padding: 8px;">Awaiting events...</span>
			{:else}
				<div style="height: {feedViewport.spacerTop}px;"></div>
				{#each feedViewport.items as evt}
					<div class="feed-item" style="height: {ITEM_HEIGHT}px;" class:birth={evt.type === 'birth'} class:death={evt.type === 'death'} class:tech={evt.type === 'tech'} class:matrix={evt.type === 'matrix'}>
						<span class="feed-tick">t={evt.tick}</span>
						<span>{evt.text}</span>
					</div>
				{/each}
				<div style="height: {feedViewport.spacerBottom}px;"></div>
			{/if}
		</div>
	</div>
{/if}

<style>
	.edge-panel {
		position: fixed;
		background: var(--bg-panel);
		backdrop-filter: blur(8px);
		border: 1px solid rgba(0, 255, 136, 0.1);
		z-index: 10;
		transition: transform 0.25s ease, opacity 0.25s ease;
		overflow-y: auto;
		font-size: 11px;
	}

	/* Left */
	.edge-panel.left {
		left: 0;
		top: 0;
		bottom: 0;
		width: var(--panel-width);
		transform: translateX(-100%);
		opacity: 0;
		padding: 12px;
		border-right: 1px solid rgba(0, 255, 136, 0.15);
	}
	.edge-panel.left.visible { transform: translateX(0); opacity: 1; }

	/* Right */
	.edge-panel.right {
		right: 0;
		top: 0;
		bottom: 0;
		width: var(--panel-width);
		transform: translateX(100%);
		opacity: 0;
		padding: 12px;
		border-left: 1px solid rgba(0, 170, 204, 0.15);
	}
	.edge-panel.right.visible { transform: translateX(0); opacity: 1; }

	/* Top */
	.edge-panel.top {
		top: 0;
		left: var(--panel-width);
		right: var(--panel-width);
		height: 110px;
		transform: translateY(-100%);
		opacity: 0;
		padding: 10px 20px;
		border-bottom: 1px solid rgba(0, 255, 136, 0.1);
	}
	.edge-panel.top.visible { transform: translateY(0); opacity: 1; }

	.top-row {
		display: flex;
		gap: 24px;
		align-items: flex-start;
		justify-content: space-between;
		height: 100%;
	}
	.top-col {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}
	.top-col.architect {
		align-items: flex-end;
	}
	.top-col.architect .panel-header { text-align: right; }

	/* Bottom */
	.edge-panel.bottom {
		bottom: 0;
		left: var(--panel-width);
		right: var(--panel-width);
		height: 120px;
		transform: translateY(100%);
		opacity: 0;
		border-top: 1px solid rgba(0, 255, 136, 0.1);
	}
	.edge-panel.bottom.visible { transform: translateY(0); opacity: 1; }

	.panel-header {
		font-size: 12px;
		font-weight: bold;
		letter-spacing: 3px;
		color: var(--green-primary);
		padding-bottom: 8px;
		border-bottom: 1px solid var(--green-dim);
		margin-bottom: 10px;
	}

	.panel-section {
		margin-bottom: 12px;
	}
	.panel-section.horizontal {
		display: flex;
		gap: 20px;
		justify-content: center;
	}

	.section-title {
		font-size: 10px;
		letter-spacing: 2px;
		color: var(--text-dim);
		margin-bottom: 6px;
	}

	.metric-row {
		display: flex;
		justify-content: space-between;
		padding: 2px 0;
	}
	.metric-row.sub { padding-left: 12px; }
	.label { color: var(--text-dim); }
	.value { color: var(--green-primary); font-weight: 500; }
	.value.dim { color: var(--text-dim); }
	.value.large { font-size: 16px; }

	.metric-col {
		text-align: center;
	}
	.metric-col .label { display: block; margin-bottom: 4px; }

	.faction-item {
		display: flex;
		gap: 8px;
		padding: 2px 0;
	}
	.faction-name {
		color: var(--cyan);
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.tech-item {
		color: var(--gold);
		padding: 1px 0;
	}
	.tech-item::before { content: '◆ '; color: var(--gold-dim); }

	.dim { color: var(--text-dim); }

	/* Control gauge */
	.control-gauge { text-align: center; }
	.gauge-label { font-size: 10px; letter-spacing: 2px; color: var(--text-dim); margin-bottom: 6px; }
	.gauge-bar {
		height: 12px;
		background: var(--bg-primary);
		border-radius: 6px;
		overflow: hidden;
		margin: 6px 0;
	}
	.gauge-fill {
		height: 100%;
		border-radius: 6px;
		transition: width 0.5s ease, background 0.5s ease;
	}
	.gauge-value { font-size: 18px; font-weight: bold; }

	/* Feed */
	.feed-scroll {
		height: 100%;
		overflow-y: auto;
		padding: 8px 12px;
	}
	.feed-item {
		padding: 2px 0;
		border-bottom: 1px solid rgba(0, 255, 136, 0.03);
	}
	.feed-tick { color: var(--text-dim); margin-right: 6px; font-size: 10px; }
	.feed-item.birth { color: var(--phase-infant); }
	.feed-item.death { color: var(--red-warning); }
	.feed-item.tech { color: var(--gold); }
	.feed-item.matrix { color: var(--system-color); }

	/* ── Mobile: panels become overlays ── */
	@media (max-width: 768px) {
		.edge-panel.left,
		.edge-panel.right {
			width: 100%;
			height: 50vh;
			top: auto;
			bottom: 0;
		}
		.edge-panel.left {
			border-right: none;
			border-top: 1px solid rgba(0, 255, 136, 0.15);
			transform: translateY(100%);
		}
		.edge-panel.left.visible { transform: translateY(0); }

		.edge-panel.right {
			border-left: none;
			border-top: 1px solid rgba(0, 170, 204, 0.15);
			transform: translateY(100%);
		}
		.edge-panel.right.visible { transform: translateY(0); }

		.edge-panel.top {
			left: 0;
			right: 0;
			height: auto;
			min-height: 60px;
		}
		.panel-section.horizontal {
			flex-wrap: wrap;
			gap: 10px;
		}
		.metric-col .value.large { font-size: 13px; }

		.edge-panel.bottom {
			left: 0;
			right: 0;
			height: 100px;
		}
	}
</style>
