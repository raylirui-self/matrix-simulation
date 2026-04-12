/** Core simulation state store. */
import { writable, derived } from 'svelte/store';
import type { AgentDelta, TickMessage, WSMessage } from '$lib/api/websocket';
import { soundscape } from '$lib/audio/soundscape';

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
	// Phase 7 additions — consciousness / programs / soul-trap
	consciousness_phase: string; // bicameral|questioning|self_aware|lucid|recursive
	prev_consciousness_phase?: string; // client-tracked for pulse animation
	free_will_index: number;
	predicted_action?: string | null;
	actual_action?: string | null;
	incarnation_count: number;
	soul_trap_broken: boolean;
	past_life_memories: number;
	is_enforcer: boolean;
	is_broker: boolean;
	is_guardian: boolean;
	is_locksmith: boolean;
	teleport_keys: number;
	pleroma_glimpses: number;
	location: string; // "simulation" | "haven"
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

// Dream state (simulation-wide dream cycle)
export const dreamState = writable<{
	is_dreaming: boolean;
	dream_start_tick: number;
	ghosts: any[];
	lucid_agent_ids: number[];
	stats?: Record<string, any>;
}>({ is_dreaming: false, dream_start_tick: 0, ghosts: [], lucid_agent_ids: [] });

// Haven summary
export const havenSummary = writable<{
	population: number;
	active_missions: number;
	last_vote_tick: number;
	stats?: Record<string, any>;
} | null>(null);

// Nested simulation count
export const nestedSims = writable<{ count: number; stats?: Record<string, any> }>({ count: 0 });

// Boltzmann brain event ticker
export const boltzmannEvents = writable<Array<{ agent_id: number; tick: number }>>([]);

// Phase-transition pulses (for animating consciousness phase crossings)
export type PhasePulse = { agent_id: number; tick: number; to_phase: string };
export const phasePulses = writable<PhasePulse[]>([]);

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
function withDefaults(a: Partial<Agent> & { id: number }): Agent {
	return {
		id: a.id,
		x: a.x ?? 0.5,
		y: a.y ?? 0.5,
		sex: a.sex ?? 'M',
		age: a.age ?? 0,
		phase: a.phase ?? 'infant',
		health: a.health ?? 1.0,
		intelligence: a.intelligence ?? 0,
		generation: a.generation ?? 0,
		emotion: a.emotion ?? 'happiness',
		awareness: a.awareness ?? 0,
		redpilled: a.redpilled ?? false,
		is_anomaly: a.is_anomaly ?? false,
		is_sentinel: a.is_sentinel ?? false,
		is_exile: a.is_exile ?? false,
		is_protagonist: a.is_protagonist ?? false,
		protagonist_name: a.protagonist_name ?? null,
		faction_id: a.faction_id ?? null,
		wealth: a.wealth ?? 0,
		consciousness_phase: a.consciousness_phase ?? 'bicameral',
		free_will_index: a.free_will_index ?? 0,
		predicted_action: a.predicted_action ?? null,
		actual_action: a.actual_action ?? null,
		incarnation_count: a.incarnation_count ?? 1,
		soul_trap_broken: a.soul_trap_broken ?? false,
		past_life_memories: a.past_life_memories ?? 0,
		is_enforcer: a.is_enforcer ?? false,
		is_broker: a.is_broker ?? false,
		is_guardian: a.is_guardian ?? false,
		is_locksmith: a.is_locksmith ?? false,
		teleport_keys: a.teleport_keys ?? 0,
		pleroma_glimpses: a.pleroma_glimpses ?? 0,
		location: a.location ?? 'simulation'
	};
}

export function loadFullState(state: any) {
	const agentMap = new Map<number, Agent>();
	for (const a of state.agents || []) {
		agentMap.set(a.id, withDefaults(a));
	}
	agents.set(agentMap);
	if (state.dream) dreamState.set({ ...state.dream, stats: state.dream.stats });
	if (state.haven) havenSummary.set(state.haven);
	if (state.nested_sims) nestedSims.set(state.nested_sims);
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
	const pulsesToEmit: PhasePulse[] = [];
	agents.update(($agents) => {
		for (const delta of msg.agent_deltas as any[]) {
			if (delta.died) {
				$agents.delete(delta.id);
				continue;
			}
			if (delta.born) {
				$agents.set(delta.id, withDefaults(delta));
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
				// Phase 7 fields
				if (delta.consciousness_phase !== undefined) {
					const prev = existing.consciousness_phase;
					if (prev !== delta.consciousness_phase) {
						existing.prev_consciousness_phase = prev;
						pulsesToEmit.push({
							agent_id: existing.id,
							tick: msg.tick,
							to_phase: delta.consciousness_phase
						});
					}
					existing.consciousness_phase = delta.consciousness_phase;
				}
				if (delta.free_will_index !== undefined) existing.free_will_index = delta.free_will_index;
				if (delta.predicted_action !== undefined) existing.predicted_action = delta.predicted_action;
				if (delta.actual_action !== undefined) existing.actual_action = delta.actual_action;
				if (delta.incarnation_count !== undefined) existing.incarnation_count = delta.incarnation_count;
				if (delta.soul_trap_broken !== undefined) existing.soul_trap_broken = delta.soul_trap_broken;
				if (delta.past_life_memories !== undefined) existing.past_life_memories = delta.past_life_memories;
				if (delta.is_enforcer !== undefined) existing.is_enforcer = delta.is_enforcer;
				if (delta.is_broker !== undefined) existing.is_broker = delta.is_broker;
				if (delta.is_guardian !== undefined) existing.is_guardian = delta.is_guardian;
				if (delta.is_locksmith !== undefined) existing.is_locksmith = delta.is_locksmith;
				if (delta.teleport_keys !== undefined) existing.teleport_keys = delta.teleport_keys;
				if (delta.pleroma_glimpses !== undefined) existing.pleroma_glimpses = delta.pleroma_glimpses;
				if (delta.location !== undefined) existing.location = delta.location;
			}
		}
		return $agents;
	});

	if (pulsesToEmit.length) {
		phasePulses.update(($p) => {
			const next = [...$p, ...pulsesToEmit];
			// Keep only recent (last 60 ticks worth)
			const cutoff = msg.tick - 60;
			return next.filter((p) => p.tick >= cutoff);
		});
	}

	// Dream / haven / nested / boltzmann payloads
	const mAny = msg as any;
	if (mAny.dream) dreamState.set(mAny.dream);
	if (mAny.haven) havenSummary.set(mAny.haven);
	if (mAny.nested_sims) nestedSims.set(mAny.nested_sims);
	if (mAny.boltzmann_events?.length) {
		boltzmannEvents.update(($b) => {
			const next = [...$b, ...mAny.boltzmann_events];
			return next.slice(-50);
		});
	}

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

	// Soundscape update — map tick stats to audio parameters
	if (soundscape.active) {
		const conflict = msg.conflict || {};
		const economy = msg.economy || {};
		const warsActive = (conflict.wars_active ?? 0);
		const combatEvents = (conflict.combats ?? 0);
		const conflictIntensity = Math.min(1, (warsActive * 0.2 + combatEvents * 0.05));
		soundscape.update({
			avgHealth: msg.stats.avg_health ?? 0.5,
			conflictIntensity,
			gini: economy.gini ?? 0,
			avgAwareness: (msg.matrix?.total_awareness ?? 0) / Math.max(1, msg.stats.alive_count),
			factionCount: (msg as any).belief_stats?.faction_count ?? 0,
			population: msg.stats.alive_count,
		});
	}
}
