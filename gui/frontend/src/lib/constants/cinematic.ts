/**
 * Shared cinematic-mode timings.
 *
 * L-1 / L-4 in docs/code_review.md — these durations were previously
 * duplicated across simulation.ts and CinematicOverlay.svelte with
 * `Date.now()`-based comparisons. Centralizing them means a backend
 * cadence tweak only requires updating one constant.
 *
 * `monoNow()` returns a monotonic millisecond timestamp that's safe
 * against wall-clock jumps (NTP corrections, manual clock changes).
 * Prefer it over `Date.now()` for ALL relative-time comparisons.
 */

/** Cycle-reset whiteout cinematic — backend keeps the paused state this long. */
export const CYCLE_RESET_WHITEOUT_MS = 4500;

/** Safety window on the setTimeout callback — a hair longer than the backend cinematic. */
export const CYCLE_RESET_SAFETY_MS = 4700;

/** Default on-screen dwell for single-event cinematic cards. */
export const CINEMATIC_DISPLAY_MS = 4000;

/** Fade-in / fade-out duration for cinematic cards. */
export const CINEMATIC_FADE_MS = 600;

/** Staged cycle-reset cinematic: pause → whiteout → hold → fadeback. */
export const CYCLE_RESET_STAGES = {
	PAUSE_MS: 400,
	WHITEOUT_MS: 900,
	HOLD_MS: 1300,
	FADEBACK_MS: 1100
} as const;

/**
 * Monotonic clock in milliseconds. In a browser / jsdom context this
 * wraps `performance.now()`, which is immune to wall-clock jumps. Falls
 * back to `Date.now()` only if `performance` is somehow missing — which
 * would be an unusual environment.
 */
export function monoNow(): number {
	if (typeof performance !== 'undefined' && typeof performance.now === 'function') {
		return performance.now();
	}
	return Date.now();
}
