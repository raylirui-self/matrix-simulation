<script lang="ts">
	import { stats, matrixState, breakthroughs, tick } from '$lib/stores/simulation';

	const ERAS = [
		{ name: 'Industrial Age', color: '#ffd700', desc: 'Machines reshape the world', check: (s: any, techs: string[]) => techs.includes('industrialization') },
		{ name: 'Trade Era', color: '#00ccff', desc: 'Commerce connects communities', check: (s: any, techs: string[]) => techs.includes('trade_networks') },
		{ name: 'Bronze Age', color: '#cd7f32', desc: 'Metal tools forge a new world', check: (s: any, techs: string[]) => techs.includes('mining') },
		{ name: 'Agricultural Age', color: '#4a7a3a', desc: 'Settled life begins', check: (s: any, techs: string[]) => techs.includes('agriculture') },
		{ name: 'Age of Awakening', color: '#aa66ff', desc: 'Knowledge grows rapidly', check: (s: any) => s.avg_intelligence > 0.3 },
		{ name: 'Tribal Expansion', color: '#ff8844', desc: 'Clans spread across the land', check: (s: any) => s.alive_count > 80 },
		{ name: 'Dawn of Tribes', color: '#00ff88', desc: 'Small groups form bonds', check: (s: any) => s.alive_count > 20 },
		{ name: 'Genesis', color: '#5a8a5a', desc: 'Life stirs in the void', check: (s: any) => s.alive_count > 0 },
		{ name: 'The Void', color: '#ff4466', desc: 'Nothing remains...', check: () => true },
	];

	let currentEra = $derived.by(() => {
		const s = $stats;
		const techs = $breakthroughs;
		for (const era of ERAS) {
			if (era.check(s, techs)) return era;
		}
		return ERAS[ERAS.length - 1];
	});
</script>

<div class="era-strip" style="--era-color: {currentEra.color};">
	<span class="era-label">{currentEra.name}</span>
	<span class="era-sep">|</span>
	<span class="era-desc">{currentEra.desc}</span>
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
