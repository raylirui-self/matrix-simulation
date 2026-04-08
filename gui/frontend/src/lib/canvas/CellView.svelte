<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { agents, type Agent } from '$lib/stores/simulation';
	import { zoomLevel, focusCell, focusAgentId } from '$lib/stores/ui';

	let canvas: HTMLCanvasElement;
	let ctx: CanvasRenderingContext2D;
	let animFrame: number;
	let width = 0;
	let height = 0;
	let hoverAgent: Agent | null = null;

	const PHASE_SHAPES: Record<string, number> = {
		infant: 20,    // circle (many sides)
		child: 3,      // triangle
		adolescent: 5, // pentagon
		adult: 6,      // hexagon
		elder: 8       // octagon
	};

	const EMOTION_COLORS: Record<string, string> = {
		happiness: '#00ff88',
		fear: '#ffff00',
		anger: '#ff2200',
		grief: '#6644cc',
		hope: '#00aaff'
	};

	function getCellAgents(): Agent[] {
		const cell = $focusCell;
		if (!cell) return [];
		const gridSize = 8;
		return Array.from($agents.values()).filter((a) => {
			const row = Math.min(gridSize - 1, Math.floor(a.y * gridSize));
			const col = Math.min(gridSize - 1, Math.floor(a.x * gridSize));
			return row === cell.row && col === cell.col;
		});
	}

	function drawPolygon(cx: number, cy: number, radius: number, sides: number) {
		ctx.beginPath();
		for (let i = 0; i < sides; i++) {
			const angle = (i / sides) * Math.PI * 2 - Math.PI / 2;
			const x = cx + radius * Math.cos(angle);
			const y = cy + radius * Math.sin(angle);
			if (i === 0) ctx.moveTo(x, y);
			else ctx.lineTo(x, y);
		}
		ctx.closePath();
	}

	function draw() {
		if (!ctx || $zoomLevel !== 2) {
			animFrame = requestAnimationFrame(draw);
			return;
		}

		ctx.clearRect(0, 0, width, height);
		ctx.fillStyle = '#040e04';
		ctx.fillRect(0, 0, width, height);

		const cell = $focusCell;
		if (!cell) {
			animFrame = requestAnimationFrame(draw);
			return;
		}

		// Header
		ctx.font = '14px JetBrains Mono';
		ctx.fillStyle = '#00ddff';
		ctx.textAlign = 'left';
		ctx.fillText(`CELL [${cell.row}, ${cell.col}]`, 20, 30);
		ctx.fillStyle = '#4a6a4a';
		ctx.fillText('Click agent for details | ESC to go back', 20, 50);

		const cellAgents = getCellAgents();
		const padding = 80;
		const areaW = width - padding * 2;
		const areaH = height - padding * 2;

		// Draw agents as large glyphs
		for (const agent of cellAgents) {
			// Map agent position within cell to screen
			const cellFracX = Math.max(0, Math.min(1, agent.x * 8 - cell.col));
			const cellFracY = Math.max(0, Math.min(1, agent.y * 8 - cell.row));
			const ax = padding + cellFracX * areaW;
			const ay = padding + cellFracY * areaH;

			const sides = PHASE_SHAPES[agent.phase] || 6;
			const size = 12 + agent.intelligence * 20;
			const color = EMOTION_COLORS[agent.emotion] || '#00ff88';

			// Awareness glow
			if (agent.awareness > 0.1) {
				const glowR = size + 8 + agent.awareness * 15;
				const glowColor = agent.is_anomaly ? 'rgba(255, 215, 0,' : 'rgba(255, 255, 255,';
				ctx.fillStyle = `${glowColor} ${agent.awareness * 0.3})`;
				ctx.beginPath();
				ctx.arc(ax, ay, glowR, 0, Math.PI * 2);
				ctx.fill();
			}

			// Draw shape
			drawPolygon(ax, ay, size, sides);
			ctx.fillStyle = color;
			ctx.globalAlpha = 0.5 + agent.health * 0.5;
			ctx.fill();
			ctx.globalAlpha = 1;
			ctx.strokeStyle = color;
			ctx.lineWidth = 1.5;
			ctx.stroke();

			// Sentinel: red outline + scan line
			if (agent.is_sentinel) {
				ctx.strokeStyle = '#ff0000';
				ctx.lineWidth = 2;
				drawPolygon(ax, ay, size + 3, sides);
				ctx.stroke();
			}

			// Protagonist star
			if (agent.is_protagonist) {
				ctx.font = 'bold 16px JetBrains Mono';
				ctx.fillStyle = '#ffd700';
				ctx.textAlign = 'center';
				ctx.fillText('★', ax, ay - size - 8);
				if (agent.protagonist_name) {
					ctx.font = '11px JetBrains Mono';
					ctx.fillText(agent.protagonist_name, ax, ay - size - 22);
				}
			}

			// ID label
			ctx.font = '10px JetBrains Mono';
			ctx.fillStyle = 'rgba(0, 255, 136, 0.5)';
			ctx.textAlign = 'center';
			ctx.fillText(`#${agent.id}`, ax, ay + size + 14);

			// Hover detection
			if (hoverAgent?.id === agent.id) {
				ctx.strokeStyle = '#00ff88';
				ctx.lineWidth = 2;
				drawPolygon(ax, ay, size + 5, sides);
				ctx.stroke();

				// Mini stats
				const lines = [
					`#${agent.id} ${agent.sex} ${agent.phase} age:${agent.age}`,
					`HP:${agent.health.toFixed(2)} IQ:${agent.intelligence.toFixed(2)}`,
					`${agent.emotion} AWR:${(agent.awareness * 100).toFixed(0)}%`,
					agent.redpilled ? 'REDPILLED' : ''
				].filter(Boolean);

				ctx.fillStyle = 'rgba(6, 18, 6, 0.9)';
				ctx.beginPath();
				ctx.roundRect(ax + size + 10, ay - 30, 200, lines.length * 16 + 12, 4);
				ctx.fill();
				ctx.font = '11px JetBrains Mono';
				ctx.fillStyle = '#00ff88';
				ctx.textAlign = 'left';
				lines.forEach((line, i) => {
					ctx.fillText(line, ax + size + 16, ay - 16 + i * 16);
				});
			}
		}

		// Bond rendering between agents in this cell could be added here

		animFrame = requestAnimationFrame(draw);
	}

	function handleMouseMove(e: MouseEvent) {
		const cellAgents = getCellAgents();
		const cell = $focusCell;
		if (!cell) return;

		const padding = 80;
		const areaW = width - padding * 2;
		const areaH = height - padding * 2;

		let closest: Agent | null = null;
		let closestDist = 30;

		for (const agent of cellAgents) {
			const cellFracX = Math.max(0, Math.min(1, agent.x * 8 - cell.col));
			const cellFracY = Math.max(0, Math.min(1, agent.y * 8 - cell.row));
			const ax = padding + cellFracX * areaW;
			const ay = padding + cellFracY * areaH;

			const dist = Math.sqrt((e.clientX - ax) ** 2 + (e.clientY - ay) ** 2);
			if (dist < closestDist) {
				closestDist = dist;
				closest = agent;
			}
		}
		hoverAgent = closest;
	}

	function handleClick() {
		if (hoverAgent) {
			focusAgentId.set(hoverAgent.id);
			zoomLevel.set(3);
		}
	}

	onMount(() => {
		ctx = canvas.getContext('2d')!;
		width = canvas.width = window.innerWidth;
		height = canvas.height = window.innerHeight;
		draw();

		const handleResize = () => {
			width = canvas.width = window.innerWidth;
			height = canvas.height = window.innerHeight;
		};
		window.addEventListener('resize', handleResize);
		return () => {
			window.removeEventListener('resize', handleResize);
			cancelAnimationFrame(animFrame);
		};
	});

	onDestroy(() => cancelAnimationFrame(animFrame));
</script>

<canvas
	bind:this={canvas}
	class="cell-view"
	class:visible={$zoomLevel === 2}
	onmousemove={handleMouseMove}
	onclick={handleClick}
	aria-label="Cell neighborhood view"
></canvas>

<style>
	.cell-view {
		position: fixed;
		inset: 0;
		z-index: 2;
		opacity: 0;
		transition: opacity 0.4s ease;
		pointer-events: none;
		cursor: crosshair;
	}
	.cell-view.visible {
		opacity: 1;
		pointer-events: auto;
	}
</style>
