/** Core simulation state store. */
import { writable, derived } from 'svelte/store';
import type { AgentDelta, TickMessage, WSMessage } from '$lib/api/websocket';

// ── Agent type ──
export type Agent = {
	id: number;
	x: number;
	y: number;
	sex: string;
	age: number;
	phase: string;
	health: number;
	intelligence: number;
	generation: number;
	emotion: string;
	awareness: number;
	redpilled: boolean;
	is_anomaly: boolean;
	is_sentinel: boolean;
	is_exile: boolean;
	is_protagonist: boolean;
	protagonist_name: string | null;
	faction_id: number | null;
	wealth: number;
};

// ── Stores ──
export const runId = writable<string | null>(null);
export const tick = writable(0);
export const agents = writable<Map<number, Agent>>(new Map());
export const aliveCounts = writable<number[]>([]);
export const isRunning = writable(false);

// Matrix state
export const matrixState = writable({
	control_index: 1.0,
	total_awareness: 0.0,
	cycle_number: 1,
	anomaly_id: null as number | null,
	sentinels_deployed: 0,
	glitches_this_cycle: 0,
	ticks_since_reset: 0
});

// Stats
export const stats = writable({
	alive_count: 0,
	births: 0,
	deaths: 0,
	avg_intelligence: 0,
	avg_health: 0,
	avg_generation: 0,
	phase_counts: {} as Record<string, number>
});

// Events feed
export const events = writable<Array<{ tick: number; text: string; type: string }>>([]);

// Factions
export const factions = writable<any[]>([]);

// Economy
export const economyStats = writable<Record<string, any>>({});

// Emotion stats
export const emotionStats = writable<Record<string, any>>({});

// Breakthroughs
export const breakthroughs = writable<string[]>([]);

// Death causes (from tick stats)
export const deathCauses = writable<Record<string, number>>({});

// Age distribution (from tick stats, keyed like M_20s, F_10s)
export const ageDistribution = writable<Record<string, number>>({});

// Tech progress (tech_name -> 0.0-1.0 proximity)
export const techProgress = writable<Record<string, number>>({});

// Faction belief means (faction_id -> { individualism, tradition, system_trust, spirituality })
export const factionBeliefMeans = writable<Record<string, Record<string, number>>>({});

// Active wars
export type War = {
	faction_a_id: number;
	faction_b_id: number;
	started_at: number;
	casualties_a: number;
	casualties_b: number;
	intensity: number;
};
export const wars = writable<War[]>([]);

// Cinematic events — full-screen overlays for key moments
export type CinematicEvent = {
	type: string;
	title: string;
	subtitle: string;
	tick: number;
	agent_id?: number;
	cycle?: number;
	enforcer_count?: number;
};
export const cinematicEventQueue = writable<CinematicEvent[]>([]);

// Tick history for sparkline
export const tickHistory = writable<
	Array<{ tick: number; alive: number; intelligence: number; health: number }>
>([]);

// ── Derived ──
export const aliveAgents = derived(agents, ($agents) =>
	Array.from($agents.values())
);

export const protagonists = derived(agents, ($agents) =>
	Array.from($agents.values()).filter((a) => a.is_protagonist)
);

export const population = derived(agents, ($agents) => $agents.size);

// ── Actions ──
export function loadFullState(state: any) {
	const agentMap = new Map<number, Agent>();
	for (const a of state.agents || []) {
		agentMap.set(a.id, a);
	}
	agents.set(agentMap);
	tick.set(state.tick || 0);
	stats.set({
		alive_count: agentMap.size,
		births: state.total_born || 0,
		deaths: state.total_died || 0,
		avg_intelligence: state.summary?.avg_intelligence || 0,
		avg_health: state.summary?.avg_health || 0,
		avg_generation: state.summary?.avg_generation || 0,
		phase_counts: state.summary?.phases || {}
	});
	if (state.matrix) {
		matrixState.set(state.matrix);
	}
	if (state.factions) {
		factions.set(state.factions);
	}
	if (state.wars) {
		wars.set(state.wars);
	}
}

export function applyTickMessage(msg: TickMessage) {
	tick.set(msg.tick);
	stats.set(msg.stats);

	// Apply agent deltas
	agents.update(($agents) => {
		for (const delta of msg.agent_deltas) {
			if (delta.died) {
				$agents.delete(delta.id);
				continue;
			}
			if (delta.born) {
				$agents.set(delta.id, {
					id: delta.id,
					x: delta.x ?? 0.5,
					y: delta.y ?? 0.5,
					sex: delta.sex ?? 'M',
					age: 0,
					phase: delta.phase ?? 'infant',
					health: delta.health ?? 1.0,
					intelligence: delta.intelligence ?? 0,
					generation: 0,
					emotion: delta.emotion ?? 'happiness',
					awareness: delta.awareness ?? 0,
					redpilled: false,
					is_anomaly: false,
					is_sentinel: delta.is_sentinel ?? false,
					is_exile: false,
					is_protagonist: delta.is_protagonist ?? false,
					protagonist_name: null,
					faction_id: delta.faction_id ?? null,
					wealth: 0
				});
				continue;
			}
			// Update existing
			const existing = $agents.get(delta.id);
			if (existing) {
				if (delta.x !== undefined) existing.x = delta.x;
				if (delta.y !== undefined) existing.y = delta.y;
				if (delta.health !== undefined) existing.health = delta.health;
				if (delta.intelligence !== undefined) existing.intelligence = delta.intelligence;
				if (delta.phase !== undefined) existing.phase = delta.phase;
				if (delta.emotion !== undefined) existing.emotion = delta.emotion;
				if (delta.awareness !== undefined) existing.awareness = delta.awareness;
				if (delta.age !== undefined) existing.age = delta.age;
				if (delta.redpilled !== undefined) existing.redpilled = delta.redpilled;
				if (delta.is_anomaly !== undefined) existing.is_anomaly = delta.is_anomaly;
				if (delta.is_sentinel !== undefined) existing.is_sentinel = delta.is_sentinel;
				if (delta.is_protagonist !== undefined) existing.is_protagonist = delta.is_protagonist;
				if (delta.faction_id !== undefined) existing.faction_id = delta.faction_id;
			}
		}
		return $agents;
	});

	// Update matrix
	if (msg.matrix) {
		matrixState.update(($m) => ({ ...$m, ...msg.matrix }));
	}

	if (msg.emotions) {
		emotionStats.set(msg.emotions);
	}
	if (msg.economy) {
		economyStats.set(msg.economy);
	}

	// Track breakthroughs
	if (msg.breakthroughs?.length) {
		breakthroughs.update(($b) => [...$b, ...msg.breakthroughs]);
	}

	// Death causes
	const incomingDeathCauses = (msg as any).death_causes || (msg.stats as any).death_causes;
	if (incomingDeathCauses) {
		deathCauses.update(($dc) => {
			for (const [cause, count] of Object.entries(incomingDeathCauses as Record<string, number>)) {
				$dc[cause] = ($dc[cause] || 0) + count;
			}
			return { ...$dc };
		});
	}

	// Age distribution (snapshot from current tick)
	if ((msg as any).age_distribution) {
		ageDistribution.set((msg as any).age_distribution);
	}

	// Tech progress (snapshot from current tick)
	if ((msg as any).tech_progress) {
		techProgress.set((msg as any).tech_progress);
	}

	// Faction belief means
	if ((msg as any).belief_stats?.faction_belief_means) {
		factionBeliefMeans.set((msg as any).belief_stats.faction_belief_means);
	}

	// Wars
	if ((msg as any).wars) {
		wars.set((msg as any).wars);
	}

	// Add to history
	tickHistory.update(($h) => {
		$h.push({
			tick: msg.tick,
			alive: msg.stats.alive_count,
			intelligence: msg.stats.avg_intelligence,
			health: msg.stats.avg_health
		});
		// Keep last 500 entries
		if ($h.length > 500) $h = $h.slice(-500);
		return $h;
	});

	// Generate feed events
	const newEvents: Array<{ tick: number; text: string; type: string }> = [];
	if (msg.stats.births > 0) {
		newEvents.push({
			tick: msg.tick,
			text: `${msg.stats.births} born (pop: ${msg.stats.alive_count})`,
			type: 'birth'
		});
	}
	if (msg.stats.deaths > 0) {
		newEvents.push({
			tick: msg.tick,
			text: `${msg.stats.deaths} died (pop: ${msg.stats.alive_count})`,
			type: 'death'
		});
	}
	for (const bt of msg.breakthroughs) {
		newEvents.push({ tick: msg.tick, text: `BREAKTHROUGH: ${bt}`, type: 'tech' });
	}
	if (msg.matrix?.glitches > 0) {
		newEvents.push({ tick: msg.tick, text: 'GLITCH detected in the Matrix...', type: 'matrix' });
	}
	if (msg.matrix?.anomaly_active) {
		newEvents.push({ tick: msg.tick, text: 'THE ANOMALY walks among us', type: 'matrix' });
	}
	if (newEvents.length) {
		events.update(($e) => {
			$e.push(...newEvents);
			if ($e.length > 10000) $e = $e.slice(-10000);
			return $e;
		});
	}

	// Cinematic events
	if ((msg as any).cinematic_events?.length) {
		cinematicEventQueue.update(($q) => [...$q, ...(msg as any).cinematic_events]);
	}
}
