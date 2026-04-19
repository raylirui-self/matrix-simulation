<!--
  CinematicOverlay.svelte — Full-screen overlay for key cinematic moments.
  Triggered by cinematic_event types: anomaly_emergence, cycle_reset, enforcer_swarm.
  Auto-dismisses after a few seconds, or on click.
-->
<script lang="ts">
	import { onDestroy } from 'svelte';
	import {
		cinematicEventQueue,
		triggerCycleResetAnimation,
		type CinematicEvent
	} from '$lib/stores/simulation';

	let currentEvent = $state<CinematicEvent | null>(null);
	let visible = $state(false);
	let fadeClass = $state('');
	let cycleResetStage = $state<'idle' | 'pause' | 'whiteout' | 'hold' | 'fadeback'>('idle');
	let timer: ReturnType<typeof setTimeout> | null = null;

	import {
		CINEMATIC_DISPLAY_MS as DISPLAY_MS,
		CINEMATIC_FADE_MS as FADE_MS,
		CYCLE_RESET_STAGES
	} from '$lib/constants/cinematic';

	// Cycle-reset timings (ms): pause → expanding whiteout → hold → fade-back → done
	const RESET_PAUSE = CYCLE_RESET_STAGES.PAUSE_MS;
	const RESET_WHITEOUT = CYCLE_RESET_STAGES.WHITEOUT_MS;
	const RESET_HOLD = CYCLE_RESET_STAGES.HOLD_MS;
	const RESET_FADEBACK = CYCLE_RESET_STAGES.FADEBACK_MS;

	const unsub = cinematicEventQueue.subscribe(($q) => {
		if ($q.length > 0 && !currentEvent) {
			showNext();
		}
	});

	function showNext() {
		cinematicEventQueue.update(($q) => {
			if ($q.length === 0) return $q;
			currentEvent = $q[0];
			return $q.slice(1);
		});
		if (!currentEvent) return;
		if (currentEvent.type === 'cycle_reset') {
			startCycleReset();
			return;
		}
		fadeClass = 'fade-in';
		visible = true;
		timer = setTimeout(() => dismiss(), DISPLAY_MS);
	}

	function startCycleReset() {
		triggerCycleResetAnimation(currentEvent?.cycle ?? 0);
		visible = true;
		fadeClass = 'fade-in';
		cycleResetStage = 'pause';
		timer = setTimeout(() => {
			cycleResetStage = 'whiteout';
			timer = setTimeout(() => {
				cycleResetStage = 'hold';
				timer = setTimeout(() => {
					cycleResetStage = 'fadeback';
					timer = setTimeout(() => {
						cycleResetStage = 'idle';
						dismiss();
					}, RESET_FADEBACK);
				}, RESET_HOLD);
			}, RESET_WHITEOUT);
		}, RESET_PAUSE);
	}

	function dismiss() {
		if (timer) clearTimeout(timer);
		timer = null;
		fadeClass = 'fade-out';
		setTimeout(() => {
			visible = false;
			currentEvent = null;
			fadeClass = '';
			cycleResetStage = 'idle';
			// Check if more events queued
			cinematicEventQueue.update(($q) => {
				if ($q.length > 0) {
					setTimeout(showNext, 300);
				}
				return $q;
			});
		}, FADE_MS);
	}

	onDestroy(() => {
		unsub();
		if (timer) clearTimeout(timer);
	});

	function typeColor(type: string): string {
		switch (type) {
			case 'anomaly_emergence':
				return '#00ff41';
			case 'cycle_reset':
				return '#ff4444';
			case 'enforcer_swarm':
				return '#ff8800';
			default:
				return '#00ff41';
		}
	}
</script>

{#if visible && currentEvent}
	{#if currentEvent.type === 'cycle_reset'}
		<!-- Cycle reset: multi-stage dramatic sequence.
		     A radial whiteout grows from center, text appears mid-sequence,
		     then the whiteout fades away revealing the new cycle. -->
		<button
			type="button"
			class="cinematic-overlay reset-overlay stage-{cycleResetStage}"
			onclick={dismiss}
			aria-label="Dismiss cycle reset cinematic"
		>
			<div class="reset-whiteout"></div>
			<div class="reset-content">
				<div class="reset-label">CYCLE</div>
				<div class="reset-number">{currentEvent.cycle ?? '—'}</div>
				<div class="reset-label">ENDED</div>
			</div>
		</button>
	{:else}
		<button
			type="button"
			class="cinematic-overlay {fadeClass}"
			onclick={dismiss}
			aria-label="Dismiss cinematic"
		>
			<div class="scan-line"></div>
			<div class="content" style="--accent: {typeColor(currentEvent.type)}">
				<div class="glitch-text title">{currentEvent.title}</div>
				<div class="subtitle">{currentEvent.subtitle}</div>
				<div class="tick-stamp">TICK {currentEvent.tick}</div>
			</div>
		</button>
	{/if}
{/if}

<style>
	.cinematic-overlay {
		position: fixed;
		inset: 0;
		z-index: 9999;
		display: flex;
		align-items: center;
		justify-content: center;
		background: rgba(0, 0, 0, 0.85);
		cursor: pointer;
		pointer-events: all;
		border: none;
		padding: 0;
		font: inherit;
		color: inherit;
		width: 100%;
		height: 100%;
	}

	.cinematic-overlay.fade-in {
		animation: fadeIn 0.6s ease-out forwards;
	}

	.cinematic-overlay.fade-out {
		animation: fadeOut 0.6s ease-in forwards;
	}

	.scan-line {
		position: absolute;
		inset: 0;
		background: repeating-linear-gradient(
			0deg,
			transparent,
			transparent 2px,
			rgba(0, 255, 65, 0.03) 2px,
			rgba(0, 255, 65, 0.03) 4px
		);
		pointer-events: none;
	}

	.content {
		text-align: center;
		z-index: 1;
	}

	.title {
		font-family: 'Courier New', monospace;
		font-size: clamp(2rem, 6vw, 4.5rem);
		font-weight: 900;
		color: var(--accent);
		text-shadow:
			0 0 20px var(--accent),
			0 0 60px var(--accent);
		letter-spacing: 0.15em;
		margin-bottom: 0.5rem;
		animation: glitch 0.3s ease-in-out 0.6s 2;
	}

	.subtitle {
		font-family: 'Courier New', monospace;
		font-size: clamp(0.9rem, 2vw, 1.4rem);
		color: rgba(255, 255, 255, 0.7);
		letter-spacing: 0.08em;
		margin-bottom: 1.5rem;
	}

	.tick-stamp {
		font-family: 'Courier New', monospace;
		font-size: 0.75rem;
		color: rgba(255, 255, 255, 0.3);
		letter-spacing: 0.2em;
	}

	/* ── Cycle reset cinematic ── */
	.reset-overlay {
		background: transparent;
		overflow: hidden;
	}
	.reset-whiteout {
		position: absolute;
		left: 50%;
		top: 50%;
		width: 10px;
		height: 10px;
		border-radius: 50%;
		background: radial-gradient(
			circle,
			rgba(255, 255, 255, 0.98) 0%,
			rgba(255, 255, 255, 0.92) 55%,
			rgba(255, 255, 255, 0.0) 100%
		);
		transform: translate(-50%, -50%) scale(0);
		pointer-events: none;
		will-change: transform, opacity;
	}
	.reset-content {
		position: relative;
		z-index: 2;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.4rem;
		opacity: 0;
		transform: scale(0.92);
		font-family: 'Courier New', monospace;
		color: #222;
		text-align: center;
	}
	.reset-label {
		font-size: clamp(1.2rem, 3vw, 2.2rem);
		letter-spacing: 0.6em;
		font-weight: 600;
		color: rgba(20, 20, 30, 0.85);
	}
	.reset-number {
		font-size: clamp(4rem, 12vw, 10rem);
		font-weight: 900;
		line-height: 1;
		color: #0a0a14;
		text-shadow: 0 0 30px rgba(255, 255, 255, 0.8);
		letter-spacing: 0.1em;
	}

	.stage-pause .reset-whiteout {
		transform: translate(-50%, -50%) scale(0);
		opacity: 0;
	}
	.stage-whiteout .reset-whiteout {
		transform: translate(-50%, -50%) scale(400);
		opacity: 1;
		transition: transform 0.9s cubic-bezier(0.3, 0.1, 0.2, 1), opacity 0.3s ease;
	}
	.stage-hold .reset-whiteout {
		transform: translate(-50%, -50%) scale(400);
		opacity: 1;
	}
	.stage-hold .reset-content {
		opacity: 1;
		transform: scale(1);
		transition: opacity 0.4s ease, transform 0.6s cubic-bezier(0.2, 1, 0.3, 1);
	}
	.stage-fadeback .reset-whiteout {
		transform: translate(-50%, -50%) scale(400);
		opacity: 0;
		transition: opacity 1.05s ease;
	}
	.stage-fadeback .reset-content {
		opacity: 0;
		transition: opacity 0.9s ease;
	}

	@keyframes fadeIn {
		from { opacity: 0; }
		to { opacity: 1; }
	}

	@keyframes fadeOut {
		from { opacity: 1; }
		to { opacity: 0; }
	}

	@keyframes glitch {
		0% { transform: translate(0); }
		25% { transform: translate(-3px, 2px); }
		50% { transform: translate(3px, -1px); }
		75% { transform: translate(-1px, -2px); }
		100% { transform: translate(0); }
	}
</style>
