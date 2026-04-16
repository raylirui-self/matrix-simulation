<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import {
		agents,
		tick,
		matrixState,
		phasePulses,
		cycleResetAnimation,
		dreamState,
		nestedSims,
		reincarnationArcs,
		events as eventsFeed,
		type Agent,
		type GhostPayload,
		type NestedEngineDetail,
		type ReincarnationArc
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
	// Toggle for Gnostic Archon overlay (press 'G')
	let showArchonOverlay = false;
	// Toggle for observer mode (press 'O')
	let observerModeEnabled = false;
	let observerModeActive = false;    // true when idle timer fires
	let observerLastInput = Date.now();
	let observerZoomPhase = 0;         // cycles through zoom presets
	let observerFocusId: number | null = null;
	let observerTickerOffset = 0;      // news ticker scroll position
	const OBSERVER_IDLE_MS = 30_000;   // 30s idle before activation
	const OBSERVER_ZOOM_INTERVAL = 10_000; // 10s per zoom level

	// Soul trap chain-break animation state (per agent, one-shot)
	type ChainBreakAnim = {
		x: number; y: number;
		particles: Array<{ angle: number; r: number; life: number }>;
		started_at: number;
	};
	let chainBreakAnims: ChainBreakAnim[] = [];
	let seenChainBreaks = new Set<number>(); // agent IDs that already fired

	function handleKey(e: KeyboardEvent) {
		if (e.key === 'l' || e.key === 'L') {
			showLifePhaseOverlay = !showLifePhaseOverlay;
		}
		if (e.key === 'g' || e.key === 'G') {
			showArchonOverlay = !showArchonOverlay;
		}
		if (e.key === 'o' || e.key === 'O') {
			observerModeEnabled = !observerModeEnabled;
			if (!observerModeEnabled) observerModeActive = false;
		}
		// Any key exits observer mode
		if (observerModeActive) {
			observerModeActive = false;
		}
		observerLastInput = Date.now();
	}

	// ── Ghost manifestation during dreams (Phase 7B) ──
	// Per-ghost client-side state so drift + motes + thread flashes persist
	// across frames. Keyed by source_agent_id. Pruned when ghost disappears
	// from the backend payload.
	type GhostClientState = {
		driftX: number; // pixel offset from base x
		driftY: number;
		vx: number;
		vy: number;
		motes: Array<{ ox: number; oy: number; life: number; size: number }>;
		threads: Map<number, { life: number }>; // living_agent_id -> thread state
	};
	const ghostClientState = new Map<number, GhostClientState>();

	// Shatter animation state for each destroyed Archon, keyed by system name.
	type ShatterParticle = { x: number; y: number; vx: number; vy: number; life: number; color: string };
	type ShatterAnim = { started_at: number; particles: ShatterParticle[] };
	const archonShatterAnims = new Map<string, ShatterAnim>();
	// Track which systems were alive last frame so we can detect the
	// destruction edge and spawn the shatter burst.
	const prevArchonAlive = new Map<string, boolean>();

	// Archon system metadata — spec-fixed quadrants + sigil colors.
	// Backend x/y fields are ignored in favor of these visual quadrants
	// because TODO.md dictates the layout directly.
	const ARCHON_LAYOUT: Record<string, { quadrant: 'tl' | 'tr' | 'bl' | 'br'; color: string }> = {
		emotion:        { quadrant: 'tl', color: '#ff4466' },
		economy:        { quadrant: 'tr', color: '#ffd700' },
		belief:         { quadrant: 'bl', color: '#aa66ff' },
		communication: { quadrant: 'br', color: '#00ddff' }
	};

	// ── Faction territory borders (overlay, key 'F') ──
	// A compact hand-picked palette matched by index = faction.id % N.
	const FACTION_BORDER_COLORS = [
		'#ff4466',
		'#4488ff',
		'#ffd700',
		'#44ff88',
		'#aa66ff',
		'#ff8844',
		'#66eecc',
		'#ff66cc'
	];
	function factionColor(factionId: number): string {
		return FACTION_BORDER_COLORS[((factionId % FACTION_BORDER_COLORS.length) + FACTION_BORDER_COLORS.length) % FACTION_BORDER_COLORS.length];
	}

	// Jarvis-march (gift wrapping) convex hull. O(n*h), zero dependencies.
	// Returns hull points in counter-clockwise order.
	function convexHull(points: Array<{ x: number; y: number }>): Array<{ x: number; y: number }> {
		const n = points.length;
		if (n < 3) return points.slice();
		// Find leftmost
		let leftmost = 0;
		for (let i = 1; i < n; i++) {
			if (points[i].x < points[leftmost].x) leftmost = i;
		}
		const hull: Array<{ x: number; y: number }> = [];
		let p = leftmost;
		do {
			hull.push(points[p]);
			let q = (p + 1) % n;
			for (let i = 0; i < n; i++) {
				// Orientation: cross product sign
				const cross =
					(points[q].y - points[p].y) * (points[i].x - points[q].x) -
					(points[q].x - points[p].x) * (points[i].y - points[q].y);
				if (cross < 0) q = i;
			}
			p = q;
			if (hull.length > n) break; // safety
		} while (p !== leftmost);
		return hull;
	}

	function drawFactionBorders(ctx: CanvasRenderingContext2D, agentList: Agent[]) {
		// Group live, non-sentinel members by faction_id
		const groups = new Map<number, Array<{ x: number; y: number }>>();
		for (const a of agentList) {
			if (a.faction_id == null || a.is_sentinel) continue;
			const ax = gridLeft + a.x * gridSize * cellSize;
			const ay = gridTop + a.y * gridSize * cellSize;
			let arr = groups.get(a.faction_id);
			if (!arr) {
				arr = [];
				groups.set(a.faction_id, arr);
			}
			arr.push({ x: ax, y: ay });
		}
		for (const [fid, pts] of groups) {
			if (pts.length < 3) continue;
			const hull = convexHull(pts);
			if (hull.length < 3) continue;
			const color = factionColor(fid);
			// Thin border
			ctx.save();
			ctx.strokeStyle = color;
			ctx.lineWidth = 1.5;
			ctx.globalAlpha = 0.75;
			ctx.beginPath();
			ctx.moveTo(hull[0].x, hull[0].y);
			for (let i = 1; i < hull.length; i++) ctx.lineTo(hull[i].x, hull[i].y);
			ctx.closePath();
			ctx.stroke();
			// Very faint fill for legibility
			ctx.globalAlpha = 0.05;
			ctx.fillStyle = color;
			ctx.fill();
			ctx.restore();
		}
	}

	// ── Ghost + Archon rendering (Phase 7B) ──
	function ensureGhostState(ghostId: number): GhostClientState {
		let st = ghostClientState.get(ghostId);
		if (!st) {
			st = {
				driftX: 0,
				driftY: 0,
				vx: (Math.random() - 0.5) * 0.35,
				vy: (Math.random() - 0.5) * 0.35,
				motes: [],
				threads: new Map()
			};
			ghostClientState.set(ghostId, st);
		}
		return st;
	}

	function pruneGhostState(activeIds: Set<number>) {
		for (const id of Array.from(ghostClientState.keys())) {
			if (!activeIds.has(id)) ghostClientState.delete(id);
		}
	}

	function updateAndDrawGhosts(
		ctx: CanvasRenderingContext2D,
		ghosts: GhostPayload[],
		lucidIds: Set<number>
	) {
		const activeIds = new Set<number>();
		for (const g of ghosts) activeIds.add(g.source_agent_id);
		pruneGhostState(activeIds);

		for (const ghost of ghosts) {
			const st = ensureGhostState(ghost.source_agent_id);

			// Slow random walk drift — ignore terrain
			st.vx += (Math.random() - 0.5) * 0.08;
			st.vy += (Math.random() - 0.5) * 0.08;
			st.vx *= 0.96;
			st.vy *= 0.96;
			// Soft cap on drift magnitude
			const maxDrift = cellSize * 0.9;
			st.driftX = Math.max(-maxDrift, Math.min(maxDrift, st.driftX + st.vx));
			st.driftY = Math.max(-maxDrift, Math.min(maxDrift, st.driftY + st.vy));

			const baseX = gridLeft + ghost.x * gridSize * cellSize;
			const baseY = gridTop + ghost.y * gridSize * cellSize;
			const gx = baseX + st.driftX;
			const gy = baseY + st.driftY;

			// Silhouette — translucent cyan-white glow + inner core
			const grad = ctx.createRadialGradient(gx, gy, 0, gx, gy, 14);
			grad.addColorStop(0, 'rgba(230, 255, 255, 0.85)');
			grad.addColorStop(0.4, 'rgba(160, 220, 255, 0.45)');
			grad.addColorStop(1, 'rgba(120, 200, 255, 0)');
			ctx.fillStyle = grad;
			ctx.beginPath();
			ctx.arc(gx, gy, 14, 0, Math.PI * 2);
			ctx.fill();

			// Ghostly body
			ctx.globalAlpha = 0.55;
			ctx.fillStyle = 'rgba(220, 245, 255, 0.9)';
			ctx.beginPath();
			ctx.arc(gx, gy, 4, 0, Math.PI * 2);
			ctx.fill();
			ctx.globalAlpha = 1;

			// Mote particles — spawn occasionally, then update
			if (st.motes.length < 8 && Math.random() < 0.35) {
				const angle = Math.random() * Math.PI * 2;
				const r = 4 + Math.random() * 6;
				st.motes.push({
					ox: Math.cos(angle) * r,
					oy: Math.sin(angle) * r,
					life: 0.9 + Math.random() * 0.1,
					size: 0.8 + Math.random() * 1.2
				});
			}
			for (let i = st.motes.length - 1; i >= 0; i--) {
				const m = st.motes[i];
				m.ox *= 1.015;
				m.oy *= 1.015;
				m.life -= 0.018;
				if (m.life <= 0) {
					st.motes.splice(i, 1);
					continue;
				}
				ctx.globalAlpha = m.life;
				ctx.fillStyle = '#ffffff';
				ctx.beginPath();
				ctx.arc(gx + m.ox, gy + m.oy, m.size, 0, Math.PI * 2);
				ctx.fill();
			}
			ctx.globalAlpha = 1;

			// Golden memory-transfer threads to nearby living bonded agents
			const bondedIds = ghost.bonded_living_ids || [];
			const proxThreshold = cellSize * 1.8;
			for (const bid of bondedIds) {
				const living = $agents.get(bid);
				if (!living) continue;
				const lx = gridLeft + living.x * gridSize * cellSize;
				const ly = gridTop + living.y * gridSize * cellSize;
				const dist = Math.hypot(lx - gx, ly - gy);
				if (dist > proxThreshold) {
					// Out of range — decay existing thread
					const existing = st.threads.get(bid);
					if (existing) {
						existing.life -= 0.04;
						if (existing.life <= 0) st.threads.delete(bid);
					}
					continue;
				}
				// In range — establish or refresh thread (life ~ 1-2s at 60fps)
				let thread = st.threads.get(bid);
				if (!thread) {
					thread = { life: 1.0 };
					st.threads.set(bid, thread);
				} else if (thread.life < 0.6) {
					thread.life = Math.min(1.0, thread.life + 0.5);
				}
				thread.life -= 0.008;
				if (thread.life <= 0) {
					st.threads.delete(bid);
					continue;
				}
				ctx.strokeStyle = `rgba(255, 215, 120, ${thread.life * 0.85})`;
				ctx.lineWidth = 1.2;
				ctx.beginPath();
				ctx.moveTo(gx, gy);
				ctx.lineTo(lx, ly);
				ctx.stroke();
			}

			// Lucid dreamer core + sky beam (only if this ghost's agent is lucid;
			// lucid-living-agent rendering below handles the living variant too)
			if (lucidIds.has(ghost.source_agent_id)) {
				drawLucidBeam(ctx, gx, gy);
			}
		}
	}

	function drawLucidBeam(ctx: CanvasRenderingContext2D, ax: number, ay: number) {
		// Bright pulsing core
		const pulse = 0.6 + 0.4 * Math.sin(Date.now() / 220);
		const coreGrad = ctx.createRadialGradient(ax, ay, 0, ax, ay, 12);
		coreGrad.addColorStop(0, `rgba(255, 255, 255, ${0.9 * pulse})`);
		coreGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');
		ctx.fillStyle = coreGrad;
		ctx.beginPath();
		ctx.arc(ax, ay, 12, 0, Math.PI * 2);
		ctx.fill();
		// Vertical beam to the top of the canvas
		const beamGrad = ctx.createLinearGradient(ax, 0, ax, ay);
		beamGrad.addColorStop(0, 'rgba(255, 255, 255, 0)');
		beamGrad.addColorStop(1, `rgba(255, 255, 255, ${0.35 * pulse})`);
		ctx.fillStyle = beamGrad;
		ctx.fillRect(ax - 2, 0, 4, ay);
		// Thin core line for emphasis
		ctx.strokeStyle = `rgba(255, 255, 255, ${0.55 * pulse})`;
		ctx.lineWidth = 1;
		ctx.beginPath();
		ctx.moveTo(ax, 0);
		ctx.lineTo(ax, ay);
		ctx.stroke();
	}

	// ── Archon overlay ──
	function archonQuadrantCenter(quadrant: 'tl' | 'tr' | 'bl' | 'br'): { x: number; y: number } {
		const span = gridSize * cellSize;
		const qx = quadrant === 'tl' || quadrant === 'bl' ? gridLeft + span * 0.25 : gridLeft + span * 0.75;
		const qy = quadrant === 'tl' || quadrant === 'tr' ? gridTop + span * 0.25 : gridTop + span * 0.75;
		return { x: qx, y: qy };
	}

	function drawArchonSigil(
		ctx: CanvasRenderingContext2D,
		systemName: string,
		cx: number,
		cy: number,
		color: string,
		health: number,
		alive: boolean
	) {
		const size = 22;
		const alpha = alive ? 0.6 + health * 0.4 : 0.15;
		ctx.save();
		ctx.globalAlpha = alpha;
		ctx.strokeStyle = color;
		ctx.fillStyle = color;
		ctx.lineWidth = 2;

		// Gentle idle rotation / pulse
		const t = Date.now() / 1400;

		if (systemName === 'emotion') {
			// Triangle (pointing up)
			ctx.beginPath();
			ctx.moveTo(cx, cy - size);
			ctx.lineTo(cx + size * 0.92, cy + size * 0.7);
			ctx.lineTo(cx - size * 0.92, cy + size * 0.7);
			ctx.closePath();
			ctx.stroke();
			// Inner smaller triangle
			ctx.globalAlpha = alpha * 0.35;
			ctx.beginPath();
			ctx.moveTo(cx, cy - size * 0.5);
			ctx.lineTo(cx + size * 0.46, cy + size * 0.35);
			ctx.lineTo(cx - size * 0.46, cy + size * 0.35);
			ctx.closePath();
			ctx.fill();
		} else if (systemName === 'economy') {
			// Cube (square with isometric back-face hint)
			ctx.beginPath();
			ctx.rect(cx - size * 0.8, cy - size * 0.8, size * 1.6, size * 1.6);
			ctx.stroke();
			ctx.beginPath();
			ctx.moveTo(cx - size * 0.8, cy - size * 0.8);
			ctx.lineTo(cx - size * 0.4, cy - size * 1.2);
			ctx.lineTo(cx + size * 1.2, cy - size * 1.2);
			ctx.lineTo(cx + size * 0.8, cy - size * 0.8);
			ctx.stroke();
			ctx.beginPath();
			ctx.moveTo(cx + size * 0.8, cy - size * 0.8);
			ctx.lineTo(cx + size * 1.2, cy - size * 1.2);
			ctx.lineTo(cx + size * 1.2, cy + size * 0.4);
			ctx.lineTo(cx + size * 0.8, cy + size * 0.8);
			ctx.stroke();
		} else if (systemName === 'belief') {
			// Pentagram (5-pointed star connecting every other vertex)
			const pts: Array<[number, number]> = [];
			for (let i = 0; i < 5; i++) {
				const a = -Math.PI / 2 + (i * Math.PI * 2) / 5 + Math.sin(t) * 0.03;
				pts.push([cx + Math.cos(a) * size, cy + Math.sin(a) * size]);
			}
			ctx.beginPath();
			for (let i = 0; i < 5; i++) {
				const p = pts[(i * 2) % 5];
				if (i === 0) ctx.moveTo(p[0], p[1]);
				else ctx.lineTo(p[0], p[1]);
			}
			ctx.closePath();
			ctx.stroke();
		} else if (systemName === 'communication') {
			// Double helix (two interleaved sine waves)
			ctx.beginPath();
			for (let i = 0; i <= 24; i++) {
				const p = i / 24;
				const x = cx + (p - 0.5) * size * 2.0;
				const y = cy + Math.sin(p * Math.PI * 4 + t) * size * 0.55;
				if (i === 0) ctx.moveTo(x, y);
				else ctx.lineTo(x, y);
			}
			ctx.stroke();
			ctx.beginPath();
			for (let i = 0; i <= 24; i++) {
				const p = i / 24;
				const x = cx + (p - 0.5) * size * 2.0;
				const y = cy + Math.sin(p * Math.PI * 4 + t + Math.PI) * size * 0.55;
				if (i === 0) ctx.moveTo(x, y);
				else ctx.lineTo(x, y);
			}
			ctx.stroke();
		}

		// Health bar beneath sigil
		ctx.globalAlpha = alive ? 0.85 : 0.3;
		const barW = size * 2;
		const barH = 3;
		const barX = cx - barW / 2;
		const barY = cy + size + 10;
		ctx.fillStyle = 'rgba(0, 0, 0, 0.55)';
		ctx.fillRect(barX, barY, barW, barH);
		ctx.fillStyle = color;
		ctx.fillRect(barX, barY, barW * Math.max(0, Math.min(1, health)), barH);
		ctx.strokeStyle = 'rgba(255,255,255,0.3)';
		ctx.lineWidth = 0.5;
		ctx.strokeRect(barX, barY, barW, barH);

		// Label
		ctx.globalAlpha = alive ? 0.7 : 0.25;
		ctx.fillStyle = color;
		ctx.font = '9px JetBrains Mono';
		ctx.textAlign = 'center';
		ctx.fillText(systemName.toUpperCase(), cx, barY + 14);
		ctx.restore();
	}

	function spawnArchonShatter(systemName: string, cx: number, cy: number, color: string) {
		const particles: ShatterParticle[] = [];
		const count = 32;
		for (let i = 0; i < count; i++) {
			const angle = Math.random() * Math.PI * 2;
			const speed = 0.6 + Math.random() * 2.2;
			particles.push({
				x: cx,
				y: cy,
				vx: Math.cos(angle) * speed,
				vy: Math.sin(angle) * speed - 0.8,
				life: 1.0,
				color
			});
		}
		archonShatterAnims.set(systemName, { started_at: Date.now(), particles });
	}

	function updateAndDrawShatterAnims(ctx: CanvasRenderingContext2D) {
		for (const [name, anim] of archonShatterAnims) {
			let allDead = true;
			for (const p of anim.particles) {
				p.vy += 0.12; // gravity — rain down
				p.x += p.vx;
				p.y += p.vy;
				p.life -= 0.012;
				if (p.life > 0) {
					allDead = false;
					ctx.globalAlpha = p.life;
					ctx.fillStyle = p.color;
					ctx.fillRect(p.x - 1, p.y - 1, 2, 2);
				}
			}
			ctx.globalAlpha = 1;
			if (allDead) archonShatterAnims.delete(name);
		}
	}

	function drawArchonOverlay(ctx: CanvasRenderingContext2D) {
		const mx = $matrixState;
		const archons = (mx.archons || []) as Array<{
			system_name: string;
			health: number;
			alive: boolean;
		}>;
		// If no data has arrived yet, show empty placeholders so users still
		// see the spec layout rather than an invisible overlay.
		const layoutNames = Object.keys(ARCHON_LAYOUT);
		const byName = new Map<string, { system_name: string; health: number; alive: boolean }>();
		for (const a of archons) byName.set(a.system_name, a);

		for (const name of layoutNames) {
			const layout = ARCHON_LAYOUT[name];
			const { x: cx, y: cy } = archonQuadrantCenter(layout.quadrant);
			const snap = byName.get(name);
			const alive = snap ? snap.alive : true;
			const health = snap ? snap.health : 1;

			// Edge-trigger shatter: was alive, now destroyed
			const wasAlive = prevArchonAlive.get(name);
			if (wasAlive === true && !alive) {
				spawnArchonShatter(name, cx, cy, layout.color);
			}
			prevArchonAlive.set(name, alive);

			drawArchonSigil(ctx, name, cx, cy, layout.color, health, alive);
		}
		updateAndDrawShatterAnims(ctx);
	}

	// ── Cycle reset canvas effect: glow artifact cells during the whiteout ──
	function drawCycleResetGlow(ctx: CanvasRenderingContext2D) {
		const anim = $cycleResetAnimation;
		if (!anim.active || !worldData?.cells) return;
		const elapsed = Date.now() - anim.started_at;
		// Ramp in over 400ms, hold, fade out after 3000ms over ~1s
		let strength = 0;
		if (elapsed < 400) strength = elapsed / 400;
		else if (elapsed < 3000) strength = 1;
		else if (elapsed < 4000) strength = Math.max(0, 1 - (elapsed - 3000) / 1000);
		else strength = 0;
		if (strength <= 0) return;

		for (const cell of worldData.cells) {
			if (!cell.has_artifact) continue;
			const cx = gridLeft + cell.col * cellSize + cellSize / 2;
			const cy = gridTop + cell.row * cellSize + cellSize / 2;
			const r = cellSize * 0.85;
			const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
			grad.addColorStop(0, `rgba(255, 255, 220, ${0.85 * strength})`);
			grad.addColorStop(0.4, `rgba(255, 215, 140, ${0.55 * strength})`);
			grad.addColorStop(1, 'rgba(255, 200, 100, 0)');
			ctx.save();
			ctx.globalCompositeOperation = 'lighter';
			ctx.fillStyle = grad;
			ctx.beginPath();
			ctx.arc(cx, cy, r, 0, Math.PI * 2);
			ctx.fill();
			ctx.restore();
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

	// ── Phase 7C: Nested Simulation Windows ──
	function drawNestedSimWindows(ctx: CanvasRenderingContext2D) {
		const engines = $nestedSims.engines;
		if (!engines || engines.length === 0) return;

		for (const eng of engines) {
			const bx = gridLeft + eng.builder_x * gridSize * cellSize;
			const by = gridTop + eng.builder_y * gridSize * cellSize;
			// Position window offset from builder
			const winW = 48;
			const winH = 48;
			const wx = bx + 12;
			const wy = by - winH - 4;

			// Background
			ctx.save();
			ctx.fillStyle = 'rgba(0, 0, 0, 0.85)';
			ctx.fillRect(wx, wy, winW, winH);

			// Border color = builder's consciousness phase (approximate from awareness)
			const aw = eng.max_awareness;
			let borderColor = '#888888';
			if (aw >= 0.7) borderColor = '#ff66ff';
			else if (aw >= 0.5) borderColor = '#ffd700';
			else if (aw >= 0.3) borderColor = '#00ff88';
			else if (aw >= 0.1) borderColor = '#88aacc';

			// Pulsing border
			const pulse = 0.6 + 0.4 * Math.sin(Date.now() / 300);
			ctx.strokeStyle = borderColor;
			ctx.globalAlpha = pulse;
			ctx.lineWidth = 1.5;
			ctx.strokeRect(wx, wy, winW, winH);
			ctx.globalAlpha = 1;

			// Draw mini 4x4 grid lines
			const subSize = eng.sub_grid_size || 4;
			const subCell = winW / subSize;
			ctx.strokeStyle = 'rgba(0, 255, 136, 0.15)';
			ctx.lineWidth = 0.5;
			for (let i = 1; i < subSize; i++) {
				ctx.beginPath();
				ctx.moveTo(wx + i * subCell, wy);
				ctx.lineTo(wx + i * subCell, wy + winH);
				ctx.stroke();
				ctx.beginPath();
				ctx.moveTo(wx, wy + i * subCell);
				ctx.lineTo(wx + winW, wy + i * subCell);
				ctx.stroke();
			}

			// Draw sub-agents as tiny dots
			for (const sa of eng.sub_agents) {
				const sx = wx + sa.x * winW;
				const sy = wy + sa.y * winH;
				const dotAlpha = 0.5 + sa.aw * 0.5;
				ctx.globalAlpha = dotAlpha;
				ctx.fillStyle = sa.aw > 0.5 ? '#ffd700' : '#00ff88';
				ctx.beginPath();
				ctx.arc(sx, sy, 1.5, 0, Math.PI * 2);
				ctx.fill();
			}
			ctx.globalAlpha = 1;

			// Glitch/crack artifacts if recursive paradox detected
			if (eng.has_paradox) {
				ctx.strokeStyle = 'rgba(255, 50, 50, 0.8)';
				ctx.lineWidth = 1;
				// Diagonal cracks
				const t = Date.now() / 500;
				for (let c = 0; c < 3; c++) {
					const cx1 = wx + ((c * 17 + Math.sin(t + c)) % winW);
					const cy1 = wy + ((c * 11 + Math.cos(t + c * 2)) % winH);
					ctx.beginPath();
					ctx.moveTo(cx1, cy1);
					ctx.lineTo(cx1 + 6 + c * 3, cy1 + 8 + c * 2);
					ctx.lineTo(cx1 + 3, cy1 + 14 + c);
					ctx.stroke();
				}
			}

			// Label
			ctx.fillStyle = 'rgba(200, 200, 200, 0.6)';
			ctx.font = '7px JetBrains Mono';
			ctx.textAlign = 'left';
			ctx.fillText(`WE#${eng.engine_id} [${eng.alive_count}]`, wx + 2, wy + winH + 8);
			ctx.restore();
		}
	}

	// ── Phase 7C: Artifact Terrain Rendering ──
	function drawArtifactTerrain(ctx: CanvasRenderingContext2D) {
		if (!worldData?.cells) return;
		const currentCycle = $matrixState.cycle_number || 1;

		for (const cell of worldData.cells) {
			if (!cell.has_artifact || !cell.artifacts?.length) continue;
			const x = gridLeft + cell.col * cellSize;
			const y = gridTop + cell.row * cellSize;
			const count = cell.artifacts.length;
			// Richness factor: more artifacts = richer visual
			const richness = Math.min(1, count / 5);

			for (let i = 0; i < Math.min(count, 5); i++) {
				const art = cell.artifacts[i];
				// Age-based transparency: older = more transparent
				const cycleDiff = Math.max(0, currentCycle - (art.cycle_number || 1));
				const ageAlpha = Math.max(0.15, 1.0 - cycleDiff * 0.2);

				if (art.type === 'ruin') {
					// Faint architectural outlines — thin grey rectangles
					ctx.save();
					ctx.globalAlpha = ageAlpha * (0.2 + richness * 0.15);
					ctx.strokeStyle = '#888888';
					ctx.lineWidth = 0.5;
					const rw = cellSize * (0.3 + i * 0.08);
					const rh = cellSize * (0.2 + i * 0.06);
					const rx = x + cellSize * 0.2 + i * 3;
					const ry = y + cellSize * 0.3 + i * 2;
					ctx.strokeRect(rx, ry, rw, rh);
					// Inner wall hint
					if (richness > 0.4) {
						ctx.strokeRect(rx + 3, ry + 2, rw * 0.5, rh * 0.6);
					}
					ctx.restore();
				} else if (art.type === 'inscription') {
					// Small glowing text fragment (only visible detail on hover)
					ctx.save();
					ctx.globalAlpha = ageAlpha * (0.15 + richness * 0.1);
					ctx.fillStyle = '#ffd700';
					// Tiny glyph marks
					ctx.font = '6px JetBrains Mono';
					ctx.textAlign = 'center';
					const gx = x + cellSize * 0.5 + i * 4 - 6;
					const gy = y + cellSize * 0.6 + i * 3;
					ctx.fillText('⟐', gx, gy);
					// On hover, show more detail
					if (hoverCell && hoverCell.row === cell.row && hoverCell.col === cell.col) {
						ctx.globalAlpha = ageAlpha * 0.7;
						ctx.font = '8px JetBrains Mono';
						ctx.fillText(art.faction_name?.slice(0, 6) || '???', gx, gy + 10);
					}
					ctx.restore();
				} else if (art.type === 'tech_remnant') {
					// Metallic shimmer particle effect
					ctx.save();
					const shimmerT = Date.now() / 400 + i * 1.3;
					ctx.globalAlpha = ageAlpha * (0.12 + richness * 0.1);
					for (let p = 0; p < 3 + Math.floor(richness * 4); p++) {
						const px = x + cellSize * (0.2 + ((p * 13 + i * 7) % 60) / 100);
						const py = y + cellSize * (0.2 + ((p * 17 + i * 11) % 60) / 100);
						const shimmer = 0.4 + 0.6 * Math.abs(Math.sin(shimmerT + p * 0.8));
						ctx.fillStyle = `rgba(192, 210, 230, ${shimmer})`;
						ctx.beginPath();
						ctx.arc(px, py, 1 + richness, 0, Math.PI * 2);
						ctx.fill();
					}
					ctx.restore();
				}
			}

			// Cell-level richness indicator: subtle glow for 5+ artifacts
			if (count >= 5) {
				ctx.save();
				ctx.globalCompositeOperation = 'lighter';
				const grad = ctx.createRadialGradient(
					x + cellSize / 2, y + cellSize / 2, 0,
					x + cellSize / 2, y + cellSize / 2, cellSize * 0.45
				);
				grad.addColorStop(0, 'rgba(255, 215, 100, 0.06)');
				grad.addColorStop(1, 'rgba(255, 215, 100, 0)');
				ctx.fillStyle = grad;
				ctx.fillRect(x, y, cellSize, cellSize);
				ctx.restore();
			}
		}
	}

	// ── Phase 7C: Soul Trap / Reincarnation Visuals ──
	function drawReincarnationVisuals(ctx: CanvasRenderingContext2D, agentList: Agent[]) {
		const now = Date.now();

		// 1. Ghost trail arcs from death → birth
		const arcs = $reincarnationArcs;
		for (const arc of arcs) {
			const elapsed = now - arc.created_at;
			if (elapsed > 3500) continue;
			const fade = Math.max(0, 1 - elapsed / 3500);

			const dx = gridLeft + arc.death_x * gridSize * cellSize;
			const dy = gridTop + arc.death_y * gridSize * cellSize;
			const bx = gridLeft + arc.birth_x * gridSize * cellSize;
			const by = gridTop + arc.birth_y * gridSize * cellSize;

			// Draw a quadratic bezier arc
			const midX = (dx + bx) / 2;
			const midY = Math.min(dy, by) - 30; // arc above
			ctx.save();
			ctx.globalAlpha = fade * 0.6;
			ctx.strokeStyle = arc.soul_trap_broken ? '#ffd700' : '#88ccff';
			ctx.lineWidth = 1.5;
			ctx.setLineDash([4, 4]);
			ctx.beginPath();
			ctx.moveTo(dx, dy);
			ctx.quadraticCurveTo(midX, midY, bx, by);
			ctx.stroke();
			ctx.setLineDash([]);

			// Small dot at birth end
			ctx.fillStyle = arc.soul_trap_broken ? '#ffd700' : '#88ccff';
			ctx.beginPath();
			ctx.arc(bx, by, 3 * fade, 0, Math.PI * 2);
			ctx.fill();
			ctx.restore();
		}

		// 2. Per-agent: incarnation dots + past-life memory flash + chain break
		for (const agent of agentList) {
			if (agent.is_sentinel) continue;
			const ax = gridLeft + agent.x * gridSize * cellSize;
			const ay = gridTop + agent.y * gridSize * cellSize;
			const baseSize = 3 + agent.intelligence * 4;
			const isProgram =
				agent.is_enforcer || agent.is_broker || agent.is_guardian || agent.is_locksmith;

			// Incarnation count dots beneath agent
			if (agent.incarnation_count > 1 && !isProgram) {
				const dotCount = Math.min(agent.incarnation_count - 1, 8);
				const dotY = ay + baseSize + 5;
				const startX = ax - (dotCount - 1) * 2.5;
				ctx.save();
				ctx.globalAlpha = 0.6;
				ctx.fillStyle = '#88ccff';
				for (let d = 0; d < dotCount; d++) {
					ctx.beginPath();
					ctx.arc(startX + d * 5, dotY, 1.2, 0, Math.PI * 2);
					ctx.fill();
				}
				ctx.restore();
			}

			// Past-life memory flash — occasional hue shift
			if (agent.past_life_memories > 0 && !isProgram) {
				const flashCycle = (agent.id * 37 + Math.floor(now / 600)) % 50;
				if (flashCycle < 3) {
					ctx.save();
					ctx.globalAlpha = 0.35;
					ctx.fillStyle = '#cc88ff'; // purple-ish past-life hue
					ctx.beginPath();
					ctx.arc(ax, ay, baseSize + 2, 0, Math.PI * 2);
					ctx.fill();
					ctx.restore();
				}
			}

			// Chain-break animation (one-shot when soul_trap_broken first appears)
			if (agent.soul_trap_broken && !seenChainBreaks.has(agent.id)) {
				seenChainBreaks.add(agent.id);
				const particles: Array<{ angle: number; r: number; life: number }> = [];
				for (let i = 0; i < 12; i++) {
					particles.push({
						angle: (i / 12) * Math.PI * 2,
						r: 5,
						life: 1.0
					});
				}
				chainBreakAnims.push({ x: ax, y: ay, particles, started_at: now });
			}
		}

		// 3. Update and draw chain-break animations
		for (let i = chainBreakAnims.length - 1; i >= 0; i--) {
			const anim = chainBreakAnims[i];
			let allDead = true;
			for (const p of anim.particles) {
				p.r += 1.2;
				p.life -= 0.018;
				if (p.life <= 0) continue;
				allDead = false;
				const px = anim.x + Math.cos(p.angle) * p.r;
				const py = anim.y + Math.sin(p.angle) * p.r;
				ctx.save();
				ctx.globalAlpha = p.life * 0.9;
				ctx.fillStyle = '#ffd700';
				// Chain link shape: small rectangle
				ctx.fillRect(px - 2, py - 1, 4, 2);
				ctx.strokeStyle = '#ffee88';
				ctx.lineWidth = 0.5;
				ctx.strokeRect(px - 2, py - 1, 4, 2);
				ctx.restore();
			}
			if (allDead || now - anim.started_at > 3000) {
				chainBreakAnims.splice(i, 1);
			}
		}

		// Prune old seen chain breaks (cap memory)
		if (seenChainBreaks.size > 500) {
			seenChainBreaks = new Set(Array.from(seenChainBreaks).slice(-250));
		}
	}

	// ── Phase 7C: Observer Mode (auto-narration) ──
	// Narration template strings — deterministic, no LLM
	function getObserverNarration(agent: Agent): string {
		if (agent.is_anomaly) return `Agent #${agent.id} is THE ONE — awareness at ${(agent.awareness * 100).toFixed(0)}%`;
		if (agent.consciousness_phase === 'recursive') return `Agent #${agent.id} sees simulations within simulations...`;
		if (agent.consciousness_phase === 'lucid') return `Agent #${agent.id} is questioning reality for the first time...`;
		if (agent.redpilled) return `Agent #${agent.id} has seen beyond the veil. There is no going back.`;
		if (agent.soul_trap_broken) return `Agent #${agent.id} broke free of the soul trap — memories persist across lives`;
		if (agent.is_enforcer) return `Enforcer #${agent.id} patrols the simulation, hunting the aware...`;
		if (agent.is_locksmith) return `The Locksmith #${agent.id} forges escape routes through reality...`;
		if (agent.awareness > 0.4) return `Agent #${agent.id} senses something is wrong with the world...`;
		if (agent.emotion === 'grief') return `Agent #${agent.id} mourns a loss they cannot explain...`;
		if (agent.emotion === 'anger') return `Agent #${agent.id} rages against the unseen machine...`;
		return `Agent #${agent.id} lives unaware, a cog in the great simulation.`;
	}

	function pickInterestingAgent(agentList: Agent[]): Agent | null {
		if (agentList.length === 0) return null;
		// Score: awareness dominates, with bonuses for special states
		let best: Agent | null = null;
		let bestScore = -1;
		for (const a of agentList) {
			if (a.is_sentinel) continue;
			let score = a.awareness * 3;
			if (a.is_anomaly) score += 5;
			if (a.consciousness_phase === 'lucid' || a.consciousness_phase === 'recursive') score += 2;
			if (a.redpilled) score += 1.5;
			if (a.soul_trap_broken) score += 1;
			if (a.is_enforcer || a.is_locksmith) score += 0.5;
			if (score > bestScore) {
				bestScore = score;
				best = a;
			}
		}
		return best;
	}

	function drawObserverOverlay(ctx: CanvasRenderingContext2D, agentList: Agent[]) {
		if (!observerModeActive) return;

		const now = Date.now();

		// Auto-focus: pick interesting agent and show narration
		const zoomPhase = Math.floor((now / OBSERVER_ZOOM_INTERVAL) % 3);
		if (zoomPhase !== observerZoomPhase) {
			observerZoomPhase = zoomPhase;
			// Cycle focus agent
			const interesting = pickInterestingAgent(agentList);
			observerFocusId = interesting?.id ?? null;
		}

		const focusAgent = observerFocusId !== null ? $agents.get(observerFocusId) : null;
		if (focusAgent) {
			const ax = gridLeft + focusAgent.x * gridSize * cellSize;
			const ay = gridTop + focusAgent.y * gridSize * cellSize;

			// Soft spotlight circle
			const spotGrad = ctx.createRadialGradient(ax, ay, 0, ax, ay, 60);
			spotGrad.addColorStop(0, 'rgba(255, 255, 255, 0.08)');
			spotGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');
			ctx.fillStyle = spotGrad;
			ctx.beginPath();
			ctx.arc(ax, ay, 60, 0, Math.PI * 2);
			ctx.fill();

			// Narration text overlay
			const narration = getObserverNarration(focusAgent);
			ctx.save();
			ctx.font = '13px JetBrains Mono';
			ctx.textAlign = 'center';
			ctx.fillStyle = 'rgba(0, 255, 136, 0.7)';
			ctx.fillText(narration, width / 2, height - 80);
			ctx.restore();
		}

		// "OBSERVER MODE" badge top-right
		ctx.save();
		ctx.font = '10px JetBrains Mono';
		ctx.textAlign = 'right';
		ctx.fillStyle = 'rgba(0, 255, 136, 0.4)';
		ctx.fillText('◉ OBSERVER MODE [O to exit]', width - 20, 30);
		ctx.restore();

		// News ticker at bottom
		const feed = $eventsFeed;
		if (feed.length > 0) {
			const tickerY = height - 25;
			ctx.save();
			ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
			ctx.fillRect(0, tickerY - 12, width, 24);

			ctx.font = '11px JetBrains Mono';
			ctx.fillStyle = 'rgba(0, 255, 136, 0.65)';
			ctx.textAlign = 'left';

			// Build ticker string from recent events
			const recentEvents = feed.slice(-20);
			const tickerStr = recentEvents
				.map((e) => `[T${e.tick}] ${e.text}`)
				.join('   ●   ');

			// Scroll animation
			observerTickerOffset -= 0.8;
			const textWidth = ctx.measureText(tickerStr).width;
			if (observerTickerOffset < -textWidth) observerTickerOffset = width;
			ctx.fillText(tickerStr, observerTickerOffset, tickerY);
			ctx.restore();
		}
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

		// Observer mode idle check
		if (observerModeEnabled && !observerModeActive) {
			if (Date.now() - observerLastInput >= OBSERVER_IDLE_MS) {
				observerModeActive = true;
				observerTickerOffset = width;
			}
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

		// ── Phase 7C: Artifact terrain (render under agents) ──
		drawArtifactTerrain(ctx);

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

		// ── Faction territory borders overlay (toggle with F) ──
		if ($overlays.has('faction_borders')) {
			drawFactionBorders(ctx, agentList);
		}

		// ── Lucid dreamer beams for *living* agents (ghosts handled below) ──
		// Rendered during the dream cycle only. Keeps the beam tied to the
		// actual agent's current position rather than a stale ghost record.
		const ds = $dreamState;
		const lucidIds = new Set<number>(ds.lucid_agent_ids || []);
		if (ds.is_dreaming && lucidIds.size > 0) {
			for (const id of lucidIds) {
				const a = $agents.get(id);
				if (!a) continue;
				const lx = gridLeft + a.x * gridSize * cellSize;
				const ly = gridTop + a.y * gridSize * cellSize;
				drawLucidBeam(ctx, lx, ly);
			}
		}

		// ── Ghost manifestations (dream cycle only) ──
		// Dead agents only appear here — they are NOT leaked into the normal
		// agent loop above, so non-dream rendering stays clean.
		if (ds.is_dreaming && ds.ghosts && ds.ghosts.length > 0) {
			updateAndDrawGhosts(ctx, ds.ghosts, lucidIds);
		} else if (ghostClientState.size > 0) {
			// Drop any stale drift/mote/thread state when the dream ends
			ghostClientState.clear();
		}

		// ── Archon overlay (toggle with 'G') ──
		if (showArchonOverlay) {
			drawArchonOverlay(ctx);
		} else if (archonShatterAnims.size > 0) {
			// Keep any mid-flight shatter animation visible across toggles
			updateAndDrawShatterAnims(ctx);
		}

		// ── Cycle-reset artifact glow ── (self-gated by store state)
		drawCycleResetGlow(ctx);

		// ── Phase 7C: Nested simulation windows ──
		drawNestedSimWindows(ctx);

		// ── Phase 7C: Soul trap / reincarnation visuals ──
		drawReincarnationVisuals(ctx, agentList);

		// ── Phase 7C: Observer mode overlay (rendered on top of everything) ──
		drawObserverOverlay(ctx, agentList);

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
		// Exit observer mode on any input
		if (observerModeActive) observerModeActive = false;
		observerLastInput = Date.now();

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
		// Exit observer mode on any input
		if (observerModeActive) observerModeActive = false;
		observerLastInput = Date.now();

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
