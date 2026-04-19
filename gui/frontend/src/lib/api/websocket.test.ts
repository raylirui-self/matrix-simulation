/**
 * Tests for [websocket.ts](./websocket.ts) — H-4 (type safety) + M-4 (backoff).
 *
 * Uses a minimal WebSocket stand-in so the reconnect scheduling can be
 * exercised without touching a real server. Fake timers drive the
 * exponential-backoff calendar.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

import type { RawMessage, WSMessage } from './websocket';

// ── Minimal WebSocket stub ───────────────────────────────────────────────────
class StubSocket {
	static instances: StubSocket[] = [];
	readyState = 0; // CONNECTING
	onopen?: () => void;
	onclose?: () => void;
	onerror?: (e: unknown) => void;
	onmessage?: (e: { data: string }) => void;
	url: string;
	closed = false;

	constructor(url: string) {
		this.url = url;
		StubSocket.instances.push(this);
	}

	// Test helpers
	openIt() {
		this.readyState = 1; // OPEN
		this.onopen?.();
	}
	closeIt() {
		this.readyState = 3; // CLOSED
		this.onclose?.();
	}
	close() {
		this.closed = true;
		this.closeIt();
	}
	send(_: string) {}
	static readonly OPEN = 1;
}

describe('SimWebSocket — M-4 reconnect backoff', () => {
	let SimWebSocket: typeof import('./websocket').SimWebSocket;

	beforeEach(async () => {
		vi.useFakeTimers();
		StubSocket.instances = [];
		(globalThis as unknown as { WebSocket: typeof StubSocket }).WebSocket = StubSocket;
		const mod = await import('./websocket');
		SimWebSocket = mod.SimWebSocket;
	});

	afterEach(() => {
		vi.useRealTimers();
		vi.resetModules();
	});

	it('resets reconnect attempts on successful connection', async () => {
		const ws = new SimWebSocket('r1');
		const p = ws.connect();
		StubSocket.instances[0].openIt();
		await p;
		expect(ws.reconnectState.attempts).toBe(0);
	});

	it('schedules backoff after unintended close', async () => {
		const ws = new SimWebSocket('r2');
		const p = ws.connect();
		StubSocket.instances[0].openIt();
		await p;

		// Simulate backend going down
		StubSocket.instances[0].closeIt();
		expect(ws.reconnectState.attempts).toBe(1);
	});

	it('does not reconnect after explicit disconnect()', async () => {
		const ws = new SimWebSocket('r3');
		const p = ws.connect();
		StubSocket.instances[0].openIt();
		await p;
		ws.disconnect();

		// Advance enough time that a reconnect would have fired
		vi.advanceTimersByTime(60_000);
		expect(StubSocket.instances.length).toBe(1);
	});

	it('emits "giving_up" after MAX_RETRIES', async () => {
		const ws = new SimWebSocket('r4');
		const statusEvents: string[] = [];
		ws.onStatus((s) => statusEvents.push(s));

		// First connect succeeds then immediately fails; every subsequent
		// reconnect attempt also fails. After MAX_RETRIES (20) we give up.
		const p = ws.connect();
		StubSocket.instances[0].openIt();
		await p;

		for (let i = 0; i < 25; i++) {
			StubSocket.instances.at(-1)!.closeIt();
			// Let the scheduled reconnect fire its next connect()
			vi.advanceTimersByTime(RECONNECT_CEILING_MS);
		}

		expect(statusEvents).toContain('giving_up');
		expect(ws.reconnectState.givenUp).toBe(true);
	});
});

// Maximum base delay the backoff can reach (30s) + jitter — advance timers
// by a generous margin so each scheduled reconnect fires reliably.
const RECONNECT_CEILING_MS = 40_000;

describe('WSMessage type safety — H-4', () => {
	it('narrows on msg.type: tick', () => {
		const msg: WSMessage = {
			type: 'tick',
			tick: 5,
			stats: {
				alive_count: 10,
				births: 1,
				deaths: 0,
				avg_intelligence: 0.5,
				avg_health: 0.8,
				avg_generation: 2,
				phase_counts: {}
			},
			agent_deltas: [],
			bonds: { formed: 0, decayed: 0 },
			breakthroughs: [],
			matrix: {},
			emotions: {},
			economy: {},
			conflict: {}
		};
		if (msg.type === 'tick') {
			expect(msg.stats.alive_count).toBe(10);
		} else {
			// Unreachable — but this branch proves the narrowing works.
			expect.fail();
		}
	});

	it('narrows on msg.type: error', () => {
		const msg: WSMessage = { type: 'error', code: 'invalid_json', detail: 'garbage' };
		if (msg.type === 'error') {
			expect(msg.code).toBe('invalid_json');
			expect(msg.detail).toBe('garbage');
		}
	});

	it('unknown message types are handled via RawMessage at the boundary', () => {
		// WSMessage is strict — unknown shapes must be typed as RawMessage.
		const msg: RawMessage = { type: 'surprise', anything: 123 };
		expect(msg.type).toBe('surprise');
		expect(msg.anything).toBe(123);
	});
});
