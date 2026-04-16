<!--
  HavenPiP.svelte — Phase 7B "real world" picture-in-picture.
  Small inset panel (300x300) that renders the Haven's grid at low
  fidelity with muted blue/grey/white tones. Deliberately NO green —
  the Matrix owns that color. Toggled via the H key at Level 1.
-->
<script lang="ts">
	import { onDestroy } from 'svelte';
	import { havenSummary, agents } from '$lib/stores/simulation';
	import { havenPipOpen, zoomLevel } from '$lib/stores/ui';

	let canvas = $state<HTMLCanvasElement | null>(null);
	let ctx: CanvasRenderingContext2D;
	let animFrame: number;

	const PIP_SIZE = 300;

	// Muted palette — intentionally no green.
	const HAVEN_TERRAIN_COLORS = ['#14181e', '#1c2330', '#222c38', '#2a3644'];
	const HAVEN_AGENT_COLOR = '#d4e4f3';
	const HAVEN_AGENT_LOW_HEALTH = '#ff9080';

	function draw() {
		animFrame = requestAnimationFrame(draw);
		if (!ctx || !$havenPipOpen) return;
		const hav = $havenSummary;
		if (!hav) {
			ctx.fillStyle = '#0a0f14';
			ctx.fillRect(0, 0, PIP_SIZE, PIP_SIZE);
			ctx.fillStyle = '#6a7a8a';
			ctx.font = '10px JetBrains Mono';
			ctx.textAlign = 'center';
			ctx.fillText('HAVEN OFFLINE', PIP_SIZE / 2, PIP_SIZE / 2);
			return;
		}

		const gridSize = hav.grid_size || 4;
		const pad = 10;
		const gridSpan = PIP_SIZE - pad * 2 - 22; // leave room for status strip
		const cell = Math.floor(gridSpan / gridSize);
		const gridX = pad;
		const gridY = pad;

		// Background — harsh, low-fidelity concrete grey
		ctx.fillStyle = '#0b1016';
		ctx.fillRect(0, 0, PIP_SIZE, PIP_SIZE);

		// Chunky cell tiles — no smoothing, deliberately pixelated feel
		const cells = hav.grid_cells || [];
		for (const c of cells) {
			const x = gridX + c.col * cell;
			const y = gridY + c.row * cell;
			// Resource saturation → tile brightness (muted blue/grey scale)
			const saturation = Math.max(
				0,
				Math.min(1, c.resources / Math.max(0.01, c.base_resources))
			);
			const shadeIdx = Math.min(
				HAVEN_TERRAIN_COLORS.length - 1,
				Math.floor(saturation * HAVEN_TERRAIN_COLORS.length)
			);
			ctx.fillStyle = HAVEN_TERRAIN_COLORS[shadeIdx];
			ctx.fillRect(x, y, cell - 2, cell - 2);

			// Harshness scanline — emphasizes the low-fidelity real world
			if (c.harshness > 1.5) {
				ctx.fillStyle = 'rgba(255, 255, 255, 0.035)';
				for (let sy = y; sy < y + cell - 2; sy += 3) {
					ctx.fillRect(x, sy, cell - 2, 1);
				}
			}

			// Tiny agent count pip
			if (c.agent_count > 0) {
				ctx.fillStyle = 'rgba(212, 228, 243, 0.35)';
				ctx.font = '8px JetBrains Mono';
				ctx.textAlign = 'left';
				ctx.fillText(String(c.agent_count), x + 3, y + 10);
			}
		}

		// Overlay individual agents (filtered to location=="haven")
		const havenAgents = hav.agents && hav.agents.length > 0
			? hav.agents
			: Array.from($agents.values())
					.filter((a) => a.location === 'haven')
					.map((a) => ({ id: a.id, x: a.x, y: a.y, emotion: a.emotion, health: a.health }));

		for (const a of havenAgents) {
			const ax = gridX + a.x * gridSize * cell;
			const ay = gridY + a.y * gridSize * cell;
			ctx.fillStyle = a.health < 0.4 ? HAVEN_AGENT_LOW_HEALTH : HAVEN_AGENT_COLOR;
			ctx.beginPath();
			ctx.arc(ax, ay, 2, 0, Math.PI * 2);
			ctx.fill();
		}

		// Status strip along the bottom
		const stripY = PIP_SIZE - 18;
		ctx.fillStyle = 'rgba(8, 14, 20, 0.92)';
		ctx.fillRect(0, stripY, PIP_SIZE, 18);
		ctx.fillStyle = '#7ab0d4';
		ctx.font = '9px JetBrains Mono';
		ctx.textAlign = 'left';
		const voteLabel = (hav.last_vote_outcome || 'no vote').toUpperCase();
		ctx.fillText(
			`POP ${hav.population} · MIS ${hav.active_missions} · ${voteLabel}`,
			8,
			stripY + 12
		);
	}

	// Canvas is inside a conditional block, so initialize via $effect
	// (runs whenever the binding resolves a new element, e.g. first open).
	$effect(() => {
		if (!canvas) return;
		ctx = canvas.getContext('2d')!;
		canvas.width = PIP_SIZE;
		canvas.height = PIP_SIZE;
		cancelAnimationFrame(animFrame);
		draw();
	});

	onDestroy(() => {
		cancelAnimationFrame(animFrame);
	});
</script>

{#if $havenPipOpen && $zoomLevel === 1}
	<div class="haven-pip" aria-label="Haven picture-in-picture">
		<div class="pip-header">
			<span class="pip-title">HAVEN / REAL</span>
			<button
				class="pip-close"
				onclick={() => havenPipOpen.set(false)}
				aria-label="Close Haven PiP"
			>
				✕
			</button>
		</div>
		<canvas bind:this={canvas}></canvas>
	</div>
{/if}

<style>
	.haven-pip {
		position: fixed;
		bottom: 20px;
		left: 20px;
		width: 300px;
		z-index: 22;
		background: rgba(6, 10, 14, 0.9);
		border: 1px solid rgba(120, 160, 200, 0.35);
		border-radius: 4px;
		font-family: var(--font-mono, 'JetBrains Mono', monospace);
		pointer-events: auto;
		box-shadow: 0 0 24px rgba(0, 0, 0, 0.5);
		backdrop-filter: blur(4px);
	}
	.pip-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 4px 8px;
		border-bottom: 1px solid rgba(120, 160, 200, 0.2);
		background: rgba(16, 22, 30, 0.7);
	}
	.pip-title {
		font-size: 10px;
		letter-spacing: 2px;
		color: #7ab0d4;
	}
	.pip-close {
		background: none;
		border: none;
		color: #7ab0d4;
		font-size: 11px;
		cursor: pointer;
		padding: 0 4px;
	}
	.pip-close:hover {
		color: #ffffff;
	}
	canvas {
		display: block;
		image-rendering: pixelated;
	}

	@media (max-width: 768px) {
		.haven-pip {
			bottom: 60px;
			left: 8px;
			width: 220px;
		}
	}
</style>
