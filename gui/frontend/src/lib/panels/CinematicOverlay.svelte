<!--
  CinematicOverlay.svelte — Full-screen overlay for key cinematic moments.
  Triggered by cinematic_event types: anomaly_emergence, cycle_reset, enforcer_swarm.
  Auto-dismisses after a few seconds, or on click.
-->
<script lang="ts">
	import { onDestroy } from 'svelte';
	import { cinematicEventQueue, type CinematicEvent } from '$lib/stores/simulation';

	let currentEvent: CinematicEvent | null = null;
	let visible = false;
	let fadeClass = '';
	let timer: ReturnType<typeof setTimeout> | null = null;

	const DISPLAY_MS = 4000;
	const FADE_MS = 600;

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
		fadeClass = 'fade-in';
		visible = true;
		timer = setTimeout(() => dismiss(), DISPLAY_MS);
	}

	function dismiss() {
		if (timer) clearTimeout(timer);
		timer = null;
		fadeClass = 'fade-out';
		setTimeout(() => {
			visible = false;
			currentEvent = null;
			fadeClass = '';
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
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div class="cinematic-overlay {fadeClass}" on:click={dismiss}>
		<div class="scan-line"></div>
		<div class="content" style="--accent: {typeColor(currentEvent.type)}">
			<div class="glitch-text title">{currentEvent.title}</div>
			<div class="subtitle">{currentEvent.subtitle}</div>
			<div class="tick-stamp">TICK {currentEvent.tick}</div>
		</div>
	</div>
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

	@keyframes fadeIn {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	@keyframes fadeOut {
		from {
			opacity: 1;
		}
		to {
			opacity: 0;
		}
	}

	@keyframes glitch {
		0% {
			transform: translate(0);
		}
		25% {
			transform: translate(-3px, 2px);
		}
		50% {
			transform: translate(3px, -1px);
		}
		75% {
			transform: translate(-1px, -2px);
		}
		100% {
			transform: translate(0);
		}
	}
</style>
