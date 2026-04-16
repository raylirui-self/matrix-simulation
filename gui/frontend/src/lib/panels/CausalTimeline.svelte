<!--
  CausalTimeline.svelte — Phase 7B horizontal event timeline.
  Shows the recent "major" causal events from /api/sim/{id}/causal/events
  as colored nodes on a horizontally-scrolling strip. The current tick is
  pinned to the right edge. Click a node to fetch + display its full
  ancestor+descendant chain via /causal/events/{id}/chain.
-->
<script lang="ts">
	import { onMount } from 'svelte';
	import { tick as tickStore, runId } from '$lib/stores/simulation';
	import { causalTimelineOpen, zoomLevel } from '$lib/stores/ui';
	import { api } from '$lib/api/rest';

	type CausalEvent = {
		event_id: number;
		tick: number;
		event_type: string;
		description: string;
		agent_id: number | null;
		caused_by: number | null;
		details: Record<string, any>;
	};

	let events = $state<CausalEvent[]>([]);
	let selected = $state<CausalEvent | null>(null);
	let chain = $state<{ ancestors: CausalEvent[]; descendants: CausalEvent[] } | null>(null);
	let loadingChain = $state(false);
	let lastFetchTick = $state(-1);
	let fetchInFlight = false;

	// Color lookup by event type — keep it simple, visually legible.
	const TYPE_COLORS: Record<string, string> = {
		birth: '#66ff88',
		death: '#ff4466',
		breakthrough: '#00ddff',
		faction_founded: '#ffd700',
		faction_dissolved: '#aa8800',
		war_started: '#ff2233',
		war_ended: '#cc6644',
		anomaly_designated: '#ff66ff',
		cycle_reset: '#ffffff',
		redpill: '#ff3355',
		jack_out: '#44ccff',
		jack_in: '#ccaaff',
		archon_destroyed: '#ffaa00'
	};
	const DEFAULT_COLOR = '#888888';

	async function fetchRecentEvents() {
		if (fetchInFlight || !$runId) return;
		fetchInFlight = true;
		try {
			const data = await api.getCausalEvents($runId, 0, 200);
			events = data.events;
			lastFetchTick = data.current_tick;
		} catch (e) {
			console.warn('causal events fetch failed:', e);
		} finally {
			fetchInFlight = false;
		}
	}

	async function selectEvent(evt: CausalEvent) {
		selected = evt;
		chain = null;
		if (!$runId) return;
		loadingChain = true;
		try {
			const data = await api.getCausalChain($runId, evt.event_id);
			chain = { ancestors: data.ancestors, descendants: data.descendants };
		} catch (e) {
			console.warn('causal chain fetch failed:', e);
		} finally {
			loadingChain = false;
		}
	}

	function closeDetail() {
		selected = null;
		chain = null;
	}

	// Refetch whenever the panel opens, and periodically as ticks advance.
	$effect(() => {
		if ($causalTimelineOpen && $zoomLevel === 1) {
			const t = $tickStore;
			// Poll on first open, then every 5 ticks.
			if (t === 0 || t - lastFetchTick >= 5 || events.length === 0) {
				fetchRecentEvents();
			}
		}
	});

	// Maps a tick to an x-offset within the strip — current tick pinned right.
	function tickToX(eventTick: number, currentTick: number, stripWidth: number): number {
		const windowSize = 200; // ticks shown across the strip
		const rightEdge = stripWidth - 20;
		const leftEdge = 20;
		const clamped = Math.max(0, Math.min(windowSize, currentTick - eventTick));
		return rightEdge - (clamped / windowSize) * (rightEdge - leftEdge);
	}

	onMount(() => {
		if ($causalTimelineOpen) fetchRecentEvents();
	});
</script>

{#if $causalTimelineOpen && $zoomLevel === 1}
	<div class="causal-timeline" role="region" aria-label="Causal event timeline">
		<div class="timeline-header">
			<span class="title">CAUSAL TIMELINE</span>
			<span class="subtitle">
				{events.length} events · tick {lastFetchTick < 0 ? '—' : lastFetchTick}
			</span>
			<button class="close" onclick={() => causalTimelineOpen.set(false)} aria-label="Close timeline">
				✕
			</button>
		</div>
		<div class="strip-wrap">
			<!-- Keyboard-accessible click targets layered over the SVG nodes.
			     Using real <button>s gets a11y right (focus, Enter/Space, screen
			     readers) without wrestling SVG click handlers. -->
			{#each events as evt (evt.event_id)}
				{@const x = tickToX(evt.tick, Math.max($tickStore, lastFetchTick), 1200)}
				{@const leftPct = (x / 1200) * 100}
				<button
					type="button"
					class="event-hit"
					class:selected={selected?.event_id === evt.event_id}
					style="left: {leftPct}%;"
					title="{evt.event_type} t={evt.tick}: {evt.description}"
					onclick={() => selectEvent(evt)}
					aria-label="{evt.event_type} at tick {evt.tick}"
				></button>
			{/each}
			<svg class="strip" viewBox="0 0 1200 60" preserveAspectRatio="none">
				<!-- Base line -->
				<line x1="20" y1="30" x2="1180" y2="30" stroke="#333" stroke-width="1" />
				<!-- Current-tick marker on the right edge -->
				<line x1="1180" y1="10" x2="1180" y2="50" stroke="#00ff88" stroke-width="1.5" />
				<text x="1180" y="8" text-anchor="end" fill="#00ff88" font-size="9">NOW</text>

				<!-- Parent → child causal links (rendered before nodes so nodes sit on top) -->
				{#each events as evt (evt.event_id)}
					{#if evt.caused_by !== null}
						{@const parent = events.find((e) => e.event_id === evt.caused_by)}
						{#if parent}
							{@const lcolor = TYPE_COLORS[evt.event_type] || DEFAULT_COLOR}
							{@const lx = tickToX(evt.tick, Math.max($tickStore, lastFetchTick), 1200)}
							{@const lpx = tickToX(parent.tick, Math.max($tickStore, lastFetchTick), 1200)}
							<line
								x1={lpx}
								y1={30}
								x2={lx}
								y2={30}
								stroke={lcolor}
								stroke-width="0.6"
								opacity="0.4"
							/>
						{/if}
					{/if}
				{/each}
				<!-- Nodes — kept as plain circles; clicks are handled by the
				     button overlay below (a11y-friendlier than SVG click). -->
				{#each events as evt (evt.event_id)}
					{@const color = TYPE_COLORS[evt.event_type] || DEFAULT_COLOR}
					{@const x = tickToX(evt.tick, Math.max($tickStore, lastFetchTick), 1200)}
					<circle
						cx={x}
						cy={30}
						r={selected?.event_id === evt.event_id ? 5 : 3}
						fill={color}
						opacity="0.9"
					/>
				{/each}
			</svg>
		</div>

		{#if selected}
			<div class="detail">
				<div class="detail-header">
					<span class="type-tag" style="color: {TYPE_COLORS[selected.event_type] || DEFAULT_COLOR}">
						{selected.event_type}
					</span>
					<span class="detail-tick">t={selected.tick}</span>
					<button class="close" onclick={closeDetail} aria-label="Close detail">✕</button>
				</div>
				<div class="detail-desc">{selected.description}</div>
				{#if loadingChain}
					<div class="chain-loading">loading chain…</div>
				{:else if chain}
					<div class="chain">
						{#if chain.ancestors.length > 0}
							<div class="chain-row">
								<span class="chain-label">causes:</span>
								{#each chain.ancestors as a (a.event_id)}
									<span class="chain-node" style="color: {TYPE_COLORS[a.event_type] || DEFAULT_COLOR}">
										{a.event_type}(t{a.tick})
									</span>
								{/each}
							</div>
						{/if}
						{#if chain.descendants.length > 0}
							<div class="chain-row">
								<span class="chain-label">effects:</span>
								{#each chain.descendants as d (d.event_id)}
									<span class="chain-node" style="color: {TYPE_COLORS[d.event_type] || DEFAULT_COLOR}">
										{d.event_type}(t{d.tick})
									</span>
								{/each}
							</div>
						{/if}
						{#if chain.ancestors.length === 0 && chain.descendants.length === 0}
							<div class="chain-empty">no linked events</div>
						{/if}
					</div>
				{/if}
			</div>
		{/if}
	</div>
{/if}

<style>
	.causal-timeline {
		position: fixed;
		left: 20px;
		right: 420px;
		bottom: 78px;
		max-height: 180px;
		background: rgba(6, 12, 8, 0.88);
		border: 1px solid rgba(0, 255, 136, 0.22);
		border-radius: 4px;
		z-index: 21;
		font-family: var(--font-mono, 'JetBrains Mono', monospace);
		backdrop-filter: blur(6px);
		padding: 6px 10px 8px;
		pointer-events: auto;
	}
	.timeline-header {
		display: flex;
		align-items: center;
		gap: 10px;
		margin-bottom: 4px;
	}
	.title {
		font-size: 10px;
		letter-spacing: 2px;
		color: #00ff88;
	}
	.subtitle {
		font-size: 9px;
		color: #6a8a7a;
		flex: 1;
	}
	.close {
		background: none;
		border: none;
		color: #6a8a7a;
		font-size: 11px;
		cursor: pointer;
		padding: 0 4px;
	}
	.close:hover {
		color: #00ff88;
	}
	.strip-wrap {
		position: relative;
		width: 100%;
		height: 56px;
		overflow: hidden;
	}
	.strip {
		width: 100%;
		height: 100%;
	}
	.event-hit {
		position: absolute;
		top: 15px;
		width: 14px;
		height: 28px;
		margin-left: -7px;
		background: transparent;
		border: none;
		padding: 0;
		cursor: pointer;
		z-index: 2;
	}
	.event-hit:focus-visible {
		outline: 1px solid #00ff88;
		outline-offset: 1px;
	}
	.event-hit.selected {
		outline: 1px dashed rgba(0, 255, 136, 0.6);
	}
	.detail {
		border-top: 1px solid rgba(0, 255, 136, 0.15);
		margin-top: 4px;
		padding-top: 4px;
		max-height: 80px;
		overflow-y: auto;
	}
	.detail-header {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 10px;
	}
	.type-tag {
		letter-spacing: 1px;
		text-transform: uppercase;
	}
	.detail-tick {
		color: #6a8a7a;
		flex: 1;
	}
	.detail-desc {
		font-size: 10px;
		color: #c0ddc8;
		margin: 2px 0 4px;
	}
	.chain-row {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		font-size: 9px;
		margin: 2px 0;
	}
	.chain-label {
		color: #6a8a7a;
	}
	.chain-node {
		opacity: 0.9;
	}
	.chain-loading,
	.chain-empty {
		font-size: 9px;
		color: #6a8a7a;
	}

	@media (max-width: 768px) {
		.causal-timeline {
			right: 20px;
			bottom: 60px;
			max-height: 140px;
		}
	}
</style>
