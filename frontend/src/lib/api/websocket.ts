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
	world_summary: Record<string, any>;
	protagonist_ids: number[];
};

export type WSMessage = TickMessage | StateSyncMessage | { type: string; [key: string]: any };

type MessageHandler = (msg: WSMessage) => void;

export class SimWebSocket {
	private ws: WebSocket | null = null;
	private runId: string;
	private handlers: Set<MessageHandler> = new Set();
	private reconnectTimer: number | null = null;

	constructor(runId: string) {
		this.runId = runId;
	}

	connect(): Promise<void> {
		return new Promise((resolve, reject) => {
			this.ws = new WebSocket(`${WS_BASE}/ws/sim/${this.runId}`);

			this.ws.onopen = () => resolve();

			this.ws.onmessage = (event) => {
				try {
					const msg: WSMessage = JSON.parse(event.data);
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
				// Auto-reconnect after 2 seconds
				this.reconnectTimer = window.setTimeout(() => {
					this.connect().catch(() => {});
				}, 2000);
			};
		});
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
		if (this.reconnectTimer) {
			clearTimeout(this.reconnectTimer);
		}
		this.ws?.close();
		this.ws = null;
		this.handlers.clear();
	}
}
