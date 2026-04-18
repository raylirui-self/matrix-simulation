<!--
  ZoomSelector.svelte — RAIN / GRID / CELL / SOUL level picker.
  Embedded in the right edge panel so it only shows when the user hovers
  that edge (Phase 7D layout fix). Canvas stays unobstructed at rest.
-->
<script lang="ts">
	import { agents } from '$lib/stores/simulation';
	import { zoomLevel, focusCell, focusAgentId } from '$lib/stores/ui';

	function goCell() {
		if (!$focusCell) focusCell.set({ row: 3, col: 3 });
		zoomLevel.set(2);
	}

	function goSoul() {
		if (!$focusAgentId) {
			const firstAgent = Array.from($agents.values())[0];
			if (firstAgent) {
				const row = Math.min(7, Math.floor(firstAgent.y * 8));
				const col = Math.min(7, Math.floor(firstAgent.x * 8));
				focusCell.set({ row, col });
				focusAgentId.set(firstAgent.id);
			}
		}
		zoomLevel.set(3);
	}
</script>

<div class="zoom-group" role="group" aria-label="Zoom level">
	<button class:active={$zoomLevel === 0} onclick={() => zoomLevel.set(0)}>RAIN</button>
	<button class:active={$zoomLevel === 1} onclick={() => zoomLevel.set(1)}>GRID</button>
	<button class:active={$zoomLevel === 2} class:disabled={!$focusCell} onclick={goCell}>CELL</button>
	<button class:active={$zoomLevel === 3} class:disabled={!$focusAgentId} onclick={goSoul}>SOUL</button>
</div>

<style>
	.zoom-group {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.zoom-group button {
		background: var(--bg-panel);
		border: 1px solid rgba(0, 255, 136, 0.1);
		color: var(--text-dim);
		font-family: var(--font-mono);
		font-size: 11px;
		letter-spacing: 1px;
		padding: 6px 12px;
		cursor: pointer;
		white-space: nowrap;
		text-align: left;
	}
	.zoom-group button.active {
		color: var(--green-primary);
		border-color: var(--green-primary);
		background: var(--green-dim);
	}
	.zoom-group button:hover { color: var(--green-primary); }
	.zoom-group button.disabled { opacity: 0.4; }
	.zoom-group button.disabled:hover { opacity: 0.7; }
</style>
