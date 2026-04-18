<script lang="ts">
	import { currentEra } from '$lib/stores/era';
</script>

<div class="era-strip" style="--era-color: {$currentEra.color};">
	<span class="era-label">{$currentEra.name}</span>
	<span class="era-sep">|</span>
	<span class="era-desc">{$currentEra.desc}</span>
</div>

<style>
	.era-strip {
		position: fixed;
		top: 0;
		left: 50%;
		transform: translateX(-50%);
		z-index: 15;
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 4px 16px;
		background: rgba(6, 18, 6, 0.85);
		backdrop-filter: blur(8px);
		border: 1px solid color-mix(in srgb, var(--era-color) 30%, transparent);
		border-top: none;
		border-radius: 0 0 6px 6px;
		font-size: 10px;
	}
	.era-label {
		color: var(--era-color);
		font-weight: bold;
		letter-spacing: 2px;
		text-transform: uppercase;
	}
	.era-sep { color: var(--text-muted); }
	.era-desc { color: var(--text-dim); font-style: italic; }
</style>
