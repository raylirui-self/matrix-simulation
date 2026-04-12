<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import {
		agents,
		tick,
		matrixState,
		phasePulses,
		type Agent
	} from '$lib/stores/simulation';
	import { zoomLevel, focusCell, focusAgentId, overlays, bondConstellationMode } from '$lib/stores/ui';
	import { api } from '$lib/api/rest';
	import { runId } from '$lib/stores/simulation';

	// ── Belief Particle System ──
	type BeliefParticle = {
		x: number; y: number;
		vx: number; vy: number;
		color: string;
		life: number;     // 0-1, decays per frame
		size: number;
	};

	const INFO_COLORS: Record<string, string> = {
		knowledge: '#4488ff',
		rumor: '#ffcc00',
		propaganda: '#ff3333',
		secret: '#aa44ff',
	};

	let beliefParticles: BeliefParticle[] = [];
	const MAX_PARTICLES = 300;

	function spawnBeliefParticles(agentList: Agent[]) {
		// Spawn particles from agents based on their state
		// High-awareness agents emit secret particles; faction members emit propaganda
		// All agents with faction_id emit belief-colored particles
		for (const agent of agentList) {
			if (agent.is_sentinel || beliefParticles.length >= MAX_PARTICLES) break;
			if (Math.random() > 0.15) continue; // throttle spawning

			const ax = gridLeft + agent.x * gridSize * cellSize;
			const ay = gridTop + agent.y * gridSize * cellSize;

			let infoType: string;
			if (agent.awareness > 0.6) {
				infoType = 'secret';
			} else if (agent.faction_id !== null && Math.random() < 0.5) {
				infoType = 'propaganda';
			} else if (Math.random() < 0.3) {
				infoType = 'rumor';
			} else {
				infoType = 'knowledge';
			}

			// Direction: toward a random nearby agent or random drift
			const angle = Math.random() * Math.PI * 2;
			const speed = 0.3 + Math.random() * 0.8;

			beliefParticles.push({
				x: ax, y: ay,
				vx: Math.cos(angle) * speed,
				vy: Math.sin(angle) * speed,
				color: INFO_COLORS[infoType],
				life: 0.8 + Math.random() * 0.2,
				size: 1.5 + Math.random() * 1.5,
			});
		}
	}

	function updateBeliefParticles() {
		for (let i = beliefParticles.length - 1; i >= 0; i--) {
			const p = beliefParticles[i];
			p.x += p.vx;
			p.y += p.vy;
			p.life -= 0.008;
			p.vx *= 0.99; // gentle drag
			p.vy *= 0.99;
			if (p.life <= 0) {
				beliefParticles.splice(i, 1);
			}
		}
	}

	function drawBeliefParticles(ctx: CanvasRenderingContext2D) {
		for (const p of beliefParticles) {
			ctx.globalAlpha = p.life * 0.7;
			ctx.fillStyle = p.color;
			ctx.beginPath();
			ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
			ctx.fill();
		}
		ctx.globalAlpha = 1;
	}

	// ── Propaganda Wave System ──
	type PropagandaWave = {
		cx: number; cy: number;   // center (canvas coords)
		radius: number;           // current radius
		maxRadius: number;
		color: string;
		life: number;             // 0-1
		factionId: number;
	};

	let propagandaWaves: PropagandaWave[] = [];
	const MAX_WAVES = 20;

	// Faction color palette for waves
	const FACTION_WAVE_COLORS = [
		'rgba(255, 50, 50,',    // red
		'rgba(50, 150, 255,',   // blue
		'rgba(255, 200, 50,',   // gold
		'rgba(50, 255, 150,',   // green
		'rgba(200, 100, 255,',  // purple
		'rgba(255, 150, 50,',   // orange
	];

	function spawnPropagandaWaves(agentList: Agent[]) {
		if (propagandaWaves.length >= MAX_WAVES) return;

		// Faction leaders / high-charisma agents in factions emit propaganda waves
		for (const agent of agentList) {
			if (agent.faction_id === null || agent.is_sentinel) continue;
			if (propagandaWaves.length >= MAX_WAVES) break;
			// Low spawn chance — only notable agents
			if (Math.random() > 0.02) continue;

			const ax = gridLeft + agent.x * gridSize * cellSize;
			const ay = gridTop + agent.y * gridSize * cellSize;

			const colorIdx = (agent.faction_id ?? 0) % FACTION_WAVE_COLORS.length;
			propagandaWaves.push({
				cx: ax, cy: ay,
				radius: 2,
				maxRadius: cellSize * 1.5 + Math.random() * cellSize,
				color: FACTION_WAVE_COLORS[colorIdx],
				life: 1.0,
				factionId: agent.faction_id,
			});
		}
	}

	function updatePropagandaWaves() {
		for (let i = propagandaWaves.length - 1; i >= 0; i--) {
			const w = propagandaWaves[i];
			w.radius += 1.2;
			w.life -= 0.012;
			if (w.life <= 0 || w.radius > w.maxRadius) {
				propagandaWaves.splice(i, 1);
			}
		}
	}

	function drawPropagandaWaves(ctx: CanvasRenderingContext2D) {
		for (const w of propagandaWaves) {
			const alpha = w.life * 0.25;
			ctx.strokeStyle = w.color + alpha + ')';
			ctx.lineWidth = 2;
			ctx.beginPath();
			ctx.arc(w.cx, w.cy, w.radius, 0, Math.PI * 2);
			ctx.stroke();

			// Inner glow ring
			if (w.life > 0.5) {
				ctx.strokeStyle = w.color + (alpha * 0.5) + ')';
				ctx.lineWidth = 4;
				ctx.beginPath();
				ctx.arc(w.cx, w.cy, w.radius * 0.7, 0, Math.PI * 2);
				ctx.stroke();
			}
		}

		// ── Interference patterns where waves from different factions overlap ──
		for (let i = 0; i < propagandaWaves.length; i++) {
			for (let j = i + 1; j < propagandaWaves.length; j++) {
				const a = propagandaWaves[i];
				const b = propagandaWaves[j];
				if (a.factionId === b.factionId) continue;
				const dist = Math.sqrt((a.cx - b.cx) ** 2 + (a.cy - b.cy) ** 2);
				// Check if wave rings intersect
				if (dist < a.radius + b.radius && dist > Math.abs(a.radius - b.radius)) {
					// Draw interference points at the two intersection locations
					const interAlpha = Math.min(a.life, b.life) * 0.4;
					const midX = (a.cx + b.cx) / 2;
					const midY = (a.cy + b.cy) / 2;

					ctx.fillStyle = `rgba(255, 255, 255, ${interAlpha})`;
					ctx.beginPath();
					ctx.arc(midX, midY, 3, 0, Math.PI * 2);
					ctx.fill();

					// Perpendicular interference lines
					const dx = b.cx - a.cx;
					const dy = b.cy - a.cy;
					const nx = -dy / (dist || 1) * 8;
					const ny = dx / (dist || 1) * 8;
					ctx.strokeStyle = `rgba(255, 255, 255, ${interAlpha * 0.5})`;
					ctx.lineWidth = 1;
					ctx.beginPath();
					ctx.moveTo(midX - nx, midY - ny);
					ctx.lineTo(midX + nx, midY + ny);
					ctx.stroke();
				}
			}
		}
	}

	// Spawn particles/waves on tick change
	$effect(() => {
		const t = $tick;
		if (t > 0) {
			const agentList = Array.from($agents.values());
			if ($overlays.has('particles')) {
				spawnBeliefParticles(agentList);
			}
			if ($overlays.has('propaganda')) {
				spawnPropagandaWaves(agentList);
			}
		}
	});

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

	// Consciousness phase base tints
	const CONSCIOUSNESS_COLORS: Record<string, string> = {
		bicameral: '#888888',
		questioning: '#88aacc',
		self_aware: '#00ff88',
		lucid: '#ffd700',
		recursive: '#ff66ff'
	};

	// Toggle for secondary life-phase overlay (press 'L')
	let showLifePhaseOverlay = false;

	function handleKey(e: KeyboardEvent) {
		if (e.key === 'l' || e.key === 'L') {
			showLifePhaseOverlay = !showLifePhaseOverlay;
		}
	}

	// Phase pulse wave animations — spawned by phasePulses store
	type PulseWave = {
		agent_id: number;
		tick: number;
		radius: number;
		life: number;
		color: string;
	};
	let pulseWaves: PulseWave[] = [];
	let seenPulseKeys = new Set<string>();

	$effect(() => {
		const pulses = $phasePulses;
		for (const p of pulses) {
			const key = `${p.agent_id}:${p.tick}`;
			if (seenPulseKeys.has(key)) continue;
			seenPulseKeys.add(key);
			pulseWaves.push({
				agent_id: p.agent_id,
				tick: p.tick,
				radius: 4,
				life: 1.0,
				color: CONSCIOUSNESS_COLORS[p.to_phase] || '#00ff88'
			});
		}
		// Prune seen keys
		if (seenPulseKeys.size > 500) {
			seenPulseKeys = new Set(Array.from(seenPulseKeys).slice(-250));
		}
	});

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

	// ── Consciousness-phase agent rendering ──
	function drawConsciousnessAgent(
		ctx: CanvasRenderingContext2D,
		agent: Agent,
		ax: number,
		ay: number,
		size: number,
		color: string,
		cPhase: string
	) {
		const health = agent.health;
		if (cPhase === 'bicameral') {
			// Grey, translucent, minimal presence
			ctx.globalAlpha = 0.5 * (0.6 + health * 0.4);
			ctx.fillStyle = color;
			ctx.beginPath();
			ctx.arc(ax, ay, size, 0, Math.PI * 2);
			ctx.fill();
			ctx.globalAlpha = 1;
			return;
		}

		if (cPhase === 'questioning') {
			// Faint emotion tint bleed-in + occasional jitter
			const emo = EMOTION_COLORS[agent.emotion] || color;
			ctx.globalAlpha = 0.75;
			ctx.fillStyle = emo;
			const jitter = ((agent.id * 13 + Math.floor(Date.now() / 400)) % 37 === 0) ? 1 : 0;
			ctx.beginPath();
			ctx.arc(ax + jitter, ay, size, 0, Math.PI * 2);
			ctx.fill();
			ctx.globalAlpha = 1;
			return;
		}

		if (cPhase === 'self_aware') {
			// Full color, thin shimmering outline
			ctx.globalAlpha = 0.7 + health * 0.3;
			ctx.fillStyle = color;
			ctx.beginPath();
			ctx.arc(ax, ay, size, 0, Math.PI * 2);
			ctx.fill();
			ctx.globalAlpha = 0.4 + 0.4 * Math.abs(Math.sin(Date.now() / 300 + agent.id));
			ctx.strokeStyle = '#ffffff';
			ctx.lineWidth = 1;
			ctx.beginPath();
			ctx.arc(ax, ay, size + 1.5, 0, Math.PI * 2);
			ctx.stroke();
			ctx.globalAlpha = 1;
			return;
		}

		if (cPhase === 'lucid') {
			// Inner radial glow, light trail, occasional wireframe flicker
			const grad = ctx.createRadialGradient(ax, ay, 0, ax, ay, size + 6);
			grad.addColorStop(0, color);
			grad.addColorStop(0.5, 'rgba(255, 215, 0, 0.5)');
			grad.addColorStop(1, 'rgba(255, 215, 0, 0)');
			ctx.fillStyle = grad;
			ctx.beginPath();
			ctx.arc(ax, ay, size + 6, 0, Math.PI * 2);
			ctx.fill();

			ctx.fillStyle = color;
			ctx.globalAlpha = 0.9;
			ctx.beginPath();
			ctx.arc(ax, ay, size, 0, Math.PI * 2);
			ctx.fill();
			ctx.globalAlpha = 1;

			// Wireframe flicker
			if ((agent.id + Math.floor(Date.now() / 250)) % 11 === 0) {
				ctx.strokeStyle = 'rgba(255, 255, 255, 0.7)';
				ctx.lineWidth = 1;
				ctx.beginPath();
				ctx.moveTo(ax - size, ay);
				ctx.lineTo(ax + size, ay);
				ctx.moveTo(ax, ay - size);
				ctx.lineTo(ax, ay + size);
				ctx.stroke();
			}
			return;
		}

		if (cPhase === 'recursive') {
			// Ghost-copy offset, fractal multi-outline, bright inner core
			ctx.globalAlpha = 0.35;
			ctx.fillStyle = color;
			ctx.beginPath();
			ctx.arc(ax + 2, ay + 2, size, 0, Math.PI * 2);
			ctx.fill();
			ctx.beginPath();
			ctx.arc(ax - 2, ay - 1, size, 0, Math.PI * 2);
			ctx.fill();

			ctx.globalAlpha = 1;
			ctx.fillStyle = '#ffffff';
			ctx.beginPath();
			ctx.arc(ax, ay, size * 0.55, 0, Math.PI * 2);
			ctx.fill();

			ctx.fillStyle = color;
			ctx.globalAlpha = 0.85;
			ctx.beginPath();
			ctx.arc(ax, ay, size, 0, Math.PI * 2);
			ctx.fill();
			ctx.globalAlpha = 1;

			// Fractal outlines
			ctx.strokeStyle = color;
			ctx.lineWidth = 1;
			for (let r = 1; r <= 3; r++) {
				ctx.globalAlpha = 0.25 / r;
				ctx.beginPath();
				ctx.arc(ax, ay, size + r * 2, 0, Math.PI * 2);
				ctx.stroke();
			}
			ctx.globalAlpha = 1;
			return;
		}

		// Fallback — plain circle
		ctx.fillStyle = color;
		ctx.globalAlpha = 0.7 + health * 0.3;
		ctx.beginPath();
		ctx.arc(ax, ay, size, 0, Math.PI * 2);
		ctx.fill();
		ctx.globalAlpha = 1;
	}

	// ── Program icons (visually dominant) ──
	function drawProgramIcon(
		ctx: CanvasRenderingContext2D,
		agent: Agent,
		ax: number,
		ay: number
	) {
		const r = 9; // bigger than regular agents
		ctx.save();
		if (agent.is_enforcer) {
			// Red triangle
			ctx.fillStyle = '#ff2222';
			ctx.strokeStyle = '#ffaaaa';
			ctx.lineWidth = 1.5;
			ctx.beginPath();
			ctx.moveTo(ax, ay - r);
			ctx.lineTo(ax + r, ay + r * 0.8);
			ctx.lineTo(ax - r, ay + r * 0.8);
			ctx.closePath();
			ctx.fill();
			ctx.stroke();
		} else if (agent.is_broker) {
			// Gold diamond
			ctx.fillStyle = '#ffd700';
			ctx.strokeStyle = '#ffffaa';
			ctx.lineWidth = 1.5;
			ctx.beginPath();
			ctx.moveTo(ax, ay - r);
			ctx.lineTo(ax + r, ay);
			ctx.lineTo(ax, ay + r);
			ctx.lineTo(ax - r, ay);
			ctx.closePath();
			ctx.fill();
			ctx.stroke();
		} else if (agent.is_guardian) {
			// Green shield (rounded triangle)
			ctx.fillStyle = '#22cc44';
			ctx.strokeStyle = '#aaffaa';
			ctx.lineWidth = 1.5;
			ctx.beginPath();
			ctx.moveTo(ax, ay - r);
			ctx.lineTo(ax + r, ay - r * 0.3);
			ctx.lineTo(ax + r * 0.6, ay + r);
			ctx.lineTo(ax - r * 0.6, ay + r);
			ctx.lineTo(ax - r, ay - r * 0.3);
			ctx.closePath();
			ctx.fill();
			ctx.stroke();
		} else if (agent.is_locksmith) {
			// Cream key glyph — circle head + stem + tooth
			ctx.fillStyle = '#f5f0dc';
			ctx.strokeStyle = '#ffffff';
			ctx.lineWidth = 1.5;
			ctx.beginPath();
			ctx.arc(ax - r * 0.4, ay, r * 0.5, 0, Math.PI * 2);
			ctx.fill();
			ctx.stroke();
			ctx.fillRect(ax - r * 0.1, ay - 1.5, r, 3);
			ctx.fillRect(ax + r * 0.6, ay - 1.5, 2.5, r * 0.7);
		}
		ctx.restore();
	}

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
				// Convert hex to rgba
				const r = parseInt(color.slice(1, 3), 16);
				const g = parseInt(color.slice(3, 5), 16);
				const b = parseInt(color.slice(5, 7), 16);
				ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;
				ctx.globalAlpha = alpha;
				ctx.lineWidth = bondMode ? bond.strength * 3 : bond.strength * 1.5;
				ctx.beginPath();
				ctx.moveTo(sx, sy);
				ctx.lineTo(tx, ty);
				ctx.stroke();
			}
			ctx.globalAlpha = 1;
		}

		// ── Emotional contagion overlay ──
		if ($overlays.has('contagion')) {
			// Draw translucent aura circles colored by dominant emotion.
			// Overlapping auras create a visual heatmap of emotional contagion.
			const contagionRadius = cellSize * 0.6;
			for (const agent of agentList) {
				if (agent.is_sentinel) continue;
				const ax = gridLeft + agent.x * gridSize * cellSize;
				const ay = gridTop + agent.y * gridSize * cellSize;
				const color = EMOTION_COLORS[agent.emotion] || '#00ff88';
				const r = parseInt(color.slice(1, 3), 16);
				const g = parseInt(color.slice(3, 5), 16);
				const b = parseInt(color.slice(5, 7), 16);

				// Inner aura — stronger
				const grad = ctx.createRadialGradient(ax, ay, 0, ax, ay, contagionRadius);
				grad.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0.18)`);
				grad.addColorStop(0.6, `rgba(${r}, ${g}, ${b}, 0.06)`);
				grad.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);
				ctx.fillStyle = grad;
				ctx.beginPath();
				ctx.arc(ax, ay, contagionRadius, 0, Math.PI * 2);
				ctx.fill();
			}

			// Draw contagion links between nearby agents sharing dominant emotion
			const maxLinks = Math.min(agentList.length, 200);
			for (let i = 0; i < maxLinks; i++) {
				const a = agentList[i];
				if (a.is_sentinel) continue;
				const ax = gridLeft + a.x * gridSize * cellSize;
				const ay = gridTop + a.y * gridSize * cellSize;
				for (let j = i + 1; j < agentList.length; j++) {
					const b = agentList[j];
					if (b.is_sentinel || a.emotion !== b.emotion) continue;
					const bx = gridLeft + b.x * gridSize * cellSize;
					const by = gridTop + b.y * gridSize * cellSize;
					const dist = Math.sqrt((ax - bx) ** 2 + (ay - by) ** 2);
					if (dist < contagionRadius * 2.5) {
						const color = EMOTION_COLORS[a.emotion] || '#00ff88';
						const alpha = Math.max(0.02, 0.12 * (1 - dist / (contagionRadius * 2.5)));
						const cr = parseInt(color.slice(1, 3), 16);
						const cg = parseInt(color.slice(3, 5), 16);
						const cb = parseInt(color.slice(5, 7), 16);
						ctx.strokeStyle = `rgba(${cr}, ${cg}, ${cb}, ${alpha})`;
						ctx.lineWidth = 1;
						ctx.beginPath();
						ctx.moveTo(ax, ay);
						ctx.lineTo(bx, by);
						ctx.stroke();
					}
				}
			}
		}

		// ── Propaganda wave overlay ──
		if ($overlays.has('propaganda')) {
			updatePropagandaWaves();
			drawPropagandaWaves(ctx);
		}

		// ── Belief particle overlay ──
		if ($overlays.has('particles')) {
			updateBeliefParticles();
			drawBeliefParticles(ctx);
		}

		// Update pulse waves once per frame
		for (let i = pulseWaves.length - 1; i >= 0; i--) {
			pulseWaves[i].radius += 1.8;
			pulseWaves[i].life -= 0.025;
			if (pulseWaves[i].life <= 0) pulseWaves.splice(i, 1);
		}

		// Build a quick index for pulse lookups
		const pulseByAgent = new Map<number, PulseWave>();
		for (const w of pulseWaves) pulseByAgent.set(w.agent_id, w);

		// Draw agents
		for (const agent of agentList) {
			const ax = gridLeft + agent.x * gridSize * cellSize;
			const ay = gridTop + agent.y * gridSize * cellSize;

			if (bondMode && !agent.is_protagonist) {
				ctx.fillStyle = 'rgba(0, 255, 136, 0.2)';
				ctx.beginPath();
				ctx.arc(ax, ay, 2, 0, Math.PI * 2);
				ctx.fill();
				continue;
			}

			// ── Programs: distinct shapes, visually dominant ──
			const isProgram =
				agent.is_enforcer || agent.is_broker || agent.is_guardian || agent.is_locksmith;
			if (isProgram) {
				drawProgramIcon(ctx, agent, ax, ay);
				continue;
			}

			// ── Consciousness-phase rendering ──
			const baseSize = 3 + agent.intelligence * 4;
			const size = agent.is_protagonist ? baseSize + 2 : baseSize;
			const cPhase = agent.consciousness_phase || 'bicameral';

			// Base color per consciousness phase, emotion-overridable
			let color = CONSCIOUSNESS_COLORS[cPhase] || '#888888';
			if ($overlays.has('emotions') || $overlays.has('contagion')) {
				color = EMOTION_COLORS[agent.emotion] || color;
			}

			// Sentinel special rendering (Sentinel trumps consciousness visuals)
			if (agent.is_sentinel) {
				color = '#ff0000';
				ctx.strokeStyle = 'rgba(255, 0, 0, 0.15)';
				ctx.lineWidth = 1;
				ctx.beginPath();
				ctx.moveTo(ax, ay);
				ctx.lineTo(
					ax + Math.cos(Date.now() / 500 + agent.id) * 40,
					ay + Math.sin(Date.now() / 500 + agent.id) * 40
				);
				ctx.stroke();
			}

			drawConsciousnessAgent(ctx, agent, ax, ay, size, color, cPhase);

			// Pulse wave on phase threshold crossing
			const pulse = pulseByAgent.get(agent.id);
			if (pulse) {
				ctx.strokeStyle = pulse.color;
				ctx.globalAlpha = Math.max(0, pulse.life * 0.9);
				ctx.lineWidth = 2;
				ctx.beginPath();
				ctx.arc(ax, ay, size + pulse.radius, 0, Math.PI * 2);
				ctx.stroke();
				ctx.globalAlpha = 1;
			}

			// Secondary life-phase overlay (toggle with 'L')
			if (showLifePhaseOverlay) {
				const lifeColor = PHASE_COLORS[agent.phase] || '#00ff88';
				ctx.strokeStyle = lifeColor;
				ctx.globalAlpha = 0.5;
				ctx.lineWidth = 1;
				ctx.beginPath();
				ctx.arc(ax, ay, size + 1.5, 0, Math.PI * 2);
				ctx.stroke();
				ctx.globalAlpha = 1;
			}

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

	// Load world data (with request deduplication)
	let loadingWorld = false;
	async function loadWorld() {
		const rid = $runId;
		if (!rid || loadingWorld) return;
		loadingWorld = true;
		try {
			const [world, bondData] = await Promise.all([
				api.getWorld(rid),
				api.getBonds(rid, 0.15, 150)
			]);
			worldData = world;
			bonds = bondData.bonds || [];
		} catch (e) {
			console.error('Failed to load world:', e);
		} finally {
			loadingWorld = false;
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
		window.addEventListener('keydown', handleKey);

		return () => {
			window.removeEventListener('resize', handleResize);
			window.removeEventListener('keydown', handleKey);
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
