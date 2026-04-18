<!--
  DemiurgeAlertDot.svelte — tiny, unobtrusive, always-visible corner indicator.
  Shows only when the Architect's mood has a time-critical spike (fear > 0.6).
  Full HUD bars are inside the top edge panel (hover-to-reveal).
-->
<script lang="ts">
	import { matrixState } from '$lib/stores/simulation';

	let fear = $derived($matrixState.demiurge?.fear ?? 0);
	let pride = $derived($matrixState.demiurge?.pride ?? 0);
	let confusion = $derived($matrixState.demiurge?.confusion ?? 0);

	// Dot color reflects dominant spike; only render when there IS a spike.
	let alert = $derived.by(() => {
		if (fear > 0.6) return { color: '#ff3355', label: 'Architect: fear spike' };
		if (confusion > 0.7) return { color: '#00ddff', label: 'Architect: confusion spike' };
		if (pride > 0.85) return { color: '#ffd700', label: 'Architect: pride surge' };
		return null;
	});
</script>

{#if alert}
	<div
		class="dot"
		style="--c: {alert.color};"
		title={alert.label}
		aria-label={alert.label}
	></div>
{/if}

<style>
	.dot {
		position: fixed;
		top: 10px;
		right: 10px;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--c);
		box-shadow: 0 0 6px var(--c), 0 0 12px color-mix(in srgb, var(--c) 60%, transparent);
		z-index: 30;
		pointer-events: none;
		animation: pulse 1.4s ease-in-out infinite;
	}
	@keyframes pulse {
		0%, 100% { opacity: 0.55; }
		50% { opacity: 1; }
	}
</style>
