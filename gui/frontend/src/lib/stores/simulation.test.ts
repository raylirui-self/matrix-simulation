/**
 * Smoke tests for [simulation.ts](./simulation.ts).
 *
 * Establishes the first frontend test baseline called out in L-7 /
 * H-4 / M-4 of [docs/code_review.md](../../../../../docs/code_review.md).
 *
 * Pure store-logic tests — no Svelte component rendering, so this file
 * runs under vitest + jsdom without needing svelte-testing-library to
 * support component mounting in Svelte 5 / SvelteKit mode. Add DOM
 * rendering tests in a follow-up once the ecosystem settles.
 */
import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest';
import { get } from 'svelte/store';

import {
	runId,
	tick,
	agents,
	aliveCounts,
	isRunning,
	matrixState,
	cycleResetAnimation,
	triggerCycleResetAnimation,
	stats,
	factions,
	events,
	nestedSims,
	havenSummary
} from './simulation';

describe('simulation store — initial values', () => {
	it('runId starts null', () => {
		expect(get(runId)).toBeNull();
	});

	it('tick starts at 0', () => {
		expect(get(tick)).toBe(0);
	});

	it('agents starts as an empty Map', () => {
		const m = get(agents);
		expect(m).toBeInstanceOf(Map);
		expect(m.size).toBe(0);
	});

	it('isRunning starts false', () => {
		expect(get(isRunning)).toBe(false);
	});

	it('matrixState carries demiurge + archons defaults', () => {
		const ms = get(matrixState);
		expect(ms.control_index).toBe(1.0);
		expect(ms.cycle_number).toBe(1);
		expect(ms.demiurge).toMatchObject({ fear: 0.1, pride: 0.5, confusion: 0.0 });
		expect(Array.isArray(ms.archons)).toBe(true);
	});

	it('nestedSims starts with count 0', () => {
		expect(get(nestedSims).count).toBe(0);
	});

	it('havenSummary starts null', () => {
		expect(get(havenSummary)).toBeNull();
	});
});

describe('simulation store — mutation', () => {
	beforeEach(() => {
		runId.set(null);
		tick.set(0);
		agents.set(new Map());
		aliveCounts.set([]);
		isRunning.set(false);
		stats.set({
			alive_count: 0,
			births: 0,
			deaths: 0,
			avg_intelligence: 0,
			avg_health: 0,
			avg_generation: 0,
			phase_counts: {}
		});
		factions.set([]);
		events.set([]);
	});

	it('tick increments via update', () => {
		tick.set(5);
		tick.update((t) => t + 1);
		expect(get(tick)).toBe(6);
	});

	it('agents Map accepts inserts and is read back', () => {
		const next = new Map(get(agents));
		next.set(42, {
			id: 42,
			x: 0.1,
			y: 0.2,
			sex: 'F',
			age: 30,
			phase: 'adult',
			health: 0.8,
			intelligence: 0.5,
			generation: 2,
			emotion: 'hope',
			awareness: 0.1,
			redpilled: false,
			is_anomaly: false,
			is_sentinel: false,
			is_exile: false,
			is_protagonist: false,
			protagonist_name: null,
			faction_id: null,
			wealth: 1.0,
			consciousness_phase: 'bicameral',
			free_will_index: 0.3,
			incarnation_count: 0,
			soul_trap_broken: false,
			past_life_memories: 0,
			is_enforcer: false,
			is_broker: false,
			is_guardian: false,
			is_locksmith: false,
			teleport_keys: 0,
			pleroma_glimpses: 0,
			location: 'simulation'
		});
		agents.set(next);
		expect(get(agents).size).toBe(1);
		expect(get(agents).get(42)?.phase).toBe('adult');
	});

	it('events store appends in order', () => {
		events.update((arr) => [...arr, { tick: 1, text: 'first', type: 'birth' }]);
		events.update((arr) => [...arr, { tick: 2, text: 'second', type: 'death' }]);
		const list = get(events);
		expect(list).toHaveLength(2);
		expect(list[0].tick).toBe(1);
		expect(list[1].tick).toBe(2);
	});
});

describe('triggerCycleResetAnimation', () => {
	// Pins L-2 (hardcoded 4700ms) + L-4 (Date.now vs performance.now)
	// behavior. When the fix for either lands, update this test to
	// read from the new shared constant / time source.

	beforeEach(() => {
		vi.useFakeTimers();
		cycleResetAnimation.set({ active: false, started_at: 0, cycle: 0 });
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it('sets active=true immediately and records the cycle', () => {
		triggerCycleResetAnimation(7);
		const s = get(cycleResetAnimation);
		expect(s.active).toBe(true);
		expect(s.cycle).toBe(7);
		expect(s.started_at).toBeGreaterThan(0);
	});

	it('turns active=false after the 4700ms timeout fires', () => {
		triggerCycleResetAnimation(1);
		expect(get(cycleResetAnimation).active).toBe(true);

		vi.advanceTimersByTime(4700);
		expect(get(cycleResetAnimation).active).toBe(false);
	});

	it('does not prematurely turn off before the timer fires', () => {
		triggerCycleResetAnimation(2);
		vi.advanceTimersByTime(4699);
		expect(get(cycleResetAnimation).active).toBe(true);
	});
});
