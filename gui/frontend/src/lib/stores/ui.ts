/** UI state store — zoom level, panels, overlays. */
import { writable, derived } from 'svelte/store';

// Zoom levels: 0=CodeRain, 1=Grid, 2=Cell, 3=Soul
export const zoomLevel = writable(1);
export const zoomTransitioning = writable(false);

// Target cell for Level 2 (row, col)
export const focusCell = writable<{ row: number; col: number } | null>(null);

// Target agent for Level 3
export const focusAgentId = writable<number | null>(null);

// Edge panel visibility (proximity-based in practice, but can be pinned)
export const panelPinned = writable({
	left: false,
	right: false,
	top: false,
	bottom: false
});

// Data overlays (number key toggles at Level 1)
export const overlays = writable<Set<string>>(new Set());

// Terminal open state
export const terminalOpen = writable(false);

// Bond constellation mode
export const bondConstellationMode = writable(false);

// Easter egg: White Rabbit animation trigger
export const whiteRabbitActive = writable(false);

// Auto-run speed (ms between ticks)
export const autoSpeed = writable(200);

// Show parameter tuner
export const showParameterTuner = writable(false);

// Phase 7B panel/overlay toggles
export const havenPipOpen = writable(false);
export const causalTimelineOpen = writable(false);

// Phase 7D cinematic mode — when true, hide persistent chrome.
// Canvas fills the viewport; only a minimal tick counter stays visible.
// Edge panels still reveal on hover; cinematic events still show.
// Toggle hotkey: `c` (mnemonic: Cinematic).
export const cinematicMode = writable(true);

// Mouse position for edge panel proximity detection
export const mousePosition = writable({ x: 0, y: 0 });

// Raw proximity detection (instant)
const edgeProximity = derived(
	[mousePosition, panelPinned, zoomLevel],
	([$mouse, $pinned, $zoom]) => {
		if ($zoom !== 1) return { left: false, right: false, top: false, bottom: false };

		const threshold = 80; // pixels from edge (increased for easier access)
		const w = typeof window !== 'undefined' ? window.innerWidth : 1920;
		const h = typeof window !== 'undefined' ? window.innerHeight : 1080;

		return {
			left: $pinned.left || $mouse.x < threshold,
			right: $pinned.right || $mouse.x > w - threshold,
			top: $pinned.top || $mouse.y < threshold,
			bottom: $pinned.bottom || $mouse.y > h - threshold
		};
	}
);

// Debounced panel visibility: show instantly, hide after 400ms delay
function createDebouncedVisibility() {
	const store = writable({ left: false, right: false, top: false, bottom: false });
	const timers: Record<string, ReturnType<typeof setTimeout>> = {};

	const unsubProximity = edgeProximity.subscribe(($prox) => {
		for (const side of ['left', 'right', 'top', 'bottom'] as const) {
			if ($prox[side]) {
				// Show instantly
				clearTimeout(timers[side]);
				store.update((v) => ({ ...v, [side]: true }));
			} else {
				// Hide after delay
				clearTimeout(timers[side]);
				timers[side] = setTimeout(() => {
					store.update((v) => ({ ...v, [side]: false }));
				}, 400);
			}
		}
	});

	return {
		subscribe: store.subscribe,
		destroy() {
			unsubProximity();
			for (const key in timers) clearTimeout(timers[key]);
		}
	};
}

export const edgePanelVisibility = createDebouncedVisibility();

// Overlay toggle
export function toggleOverlay(name: string) {
	overlays.update(($o) => {
		if ($o.has(name)) {
			$o.delete(name);
		} else {
			$o.add(name);
		}
		return new Set($o);
	});
}
