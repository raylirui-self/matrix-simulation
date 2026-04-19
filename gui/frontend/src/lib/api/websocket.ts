/** WebSocket connection manager for real-time tick streaming. */

const WS_BASE = 'ws://localhost:8000';

export type TickMessage = {
	type: 'tick';
	tick: number;
	stats: {
		alive_count: number;
		births: number;
		deaths: number;
		avg_intelligence: number;
		avg_health: number;
		avg_generation: number;
		phase_counts: Record<string, number>;
	};
	agent_deltas: AgentDelta[];
	bonds: { formed: number; decayed: number };
	breakthroughs: string[];
	matrix: Record<string, any>;
	emotions: Record<string, any>;
	economy: Record<string, any>;
	conflict: Record<string, any>;
};

export type AgentDelta = {
	id: number;
	x?: number;
	y?: number;
	health?: number;
	phase?: string;
	emotion?: string;
	awareness?: number;
	born?: boolean;
	died?: boolean;
	sex?: string;
	age?: number;
	intelligence?: number;
	is_protagonist?: boolean;
	redpilled?: boolean;
	is_anomaly?: boolean;
	is_sentinel?: boolean;
	faction_id?: number;
};

export type StateSyncMessage = {
	type: 'state_sync';
	tick: number;
	agents: any[];
	matrix: Record<string, any>;
	factions: any[];
	wars?: any[];
	world_summary: Record<string, any>;
	protagonist_ids: number[];
};

// H-4: Known message types are explicit union members so `msg.type === 'X'`
// narrows to the correct variant. Unknown message types are handled by
// consumers' `else` branches — they fall through without type safety on
// purpose (that's the shape of "a type we don't model yet").
export type ErrorMessage = { type: 'error'; code: string; detail?: string };
export type CycleResetMessage = { type: 'cycle_reset'; cycle: number; tick: number };
export type StoppedMessage = { type: 'stopped' };
export type AutoStartedMessage = { type: 'auto_started' };
export type ExtinctionMessage = { type: 'extinction' };
export type WSMessage =
	| TickMessage
	| StateSyncMessage
	| ErrorMessage
	| CycleResetMessage
	| StoppedMessage
	| AutoStartedMessage
	| ExtinctionMessage;
/** Unknown-type fallback — use at the handler boundary only, not in WSMessage. */
export type RawMessage = { type: string; [key: string]: unknown };

type MessageHandler = (msg: WSMessage) => void;
type ConnectionStatusHandler = (status: 'connected' | 'disconnected' | 'giving_up') => void;

// M-4: Exponential backoff with jitter. 1s → 2s → 4s → … capped at 30s.
// After MAX_RETRIES consecutive failures, give up and surface status to
// the UI so the user can trigger a manual reconnect.
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30_000;
const RECONNECT_MAX_RETRIES = 20;

export class SimWebSocket {
	private ws: WebSocket | null = null;
	private runId: string;
	private handlers: Set<MessageHandler> = new Set();
	private statusHandlers: Set<ConnectionStatusHandler> = new Set();
	private reconnectTimer: number | null = null;
	private reconnectAttempts = 0;
	private closedByCaller = false;

	constructor(runId: string) {
		this.runId = runId;
	}

	/** M-4: exposed for testing and UI wiring. */
	get reconnectState() {
		return { attempts: this.reconnectAttempts, givenUp: this.reconnectAttempts >= RECONNECT_MAX_RETRIES };
	}

	connect(): Promise<void> {
		return new Promise((resolve, reject) => {
			this.closedByCaller = false;
			this.ws = new WebSocket(`${WS_BASE}/ws/sim/${this.runId}`);

			this.ws.onopen = () => {
				this.reconnectAttempts = 0;
				this.emitStatus('connected');
				resolve();
			};

			this.ws.onmessage = (event) => {
				try {
					const msg = JSON.parse(event.data) as WSMessage;
					this.handlers.forEach((h) => h(msg));
				} catch (e) {
					console.error('WS parse error:', e);
				}
			};

			this.ws.onerror = (e) => {
				console.error('WS error:', e);
				reject(e);
			};

			this.ws.onclose = () => {
				this.emitStatus('disconnected');
				if (this.closedByCaller) return;
				this.scheduleReconnect();
			};
		});
	}

	private scheduleReconnect() {
		if (this.reconnectAttempts >= RECONNECT_MAX_RETRIES) {
			this.emitStatus('giving_up');
			return;
		}
		// Exponential backoff with ±20% jitter to avoid thundering-herd.
		const base = Math.min(RECONNECT_BASE_MS * 2 ** this.reconnectAttempts, RECONNECT_MAX_MS);
		const jitter = base * (0.8 + Math.random() * 0.4);
		this.reconnectAttempts += 1;
		this.reconnectTimer = window.setTimeout(() => {
			this.connect().catch(() => {
				/* next onclose will re-schedule */
			});
		}, jitter);
	}

	private emitStatus(status: 'connected' | 'disconnected' | 'giving_up') {
		this.statusHandlers.forEach((h) => h(status));
	}

	onStatus(handler: ConnectionStatusHandler) {
		this.statusHandlers.add(handler);
		return () => this.statusHandlers.delete(handler);
	}

	onMessage(handler: MessageHandler) {
		this.handlers.add(handler);
		return () => this.handlers.delete(handler);
	}

	send(command: string, params: Record<string, any> = {}) {
		if (this.ws?.readyState === WebSocket.OPEN) {
			this.ws.send(JSON.stringify({ command, ...params }));
		}
	}

	requestTick(count = 1) {
		this.send('tick', { count });
	}

	startAuto(speedMs = 200) {
		this.send('auto', { speed: speedMs });
	}

	stop() {
		this.send('stop');
	}

	requestState() {
		this.send('state');
	}

	disconnect() {
		this.closedByCaller = true;
		if (this.reconnectTimer) {
			clearTimeout(this.reconnectTimer);
			this.reconnectTimer = null;
		}
		this.ws?.close();
		this.ws = null;
		this.handlers.clear();
		this.statusHandlers.clear();
		this.reconnectAttempts = 0;
	}
}
