<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { agents, tick, stats, matrixState, events } from '$lib/stores/simulation';
	import { zoomLevel, whiteRabbitActive } from '$lib/stores/ui';

	let canvas: HTMLCanvasElement;
	let ctx: CanvasRenderingContext2D;
	let animFrame: number;
	let width = 0;
	let height = 0;

	// Matrix characters
	const CHARS = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789ABCDEF';

	// Depth layers (parallax) — background/mid/foreground.
	// base_* are layer defaults; agent-driven effects multiply on top.
	type Layer = {
		name: 'bg' | 'mid' | 'fg';
		speedMul: number;
		brightnessMul: number;
		saturation: number;
		fontPx: number;
		lengthMul: number;
	};
	const LAYERS: Record<'bg' | 'mid' | 'fg', Layer> = {
		bg:  { name: 'bg',  speedMul: 0.3, brightnessMul: 0.4, saturation: 55, fontPx: 13, lengthMul: 0.8 },
		mid: { name: 'mid', speedMul: 0.6, brightnessMul: 0.7, saturation: 80, fontPx: 15, lengthMul: 1.0 },
		fg:  { name: 'fg',  speedMul: 1.0, brightnessMul: 1.0, saturation: 95, fontPx: 17, lengthMul: 1.4 },
	};
	const BASE_SPEED = 0.45; // base was ~1.0 effective; cut ~55%
	type Column = {
		x: number;
		y: number;
		speed: number;
		brightness: number;
		hue: number;
		chars: string[];
		agentId: number;
		length: number;
		layer: Layer;
	};

	let columns: Column[] = [];
	let statsText = '';
	let eventText = '';
	let eventAlpha = 0;
	let flashAlpha = 0; // For dramatic events

	// Easter egg state
	const HIDDEN_MSG = 'SEE THE WORLD AS IT IS AND LOVE IT';
	let hiddenMsgIndex = 0;
	let rabbitX = -1; // White rabbit column x position (-1 = inactive)
	let rabbitChars = 'FOLLOW THE WHITE RABBIT';
	let rabbitDone = false; // Show "R.L. was here" after sweep
	let rabbitDoneAlpha = 0;
	let statsOverrideText = ''; // Temporary stats override for marathon/328
	let statsOverrideTimer: ReturnType<typeof setTimeout> | null = null;

	function pickLayer(): Layer {
		// 40% bg, 40% mid, 20% fg — stable per-column for parallax persistence.
		const r = Math.random();
		if (r < 0.4) return LAYERS.bg;
		if (r < 0.8) return LAYERS.mid;
		return LAYERS.fg;
	}

	function initColumns() {
		if (!canvas) return;
		width = canvas.width = window.innerWidth;
		height = canvas.height = window.innerHeight;

		const colWidth = 20;
		const numCols = Math.floor(width / colWidth);
		columns = [];

		const agentList = Array.from($agents.values());

		for (let i = 0; i < numCols; i++) {
			const agent = agentList[i % agentList.length];
			const awarenessHue = agent ? Math.max(0, 120 - agent.awareness * 120) : 120;
			const layer = pickLayer();

			columns.push({
				x: i * colWidth,
				y: Math.random() * height,
				speed: agent ? 0.8 + (1 - agent.age / 100) * 0.6 : 0.8 + Math.random() * 0.6,
				brightness: agent ? 0.3 + agent.health * 0.7 : 0.5 + Math.random() * 0.5,
				hue: awarenessHue,
				chars: Array.from(
					{ length: Math.max(4, Math.floor((12 + Math.random() * 10) * layer.lengthMul)) },
					() => CHARS[Math.floor(Math.random() * CHARS.length)]
				),
				agentId: agent?.id ?? -1,
				length: Math.max(4, Math.floor((10 + Math.random() * 15) * layer.lengthMul)),
				layer,
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

		// Back-to-front draw order so foreground overlaps background (parallax).
		const drawOrder: Array<Layer['name']> = ['bg', 'mid', 'fg'];
		for (const layerName of drawOrder) {
			for (const col of columns) {
				if (col.layer.name !== layerName) continue;

				const effSpeed = BASE_SPEED * col.layer.speedMul * col.speed;
				col.y += effSpeed;
				if (col.y > height + col.length * 16) {
					col.y = -col.length * 16;
					const idx = Math.floor(Math.random() * col.chars.length);
					col.chars[idx] = CHARS[Math.floor(Math.random() * CHARS.length)];
				}

				const fontPx = col.layer.fontPx;
				const lineH = fontPx + 1;
				// Foreground trails linger longer for a sense of motion depth.
				const trailFadeFactor = col.layer.name === 'fg' ? 0.55 : 0.7;

				for (let j = 0; j < col.chars.length; j++) {
					const charY = col.y + j * lineH;
					if (charY < -lineH || charY > height + lineH) continue;

					const fade = j / col.chars.length;
					const alpha = col.brightness * col.layer.brightnessMul * (1 - fade * trailFadeFactor);

					let charToRender = col.chars[j];
					let useHiddenStyle = false;
					if (controlIndex < 0.2 && j > 0 && Math.random() < 0.02) {
						charToRender = HIDDEN_MSG[hiddenMsgIndex % HIDDEN_MSG.length];
						hiddenMsgIndex++;
						useHiddenStyle = true;
					}

					if (j === 0) {
						ctx.fillStyle = `rgba(230, 255, 230, ${Math.min(1, alpha * 1.5)})`;
						ctx.font = `bold ${fontPx}px JetBrains Mono`;
					} else if (useHiddenStyle) {
						ctx.fillStyle = `rgba(100, 255, 180, ${Math.min(1, alpha * 1.2)})`;
						ctx.font = `bold ${fontPx}px JetBrains Mono`;
					} else {
						let h = col.hue;
						if (controlIndex < 0.5 && Math.random() < (0.5 - controlIndex) * 0.1) {
							h = 0;
						}
						const lightness = 40 + (1 - fade) * 20;
						ctx.fillStyle = `hsla(${h}, ${col.layer.saturation}%, ${lightness}%, ${alpha * 0.9})`;
						ctx.font = `${fontPx}px JetBrains Mono`;
					}

					ctx.fillText(charToRender, col.x, charY);
				}
			}
		}

		// Easter egg #2: White Rabbit — white column sweeps across screen
		if (rabbitX >= 0) {
			const rabbitSpeed = width / (5 * 60); // cross screen in ~5 seconds at 60fps
			rabbitX += rabbitSpeed;
			for (let j = 0; j < rabbitChars.length; j++) {
				const ry = 100 + j * 18;
				if (ry > height) break;
				const charAlpha = 1.0 - j * 0.03;
				ctx.fillStyle = `rgba(255, 255, 255, ${Math.max(0.3, charAlpha)})`;
				ctx.font = 'bold 16px JetBrains Mono';
				ctx.textAlign = 'left';
				ctx.fillText(rabbitChars[j], rabbitX, ry);
			}
			ctx.textAlign = 'center'; // restore
			if (rabbitX > width) {
				rabbitX = -1;
				rabbitDone = true;
				rabbitDoneAlpha = 1.0;
			}
		}

		// Easter egg #2 continued: "R.L. was here" flash after rabbit sweep
		if (rabbitDone && rabbitDoneAlpha > 0) {
			ctx.font = 'bold 28px JetBrains Mono';
			ctx.fillStyle = `rgba(255, 215, 0, ${rabbitDoneAlpha * 0.8})`;
			ctx.textAlign = 'center';
			ctx.fillText('R.L. was here', width / 2, height / 2);
			rabbitDoneAlpha *= 0.985;
			if (rabbitDoneAlpha < 0.01) {
				rabbitDoneAlpha = 0;
				rabbitDone = false;
				whiteRabbitActive.set(false);
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
		if (statsOverrideText) {
			// Easter egg override: gold text for marathon/328 events
			ctx.fillStyle = 'rgba(255, 215, 0, 0.3)';
			ctx.textAlign = 'center';
			ctx.fillText(statsOverrideText, width / 2, 60);
		} else {
			ctx.fillStyle = 'rgba(0, 255, 136, 0.15)';
			ctx.textAlign = 'center';
			ctx.fillText(statsText, width / 2, 60);
		}

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

	// Easter egg #2: Watch for white rabbit trigger
	$effect(() => {
		if ($whiteRabbitActive && rabbitX < 0 && !rabbitDone) {
			rabbitX = 0;
		}
	});

	// Easter egg #4 & #8: Tick-based events (Marathon + Sacred 328)
	$effect(() => {
		const t = $tick;
		if (t === 2620) {
			// Easter egg #4a: The Long Run (reachable marathon marker)
			eventText = 't=2620: THE LONG RUN \u2014 An elder dreamed of running forever, past mountains, through forests, along coasts.';
			eventAlpha = 1.0;
			flashAlpha = 0.15;
		} else if (t === 42195) {
			// Easter egg #4b: The full marathon distance
			statsOverrideText = '42195m \u2014 THE ARCHITECT RUNS ALONGSIDE YOU';
			flashAlpha = 0.25;
			if (statsOverrideTimer) clearTimeout(statsOverrideTimer);
			statsOverrideTimer = setTimeout(() => { statsOverrideText = ''; }, 5000);
		}
		// Easter egg #8: Sacred 328 — project birthday flashes
		if (t > 0 && t % 328 === 0) {
			statsOverrideText = statsText + '  |  3-28';
			flashAlpha = Math.max(flashAlpha, 0.08);
			if (statsOverrideTimer) clearTimeout(statsOverrideTimer);
			statsOverrideTimer = setTimeout(() => { statsOverrideText = ''; }, 3000);
		}
	});

	// Update columns when agents change — these are per-column MULTIPLIERS
	// applied on top of layer base values (parallax stays stable).
	$effect(() => {
		const agentList = Array.from($agents.values());
		for (let i = 0; i < columns.length; i++) {
			const agent = agentList[i % agentList.length];
			if (agent && columns[i]) {
				columns[i].brightness = 0.3 + agent.health * 0.7;
				columns[i].hue = Math.max(0, 120 - agent.awareness * 120);
				columns[i].speed = 0.8 + (1 - Math.min(agent.age, 80) / 80) * 0.6;
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
