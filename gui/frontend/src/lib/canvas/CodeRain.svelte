<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { agents, tick, stats, matrixState, events } from '$lib/stores/simulation';
	import { zoomLevel } from '$lib/stores/ui';

	let canvas: HTMLCanvasElement;
	let ctx: CanvasRenderingContext2D;
	let animFrame: number;
	let width = 0;
	let height = 0;

	// Matrix characters
	const CHARS = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789ABCDEF';

	type Column = {
		x: number;
		y: number;
		speed: number;
		brightness: number;
		hue: number; // 120=green, 0=red (awareness shift)
		chars: string[];
		agentId: number;
		length: number;
	};

	let columns: Column[] = [];
	let statsText = '';
	let eventText = '';
	let eventAlpha = 0;
	let flashAlpha = 0; // For dramatic events

	function initColumns() {
		if (!canvas) return;
		width = canvas.width = window.innerWidth;
		height = canvas.height = window.innerHeight;

		const colWidth = 20; // wider spacing for cleaner look
		const numCols = Math.floor(width / colWidth);
		columns = [];

		const agentList = Array.from($agents.values());

		for (let i = 0; i < numCols; i++) {
			const agent = agentList[i % agentList.length];
			const awarenessHue = agent ? Math.max(0, 120 - agent.awareness * 120) : 120;

			columns.push({
				x: i * colWidth,
				y: Math.random() * height,
				speed: agent ? 0.4 + (1 - agent.age / 100) * 1.2 : 0.6 + Math.random() * 1.2,
				brightness: agent ? 0.3 + agent.health * 0.7 : 0.5 + Math.random() * 0.5,
				hue: awarenessHue,
				chars: Array.from({ length: 12 + Math.floor(Math.random() * 10) }, () =>
					CHARS[Math.floor(Math.random() * CHARS.length)]
				),
				agentId: agent?.id ?? -1,
				length: 10 + Math.floor(Math.random() * 15)
			});
		}
	}

	function draw() {
		if (!ctx || $zoomLevel !== 0) {
			animFrame = requestAnimationFrame(draw);
			return;
		}

		// Faster fade = sharper characters, shorter trails (more like the movie)
		ctx.fillStyle = 'rgba(3, 13, 3, 0.15)';
		ctx.fillRect(0, 0, width, height);

		const controlIndex = $matrixState.control_index;

		// Draw columns
		for (const col of columns) {
			col.y += col.speed;
			if (col.y > height + col.length * 16) {
				col.y = -col.length * 16;
				// Randomize a char
				const idx = Math.floor(Math.random() * col.chars.length);
				col.chars[idx] = CHARS[Math.floor(Math.random() * CHARS.length)];
			}

			for (let j = 0; j < col.chars.length; j++) {
				const charY = col.y + j * 16;
				if (charY < -16 || charY > height + 16) continue;

				const fade = j / col.chars.length;
				const alpha = col.brightness * (1 - fade * 0.7);

				if (j === 0) {
					// Leading character is brightest (white-ish) — movie-accurate bright tip
					ctx.fillStyle = `rgba(230, 255, 230, ${Math.min(1, alpha * 1.5)})`;
					ctx.font = 'bold 15px JetBrains Mono';
				} else {
					// Glitch: low control index causes random red flashes
					let h = col.hue;
					if (controlIndex < 0.5 && Math.random() < (0.5 - controlIndex) * 0.1) {
						h = 0; // red flash
					}
					// Sharper green, less saturated for movie-like look
					const lightness = 40 + (1 - fade) * 20;
					ctx.fillStyle = `hsla(${h}, 80%, ${lightness}%, ${alpha * 0.9})`;
					ctx.font = '15px JetBrains Mono';
				}

				ctx.fillText(col.chars[j], col.x, charY);
			}
		}

		// Flash effect (for dramatic events)
		if (flashAlpha > 0) {
			ctx.fillStyle = `rgba(255, 215, 0, ${flashAlpha})`;
			ctx.fillRect(0, 0, width, height);
			flashAlpha *= 0.92;
			if (flashAlpha < 0.01) flashAlpha = 0;
		}

		// Ambient stats overlay
		ctx.font = '24px JetBrains Mono';
		ctx.fillStyle = 'rgba(0, 255, 136, 0.15)';
		ctx.textAlign = 'center';
		ctx.fillText(statsText, width / 2, 60);

		// Ticker at bottom
		if (eventAlpha > 0) {
			ctx.font = '16px JetBrains Mono';
			ctx.fillStyle = `rgba(0, 255, 136, ${eventAlpha * 0.6})`;
			ctx.textAlign = 'center';
			ctx.fillText(eventText, width / 2, height - 40);
			eventAlpha *= 0.995;
		}

		animFrame = requestAnimationFrame(draw);
	}

	// Update stats text reactively
	$effect(() => {
		const s = $stats;
		const t = $tick;
		const m = $matrixState;
		statsText = `POP: ${s.alive_count}  |  TICK: ${t}  |  GEN: ${s.avg_generation.toFixed(1)}  |  CTRL: ${(m.control_index * 100).toFixed(0)}%`;
	});

	// Update event ticker
	$effect(() => {
		const evts = $events;
		if (evts.length > 0) {
			const last = evts[evts.length - 1];
			eventText = `t=${last.tick}: ${last.text}`;
			eventAlpha = 1.0;

			// Flash on matrix events
			if (last.type === 'matrix') {
				flashAlpha = 0.15;
			}
		}
	});

	// Update columns when agents change
	$effect(() => {
		const agentList = Array.from($agents.values());
		for (let i = 0; i < columns.length; i++) {
			const agent = agentList[i % agentList.length];
			if (agent && columns[i]) {
				columns[i].brightness = 0.3 + agent.health * 0.7;
				columns[i].hue = Math.max(0, 120 - agent.awareness * 120);
				columns[i].speed = 0.5 + (1 - Math.min(agent.age, 80) / 80) * 2;
			}
		}
	});

	onMount(() => {
		ctx = canvas.getContext('2d')!;
		initColumns();
		draw();

		const handleResize = () => initColumns();
		window.addEventListener('resize', handleResize);

		return () => {
			window.removeEventListener('resize', handleResize);
			cancelAnimationFrame(animFrame);
		};
	});

	onDestroy(() => {
		cancelAnimationFrame(animFrame);
	});
</script>

<canvas
	bind:this={canvas}
	class="code-rain"
	class:visible={$zoomLevel === 0}
></canvas>

<style>
	.code-rain {
		position: fixed;
		inset: 0;
		z-index: 0;
		opacity: 0;
		transition: opacity 0.6s ease;
		pointer-events: none;
	}
	.code-rain.visible {
		opacity: 1;
		pointer-events: auto;
	}
</style>
