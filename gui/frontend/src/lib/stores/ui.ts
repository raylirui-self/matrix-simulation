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

// Auto-run speed (ms between ticks)
export const autoSpeed = writable(200);

// Show parameter tuner
export const showParameterTuner = writable(false);

// Mouse position for edge panel proximity detection
export const mousePosition = writable({ x: 0, y: 0 });

// Derived: which edge panels should show based on mouse proximity
export const edgePanelVisibility = derived(
	[mousePosition, panelPinned, zoomLevel],
	([$mouse, $pinned, $zoom]) => {
		if ($zoom !== 1) return { left: false, right: false, top: false, bottom: false };

		const threshold = 60; // pixels from edge
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
