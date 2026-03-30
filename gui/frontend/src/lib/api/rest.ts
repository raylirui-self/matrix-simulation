/** REST API client for the simulation backend. */

const BASE = 'http://localhost:8000';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
	const res = await fetch(`${BASE}${path}`, {
		headers: { 'Content-Type': 'application/json' },
		...options
	});
	if (!res.ok) {
		const err = await res.json().catch(() => ({ detail: res.statusText }));
		throw new Error(err.detail || res.statusText);
	}
	return res.json();
}

export const api = {
	// Simulation CRUD
	createSim: (era?: string, scenario?: string) =>
		request<any>('/api/sim', {
			method: 'POST',
			body: JSON.stringify({ era, scenario })
		}),

	getSim: (runId: string) => request<any>(`/api/sim/${runId}`),

	tick: (runId: string, count = 1) =>
		request<any>(`/api/sim/${runId}/tick`, {
			method: 'POST',
			body: JSON.stringify({ count })
		}),

	getState: (runId: string) => request<any>(`/api/sim/${runId}/state`),

	getHistory: (runId: string, offset = 0, limit = 500) =>
		request<any>(`/api/sim/${runId}/history?offset=${offset}&limit=${limit}`),

	updateConfig: (runId: string, overrides: Record<string, any>) =>
		request<any>(`/api/sim/${runId}/config`, {
			method: 'PUT',
			body: JSON.stringify(overrides)
		}),

	// Agents
	listAgents: (runId: string, params?: Record<string, any>) => {
		const qs = params ? '?' + new URLSearchParams(params as any).toString() : '';
		return request<any>(`/api/sim/${runId}/agents${qs}`);
	},

	getAgent: (runId: string, agentId: number) =>
		request<any>(`/api/sim/${runId}/agents/${agentId}`),

	// World
	getWorld: (runId: string) => request<any>(`/api/sim/${runId}/world`),

	getBonds: (runId: string, minStrength = 0.1, limit = 200) =>
		request<any>(
			`/api/sim/${runId}/world/bonds?min_strength=${minStrength}&limit=${limit}`
		),

	// God mode
	godAction: (runId: string, action: string, targetId?: number, params?: Record<string, any>) =>
		request<any>(`/api/sim/${runId}/god`, {
			method: 'POST',
			body: JSON.stringify({ action, target_id: targetId, params: params || {} })
		}),

	// Media / LLM
	generatePortrait: (runId: string, agentId: number) =>
		request<any>(`/api/sim/${runId}/media/portrait/${agentId}`, { method: 'POST' }),

	getPortraitUrl: (runId: string, agentId: number) =>
		`${BASE}/api/sim/${runId}/media/portrait/${agentId}/image`,

	generateLandscape: (runId: string) =>
		request<any>(`/api/sim/${runId}/media/landscape`, { method: 'POST' }),

	getLandscapeUrl: (runId: string, era: string) =>
		`${BASE}/api/sim/${runId}/media/landscape/image?era=${encodeURIComponent(era)}`,

	generateNarrative: (runId: string) =>
		request<any>(`/api/sim/${runId}/media/narrate`, { method: 'POST' }),

	generateMonologue: (runId: string, agentId: number) =>
		request<any>(`/api/sim/${runId}/media/monologue/${agentId}`, { method: 'POST' }),

	// Meta
	listRuns: () => request<any>('/api/runs'),
	listEras: () => request<any>('/api/config/eras'),
	listScenarios: () => request<any>('/api/config/scenarios'),
	health: () => request<any>('/api/health')
};
