<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import {
		agents,
		tick,
		matrixState,
		type Agent
	} from '$lib/stores/simulation';
	import { zoomLevel, focusCell, focusAgentId, overlays, bondConstellationMode } from '$lib/stores/ui';
	import { api } from '$lib/api/rest';
	import { runId } from '$lib/stores/simulation';

	let canvas: HTMLCanvasElement;
	let ctx: CanvasRenderingContext2D;
	let animFrame: number;
	let width = 0;
	let height = 0;

	// World data
	let worldData: any = null;
	let bonds: any[] = [];

	// Terrain colors
	const TERRAIN_COLORS: Record<string, string> = {
		plains: '#1a3a12',
		forest: '#0a2a08',
		mountains: '#2a2a1a',
		coast: '#0a1a2a'
	};

	const TERRAIN_COLORS_BRIGHT: Record<string, string> = {
		plains: '#2a5a22',
		forest: '#1a4a18',
		mountains: '#3a3a2a',
		coast: '#1a2a4a'
	};

	// Phase colors
	const PHASE_COLORS: Record<string, string> = {
		infant: '#66ff66',
		child: '#00ddff',
		adolescent: '#ffaa00',
		adult: '#ff4466',
		elder: '#aa66ff'
	};

	// Emotion colors
	const EMOTION_COLORS: Record<string, string> = {
		happiness: '#00ff88',
		fear: '#ffff00',
		anger: '#ff2200',
		grief: '#6644cc',
		hope: '#00aaff'
	};

	// Bond colors
	const BOND_COLORS: Record<string, string> = {
		family: '#00ff88',
		friend: '#00ddff',
		rival: '#ff4466',
		mate: '#ffa500',
		ally: '#66ff66',
		enemy: '#ff0000',
		resistance: '#ffd700'
	};

	// Hover state
	let hoverAgent: Agent | null = null;
	let hoverCell: { row: number; col: number } | null = null;
	let mouseX = 0;
	let mouseY = 0;

	// Grid layout
	let gridLeft = 0;
	let gridTop = 0;
	let cellSize = 0;
	let gridSize = 8;

	function calculateGrid() {
		const padding = 40;
		const maxSize = Math.min(width - padding * 2, height - padding * 2);
		gridSize = worldData?.grid_size || 8;
		cellSize = Math.floor(maxSize / gridSize);
		gridLeft = Math.floor((width - cellSize * gridSize) / 2);
		gridTop = Math.floor((height - cellSize * gridSize) / 2);
	}

	function draw() {
		if (!ctx || $zoomLevel !== 1) {
			animFrame = requestAnimationFrame(draw);
			return;
		}

		ctx.clearRect(0, 0, width, height);

		// Background
		ctx.fillStyle = '#030d03';
		ctx.fillRect(0, 0, width, height);

		if (!worldData) {
			// Loading state
			ctx.font = '18px JetBrains Mono';
			ctx.fillStyle = '#0a3a0a';
			ctx.textAlign = 'center';
			ctx.fillText('LOADING WORLD DATA...', width / 2, height / 2);
			animFrame = requestAnimationFrame(draw);
			return;
		}

		calculateGrid();
		const controlIndex = $matrixState.control_index;

		// Draw terrain cells
		for (const cell of worldData.cells) {
			const x = gridLeft + cell.col * cellSize;
			const y = gridTop + cell.row * cellSize;

			// Base terrain color
			const baseColor = TERRAIN_COLORS[cell.terrain] || '#1a1a1a';
			const brightColor = TERRAIN_COLORS_BRIGHT[cell.terrain] || '#2a2a2a';

			// Resource saturation — depleted cells are grey
			const resourceFactor = Math.min(1, cell.resources / (cell.base_resources || 1));
			ctx.fillStyle = resourceFactor > 0.3 ? brightColor : baseColor;
			ctx.fillRect(x, y, cellSize - 1, cellSize - 1);

			// Resource glow overlay
			if (resourceFactor > 0.5) {
				const glowAlpha = (resourceFactor - 0.5) * 0.15;
				ctx.fillStyle = `rgba(0, 255, 136, ${glowAlpha})`;
				ctx.fillRect(x, y, cellSize - 1, cellSize - 1);
			}

			// Depleted warning
			if (resourceFactor < 0.2) {
				ctx.fillStyle = 'rgba(255, 68, 102, 0.1)';
				ctx.fillRect(x, y, cellSize - 1, cellSize - 1);
			}

			// Tech icons
			if (cell.unlocked_techs?.length > 0) {
				ctx.font = '10px JetBrains Mono';
				ctx.fillStyle = 'rgba(0, 255, 136, 0.4)';
				ctx.textAlign = 'left';
				const techLabel = cell.unlocked_techs.length > 2
					? `T:${cell.unlocked_techs.length}`
					: cell.unlocked_techs.map((t: string) => t[0].toUpperCase()).join('');
				ctx.fillText(techLabel, x + 3, y + cellSize - 4);
			}

			// Hover highlight
			if (hoverCell && hoverCell.row === cell.row && hoverCell.col === cell.col) {
				ctx.strokeStyle = 'rgba(0, 255, 136, 0.6)';
				ctx.lineWidth = 2;
				ctx.strokeRect(x + 1, y + 1, cellSize - 3, cellSize - 3);
			}
		}

		// Grid lines
		ctx.strokeStyle = 'rgba(0, 255, 136, 0.08)';
		ctx.lineWidth = 1;
		for (let i = 0; i <= gridSize; i++) {
			ctx.beginPath();
			ctx.moveTo(gridLeft + i * cellSize, gridTop);
			ctx.lineTo(gridLeft + i * cellSize, gridTop + gridSize * cellSize);
			ctx.stroke();
			ctx.beginPath();
			ctx.moveTo(gridLeft, gridTop + i * cellSize);
			ctx.lineTo(gridLeft + gridSize * cellSize, gridTop + i * cellSize);
			ctx.stroke();
		}

		const agentList = Array.from($agents.values());
		const bondMode = $bondConstellationMode;

		// Draw bonds
		if (bonds.length > 0) {
			for (const bond of bonds) {
				const sx = gridLeft + bond.source_x * gridSize * cellSize;
				const sy = gridTop + bond.source_y * gridSize * cellSize;
				const tx = gridLeft + bond.target_x * gridSize * cellSize;
				const ty = gridTop + bond.target_y * gridSize * cellSize;

				const color = BOND_COLORS[bond.type] || '#00ff88';
				const alpha = bondMode ? bond.strength * 0.8 : bond.strength * 0.3;
				ctx.strokeStyle = color.replace(')', `, ${alpha})`).replace('rgb', 'rgba');
				ctx.globalAlpha = alpha;
				ctx.lineWidth = bondMode ? bond.strength * 3 : bond.strength * 1.5;
				ctx.beginPath();
				ctx.moveTo(sx, sy);
				ctx.lineTo(tx, ty);
				ctx.stroke();
			}
			ctx.globalAlpha = 1;
		}

		// Draw agents as particles
		for (const agent of agentList) {
			const ax = gridLeft + agent.x * gridSize * cellSize;
			const ay = gridTop + agent.y * gridSize * cellSize;

			if (bondMode && !agent.is_protagonist) {
				// In bond constellation, agents are dim dots
				ctx.fillStyle = 'rgba(0, 255, 136, 0.2)';
				ctx.beginPath();
				ctx.arc(ax, ay, 2, 0, Math.PI * 2);
				ctx.fill();
				continue;
			}

			// Size based on intelligence
			const baseSize = 3 + agent.intelligence * 4;
			const size = agent.is_protagonist ? baseSize + 2 : baseSize;

			// Color based on phase (or emotion if overlay active)
			let color = PHASE_COLORS[agent.phase] || '#00ff88';
			if ($overlays.has('emotions')) {
				color = EMOTION_COLORS[agent.emotion] || '#00ff88';
			}

			// Sentinel special rendering
			if (agent.is_sentinel) {
				color = '#ff0000';
				// Scanning beam
				ctx.strokeStyle = 'rgba(255, 0, 0, 0.15)';
				ctx.lineWidth = 1;
				ctx.beginPath();
				ctx.moveTo(ax, ay);
				ctx.lineTo(ax + Math.cos(Date.now() / 500 + agent.id) * 40, ay + Math.sin(Date.now() / 500 + agent.id) * 40);
				ctx.stroke();
			}

			// Draw agent circle
			ctx.beginPath();
			ctx.arc(ax, ay, size, 0, Math.PI * 2);
			ctx.fillStyle = color;
			ctx.globalAlpha = 0.7 + agent.health * 0.3;
			ctx.fill();
			ctx.globalAlpha = 1;

			// Awareness glow
			if (agent.awareness > 0.1) {
				const glowSize = size + 3 + agent.awareness * 6;
				const glowColor = agent.is_anomaly ? 'rgba(255, 215, 0, ' : 'rgba(255, 255, 255, ';
				const glowAlpha = agent.awareness * 0.4;
				ctx.beginPath();
				ctx.arc(ax, ay, glowSize, 0, Math.PI * 2);
				ctx.fillStyle = `${glowColor}${glowAlpha})`;
				ctx.fill();
			}

			// Protagonist star marker
			if (agent.is_protagonist) {
				ctx.font = 'bold 12px JetBrains Mono';
				ctx.fillStyle = '#ffd700';
				ctx.textAlign = 'center';
				ctx.fillText('★', ax, ay - size - 4);
				if (agent.protagonist_name) {
					ctx.font = '9px JetBrains Mono';
					ctx.fillStyle = 'rgba(255, 215, 0, 0.7)';
					ctx.fillText(agent.protagonist_name, ax, ay + size + 10);
				}
			}
		}

		// Hover agent tooltip
		if (hoverAgent) {
			drawAgentTooltip(hoverAgent);
		}

		// Hover cell tooltip
		if (hoverCell && !hoverAgent && worldData) {
			drawCellTooltip(hoverCell);
		}

		// Glitch effect when control is low
		if (controlIndex < 0.5) {
			applyGlitchEffect(controlIndex);
		}

		animFrame = requestAnimationFrame(draw);
	}

	function drawAgentTooltip(agent: Agent) {
		const ax = gridLeft + agent.x * gridSize * cellSize;
		const ay = gridTop + agent.y * gridSize * cellSize;

		const lines = [
			`#${agent.id} ${agent.protagonist_name || ''} ${agent.sex}`,
			`${agent.phase} age:${agent.age} gen:${agent.generation}`,
			`HP:${agent.health.toFixed(2)} IQ:${agent.intelligence.toFixed(2)}`,
			`${agent.emotion} AWR:${(agent.awareness * 100).toFixed(0)}%`,
			agent.redpilled ? '🔴 REDPILLED' : '',
			agent.is_anomaly ? '⚡ THE ONE' : ''
		].filter(Boolean);

		const padding = 8;
		const lineH = 16;
		const boxW = 220;
		const boxH = lines.length * lineH + padding * 2;
		let tx = ax + 15;
		let ty = ay - boxH / 2;
		if (tx + boxW > width) tx = ax - boxW - 15;
		if (ty < 0) ty = 5;
		if (ty + boxH > height) ty = height - boxH - 5;

		ctx.fillStyle = 'rgba(6, 18, 6, 0.92)';
		ctx.strokeStyle = 'rgba(0, 255, 136, 0.5)';
		ctx.lineWidth = 1;
		ctx.beginPath();
		ctx.roundRect(tx, ty, boxW, boxH, 4);
		ctx.fill();
		ctx.stroke();

		ctx.font = '11px JetBrains Mono';
		ctx.fillStyle = '#00ff88';
		ctx.textAlign = 'left';
		for (let i = 0; i < lines.length; i++) {
			const color = lines[i].includes('REDPILLED')
				? '#ff4466'
				: lines[i].includes('THE ONE')
					? '#ffd700'
					: '#00ff88';
			ctx.fillStyle = color;
			ctx.fillText(lines[i], tx + padding, ty + padding + (i + 1) * lineH - 3);
		}
	}

	function drawCellTooltip(cell: { row: number; col: number }) {
		const cellData = worldData?.cells?.find(
			(c: any) => c.row === cell.row && c.col === cell.col
		);
		if (!cellData) return;

		const x = gridLeft + cell.col * cellSize + cellSize / 2;
		const y = gridTop + cell.row * cellSize + cellSize / 2;

		const lines = [
			`[${cell.row},${cell.col}] ${cellData.terrain.toUpperCase()}`,
			`Resources: ${(cellData.resources * 100).toFixed(0)}%`,
			`Pop: ${cellData.agent_count} / Cap: ${cellData.effective_capacity}`,
			`Pressure: ${(cellData.pressure * 100).toFixed(0)}%`,
			...(cellData.unlocked_techs?.length ? [`Techs: ${cellData.unlocked_techs.join(', ')}`] : [])
		];

		const padding = 8;
		const lineH = 16;
		const boxW = 240;
		const boxH = lines.length * lineH + padding * 2;
		let tx = x + 15;
		let ty = y - boxH / 2;
		if (tx + boxW > width) tx = x - boxW - 15;
		if (ty < 0) ty = 5;

		ctx.fillStyle = 'rgba(6, 18, 6, 0.92)';
		ctx.strokeStyle = 'rgba(0, 221, 255, 0.4)';
		ctx.lineWidth = 1;
		ctx.beginPath();
		ctx.roundRect(tx, ty, boxW, boxH, 4);
		ctx.fill();
		ctx.stroke();

		ctx.font = '11px JetBrains Mono';
		ctx.fillStyle = '#00ddff';
		ctx.textAlign = 'left';
		for (let i = 0; i < lines.length; i++) {
			ctx.fillText(lines[i], tx + padding, ty + padding + (i + 1) * lineH - 3);
		}
	}

	function applyGlitchEffect(controlIndex: number) {
		const intensity = (0.5 - controlIndex) * 2; // 0-1
		const now = Date.now();

		// Random block displacement
		if (Math.random() < intensity * 0.08) {
			const blockH = 2 + Math.floor(Math.random() * 8);
			const y = Math.floor(Math.random() * height);
			const shift = Math.floor((Math.random() - 0.5) * 20 * intensity);
			const imgData = ctx.getImageData(0, y, width, blockH);
			ctx.putImageData(imgData, shift, y);
		}

		// Scan lines
		if (intensity > 0.3) {
			ctx.fillStyle = `rgba(0, 255, 136, ${intensity * 0.03})`;
			for (let y = 0; y < height; y += 4) {
				ctx.fillRect(0, y, width, 1);
			}
		}

		// Chromatic aberration hint
		if (intensity > 0.5 && Math.random() < 0.02) {
			ctx.globalCompositeOperation = 'screen';
			ctx.fillStyle = `rgba(255, 0, 0, ${intensity * 0.05})`;
			ctx.fillRect(2, 0, width, height);
			ctx.fillStyle = `rgba(0, 0, 255, ${intensity * 0.05})`;
			ctx.fillRect(-2, 0, width, height);
			ctx.globalCompositeOperation = 'source-over';
		}
	}

	function handleMouseMove(e: MouseEvent) {
		mouseX = e.clientX;
		mouseY = e.clientY;

		if (!worldData) return;
		calculateGrid();

		// Check if hovering over an agent
		const agentList = Array.from($agents.values());
		let closestAgent: Agent | null = null;
		let closestDist = 15; // pixel threshold

		for (const agent of agentList) {
			const ax = gridLeft + agent.x * gridSize * cellSize;
			const ay = gridTop + agent.y * gridSize * cellSize;
			const dist = Math.sqrt((mouseX - ax) ** 2 + (mouseY - ay) ** 2);
			if (dist < closestDist) {
				closestDist = dist;
				closestAgent = agent;
			}
		}
		hoverAgent = closestAgent;

		// Check cell hover
		if (!closestAgent) {
			const col = Math.floor((mouseX - gridLeft) / cellSize);
			const row = Math.floor((mouseY - gridTop) / cellSize);
			if (row >= 0 && row < gridSize && col >= 0 && col < gridSize) {
				hoverCell = { row, col };
			} else {
				hoverCell = null;
			}
		} else {
			hoverCell = null;
		}
	}

	function handleClick(e: MouseEvent) {
		if (hoverAgent) {
			// Click agent → zoom to Level 2 (cell) or Level 3 (soul)
			if (e.detail === 2) {
				// Double-click → zoom to soul
				focusAgentId.set(hoverAgent.id);
				zoomLevel.set(3);
			} else {
				// Single click → zoom to cell
				const row = Math.min(gridSize - 1, Math.floor(hoverAgent.y * gridSize));
				const col = Math.min(gridSize - 1, Math.floor(hoverAgent.x * gridSize));
				focusCell.set({ row, col });
				zoomLevel.set(2);
			}
		} else if (hoverCell) {
			// Click cell → zoom to Level 2
			focusCell.set(hoverCell);
			zoomLevel.set(2);
		}
	}

	// Load world data
	async function loadWorld() {
		const rid = $runId;
		if (!rid) return;
		try {
			worldData = await api.getWorld(rid);
			const bondData = await api.getBonds(rid, 0.15, 150);
			bonds = bondData.bonds || [];
		} catch (e) {
			console.error('Failed to load world:', e);
		}
	}

	// Reload world periodically (every 10 ticks)
	$effect(() => {
		const t = $tick;
		if (t > 0 && t % 10 === 0 && $zoomLevel === 1) {
			loadWorld();
		}
	});

	// Initial load
	$effect(() => {
		if ($runId && !worldData) {
			loadWorld();
		}
	});

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

	onDestroy(() => {
		cancelAnimationFrame(animFrame);
	});
</script>

<canvas
	bind:this={canvas}
	class="world-map"
	class:visible={$zoomLevel === 1}
	onmousemove={handleMouseMove}
	onclick={handleClick}
	aria-label="World map"
></canvas>

<style>
	.world-map {
		position: fixed;
		inset: 0;
		z-index: 1;
		opacity: 0;
		transition: opacity 0.4s ease;
		pointer-events: none;
		cursor: crosshair;
	}
	.world-map.visible {
		opacity: 1;
		pointer-events: auto;
	}
</style>
