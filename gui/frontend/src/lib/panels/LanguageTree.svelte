<!--
  LanguageTree.svelte — Phase 7C branching tree diagram showing how faction
  dialects diverged from a common root. Toggle with Y key.
  Branch thickness proportional to speaker count. Dead branches in grey.
  Language artifacts marked as preserved branches that survived cycle resets.
-->
<script lang="ts">
	import { runId, tick as tickStore } from '$lib/stores/simulation';
	import { zoomLevel } from '$lib/stores/ui';
	import { api } from '$lib/api/rest';

	let { open = $bindable(false) } = $props();

	type LanguageBranch = {
		faction_id: number;
		name: string;
		dialect_offset: number;
		concept_usage: Record<string, number>;
		speaker_count: number;
		extinct: boolean;
		language_artifacts: Array<{
			faction_name: string;
			cycle_number: number;
			concept_count: number;
			contains_awareness_clues: boolean;
		}>;
	};

	let branches = $state<LanguageBranch[]>([]);
	let encryptionLevel = $state(0);
	let decryptionLevel = $state(0);
	let lastFetchTick = $state(-1);
	let fetchInFlight = false;
	// L-3: surface fetch failures so the panel doesn't look mysteriously
	// empty when the endpoint is unavailable on an older backend.
	let fetchError = $state<string | null>(null);

	async function fetchLanguage() {
		const rid = $runId;
		if (!rid || fetchInFlight) return;
		fetchInFlight = true;
		try {
			const data = await api.getLanguageTree(rid);
			branches = data.branches || [];
			encryptionLevel = data.encryption_level;
			decryptionLevel = data.decryption_level;
			lastFetchTick = $tickStore;
			fetchError = null;
		} catch (e) {
			fetchError = e instanceof Error ? e.message : 'Language tree unavailable';
		} finally {
			fetchInFlight = false;
		}
	}

	// Refetch every 20 ticks
	$effect(() => {
		const t = $tickStore;
		if (open && t > 0 && t - lastFetchTick >= 20) {
			fetchLanguage();
		}
	});

	// Fetch on open
	$effect(() => {
		if (open && $runId && lastFetchTick < 0) {
			fetchLanguage();
		}
	});

	// SVG dimensions
	const SVG_W = 360;
	const SVG_H = 280;
	const ROOT_X = SVG_W / 2;
	const ROOT_Y = 30;

	// Compute branch positions for the tree layout
	function branchLayout(branchList: LanguageBranch[]) {
		if (branchList.length === 0) return [];
		const sorted = [...branchList].sort((a, b) => a.dialect_offset - b.dialect_offset);
		const maxSpeakers = Math.max(1, ...sorted.map((b) => b.speaker_count));
		const spacing = (SVG_W - 60) / Math.max(1, sorted.length);

		return sorted.map((b, i) => {
			const tipX = 30 + spacing * i + spacing / 2;
			const tipY = SVG_H - 40;
			const thickness = Math.max(1, (b.speaker_count / maxSpeakers) * 6);
			return { ...b, tipX, tipY, thickness };
		});
	}
</script>

{#if open && $zoomLevel === 1}
	<div class="lang-tree-panel">
		<div class="panel-header">
			<span class="title">LANGUAGE EVOLUTION</span>
			<button class="close-btn" onclick={() => (open = false)}>×</button>
		</div>

		{#if fetchError}
			<div class="fetch-error">Language tree unavailable — {fetchError}</div>
		{/if}

		<svg viewBox="0 0 {SVG_W} {SVG_H}" class="tree-svg">
			<!-- Root node -->
			<circle cx={ROOT_X} cy={ROOT_Y} r="5" fill="#00ff88" opacity="0.7" />
			<text x={ROOT_X} y={ROOT_Y - 10} fill="#00ff88" font-size="8" text-anchor="middle"
				opacity="0.5">COMMON ROOT</text>

			<!-- Branches -->
			{#each branchLayout(branches) as b}
				{@const strokeColor = b.extinct ? '#555' : '#00ff88'}
				{@const strokeOpacity = b.extinct ? 0.3 : 0.7}
				<!-- Branch line from root to tip -->
				<path
					d="M {ROOT_X} {ROOT_Y} Q {(ROOT_X + b.tipX) / 2} {(ROOT_Y + b.tipY) / 2 - 20} {b.tipX} {b.tipY}"
					fill="none"
					stroke={strokeColor}
					stroke-width={b.thickness}
					opacity={strokeOpacity}
				/>
				<!-- Branch tip -->
				<circle cx={b.tipX} cy={b.tipY} r={Math.max(3, b.thickness)}
					fill={b.extinct ? '#555' : '#00ff88'} opacity={strokeOpacity} />
				<!-- Label -->
				<text x={b.tipX} y={b.tipY + 14} fill={b.extinct ? '#666' : '#00ff88'}
					font-size="7" text-anchor="middle" opacity="0.8">
					{b.name.length > 10 ? b.name.slice(0, 10) + '..' : b.name}
				</text>
				<text x={b.tipX} y={b.tipY + 23} fill="#888"
					font-size="6" text-anchor="middle">
					{b.extinct ? 'EXTINCT' : `${b.speaker_count} speakers`}
				</text>
				<!-- Language artifact marker (preserved branch) -->
				{#each b.language_artifacts as la, lai}
					{@const markerY = b.tipY - 15 - lai * 12}
					<rect x={b.tipX - 4} y={markerY - 4} width="8" height="8"
						fill="none" stroke="#ffd700" stroke-width="0.8" opacity="0.6"
						rx="1" />
					<text x={b.tipX + 7} y={markerY + 3} fill="#ffd700" font-size="5"
						opacity="0.5">C{la.cycle_number}</text>
				{/each}
			{/each}
		</svg>

		<!-- Encryption arms race bar -->
		<div class="arms-race">
			<div class="arms-label">Encryption vs Decryption</div>
			<div class="arms-bar">
				<div class="enc-fill" style:width="{encryptionLevel * 100}%"></div>
				<div class="dec-fill" style:width="{decryptionLevel * 100}%"></div>
			</div>
			<div class="arms-labels">
				<span class="enc-label">Resistance {(encryptionLevel * 100).toFixed(0)}%</span>
				<span class="dec-label">Sentinel {(decryptionLevel * 100).toFixed(0)}%</span>
			</div>
		</div>
	</div>
{/if}

<style>
	.lang-tree-panel {
		position: fixed;
		right: 20px;
		top: 80px;
		width: 380px;
		background: rgba(6, 18, 6, 0.94);
		border: 1px solid rgba(0, 255, 136, 0.3);
		border-radius: 6px;
		z-index: 50;
		padding: 8px;
		font-family: 'JetBrains Mono', monospace;
		color: #00ff88;
	}
	.panel-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 4px;
	}
	.title {
		font-size: 11px;
		letter-spacing: 1px;
		opacity: 0.7;
	}
	.close-btn {
		background: none;
		border: none;
		color: #00ff88;
		font-size: 16px;
		cursor: pointer;
		opacity: 0.6;
		padding: 0 4px;
	}
	.close-btn:hover {
		opacity: 1;
	}
	.tree-svg {
		width: 100%;
		height: auto;
	}
	.fetch-error {
		font-size: 10px;
		color: #ffaa55;
		padding: 4px 6px;
		margin-bottom: 4px;
		border: 1px solid rgba(255, 170, 85, 0.4);
		border-radius: 3px;
		background: rgba(255, 170, 85, 0.08);
	}
	.arms-race {
		padding: 4px 8px 2px;
	}
	.arms-label {
		font-size: 8px;
		opacity: 0.5;
		text-align: center;
		margin-bottom: 3px;
	}
	.arms-bar {
		position: relative;
		height: 6px;
		background: rgba(255, 255, 255, 0.08);
		border-radius: 3px;
		overflow: hidden;
	}
	.enc-fill {
		position: absolute;
		left: 0;
		top: 0;
		height: 100%;
		background: rgba(0, 255, 136, 0.5);
		border-radius: 3px 0 0 3px;
	}
	.dec-fill {
		position: absolute;
		right: 0;
		top: 0;
		height: 100%;
		background: rgba(255, 50, 50, 0.4);
		border-radius: 0 3px 3px 0;
	}
	.arms-labels {
		display: flex;
		justify-content: space-between;
		font-size: 7px;
		opacity: 0.5;
		margin-top: 2px;
	}
	.enc-label {
		color: #00ff88;
	}
	.dec-label {
		color: #ff4466;
	}
</style>
