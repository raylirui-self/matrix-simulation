<!--
  DemiurgeHUD.svelte — Architect psychology indicator.
  A compact tri-color "eye" showing fear/pride/confusion bars.
  Visible at every zoom level; reads matrixState.demiurge from the store.
-->
<script lang="ts">
	import { matrixState } from '$lib/stores/simulation';

	// Default to neutral mood if backend hasn't sent demiurge yet.
	let fear = $derived($matrixState.demiurge?.fear ?? 0);
	let pride = $derived($matrixState.demiurge?.pride ?? 0);
	let confusion = $derived($matrixState.demiurge?.confusion ?? 0);

	let dominant = $derived.by(() => {
		const entries: Array<[string, number]> = [
			['fear', fear],
			['pride', pride],
			['confusion', confusion]
		];
		entries.sort((a, b) => b[1] - a[1]);
		return entries[0];
	});
</script>

<div class="demiurge-hud" title="Architect mood — F:{fear.toFixed(2)} P:{pride.toFixed(2)} C:{confusion.toFixed(2)}">
	<div class="eye-wrap" class:panicked={fear > 0.6} class:proud={pride > 0.7 && fear < 0.3}>
		<svg viewBox="0 0 48 48" class="eye">
			<defs>
				<radialGradient id="dm-iris" cx="50%" cy="50%" r="50%">
					<stop offset="0%" stop-color="#111" stop-opacity="0.95" />
					<stop offset="60%" stop-color="#111" stop-opacity="0.7" />
					<stop offset="100%" stop-color="#000" stop-opacity="0" />
				</radialGradient>
			</defs>
			<!-- Outer ring pulses with dominant emotion -->
			<circle
				cx="24"
				cy="24"
				r="20"
				fill="none"
				stroke={dominant[0] === 'fear' ? '#ff3355' : dominant[0] === 'pride' ? '#ffd700' : '#00ddff'}
				stroke-width="1.5"
				opacity={0.35 + dominant[1] * 0.55}
			/>
			<!-- Fear arc (red) — top -->
			<path
				d="M 8 22 A 16 16 0 0 1 40 22"
				fill="none"
				stroke="#ff3355"
				stroke-width="3.5"
				stroke-linecap="round"
				stroke-dasharray="50.3"
				stroke-dashoffset={50.3 * (1 - fear)}
				opacity="0.85"
			/>
			<!-- Pride arc (gold) — bottom-right -->
			<path
				d="M 40 26 A 16 16 0 0 1 24 42"
				fill="none"
				stroke="#ffd700"
				stroke-width="3.5"
				stroke-linecap="round"
				stroke-dasharray="25.1"
				stroke-dashoffset={25.1 * (1 - pride)}
				opacity="0.85"
			/>
			<!-- Confusion arc (cyan) — bottom-left -->
			<path
				d="M 24 42 A 16 16 0 0 1 8 26"
				fill="none"
				stroke="#00ddff"
				stroke-width="3.5"
				stroke-linecap="round"
				stroke-dasharray="25.1"
				stroke-dashoffset={25.1 * (1 - confusion)}
				opacity="0.85"
			/>
			<!-- Iris -->
			<circle cx="24" cy="24" r="9" fill="url(#dm-iris)" />
			<circle
				cx="24"
				cy="24"
				r="3"
				fill={dominant[0] === 'fear' ? '#ff3355' : dominant[0] === 'pride' ? '#ffd700' : '#00ddff'}
			/>
		</svg>
	</div>
	<div class="bars">
		<div class="bar-row">
			<span class="label fear">FEAR</span>
			<div class="bar"><div class="fill fear" style="width: {fear * 100}%"></div></div>
		</div>
		<div class="bar-row">
			<span class="label pride">PRIDE</span>
			<div class="bar"><div class="fill pride" style="width: {pride * 100}%"></div></div>
		</div>
		<div class="bar-row">
			<span class="label conf">CONFUSION</span>
			<div class="bar"><div class="fill conf" style="width: {confusion * 100}%"></div></div>
		</div>
	</div>
</div>

<style>
	.demiurge-hud {
		position: fixed;
		top: 20px;
		left: 50%;
		transform: translateX(-50%);
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 6px 12px 6px 8px;
		background: rgba(6, 10, 6, 0.78);
		border: 1px solid rgba(0, 255, 136, 0.18);
		border-radius: 6px;
		z-index: 25;
		font-family: var(--font-mono, 'JetBrains Mono', monospace);
		backdrop-filter: blur(6px);
		pointer-events: auto;
	}
	.eye-wrap {
		width: 44px;
		height: 44px;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: filter 0.4s ease;
	}
	.eye-wrap.panicked {
		animation: pulse-fear 1.1s ease-in-out infinite;
	}
	.eye-wrap.proud {
		filter: drop-shadow(0 0 6px rgba(255, 215, 0, 0.6));
	}
	.eye {
		width: 100%;
		height: 100%;
	}
	.bars {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 120px;
	}
	.bar-row {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 9px;
		letter-spacing: 1px;
	}
	.label {
		width: 56px;
		color: rgba(255, 255, 255, 0.55);
	}
	.label.fear { color: #ff6680; }
	.label.pride { color: #ffd866; }
	.label.conf { color: #66e5ff; }
	.bar {
		flex: 1;
		height: 4px;
		background: rgba(255, 255, 255, 0.08);
		border-radius: 2px;
		overflow: hidden;
	}
	.fill {
		height: 100%;
		transition: width 0.4s ease;
	}
	.fill.fear { background: linear-gradient(90deg, #7a1320, #ff3355); }
	.fill.pride { background: linear-gradient(90deg, #7a6100, #ffd700); }
	.fill.conf { background: linear-gradient(90deg, #004a5a, #00ddff); }

	@keyframes pulse-fear {
		0%, 100% { filter: drop-shadow(0 0 2px rgba(255, 51, 85, 0.6)); }
		50% { filter: drop-shadow(0 0 10px rgba(255, 51, 85, 0.95)); }
	}

	@media (max-width: 768px) {
		.demiurge-hud {
			top: 8px;
			padding: 4px 8px 4px 6px;
			gap: 6px;
		}
		.eye-wrap { width: 32px; height: 32px; }
		.bars { min-width: 86px; }
		.label { width: 44px; font-size: 8px; }
	}
</style>
