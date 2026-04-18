<!--
  EraSplash.svelte — full-screen era transition cinematic.
  Fires whenever `currentEra` changes, showing the matching LLM-generated
  landscape with era name fading in/out for ~3.5 seconds.
  Works in both normal and cinematic mode.
-->
<script lang="ts">
	import { onDestroy } from 'svelte';
	import { api } from '$lib/api/rest';
	import { runId } from '$lib/stores/simulation';
	import { currentEra, type Era } from '$lib/stores/era';

	const DISPLAY_MS = 3500;

	let visible = $state(false);
	let splashEra = $state<Era | null>(null);
	let imgUrl = $state<string | null>(null);
	let imgLoadFailed = $state(false);
	let prevSlug: string | null = null;
	let first = true;
	let timer: ReturnType<typeof setTimeout> | null = null;

	function trigger(era: Era) {
		splashEra = era;
		imgLoadFailed = false;
		const rid = $runId;
		imgUrl = rid ? api.getLandscapeUrl(rid, era.slug) : null;
		visible = true;
		if (timer) clearTimeout(timer);
		timer = setTimeout(() => {
			visible = false;
		}, DISPLAY_MS);
	}

	// Watch for era changes — skip the first sync so we don't splash on app start.
	$effect(() => {
		const era = $currentEra;
		if (prevSlug === null) {
			prevSlug = era.slug;
			first = false;
			return;
		}
		if (era.slug !== prevSlug) {
			prevSlug = era.slug;
			if (!first) trigger(era);
		}
	});

	function onImgError() {
		// Graceful degrade: no image → solid dark splash with just the era name.
		imgLoadFailed = true;
	}

	onDestroy(() => {
		if (timer) clearTimeout(timer);
	});
</script>

{#if visible && splashEra}
	<div class="splash" style="--era-color: {splashEra.color};" aria-hidden="true">
		{#if imgUrl && !imgLoadFailed}
			<img
				class="landscape"
				src={imgUrl}
				alt=""
				onerror={onImgError}
			/>
		{:else}
			<div class="landscape fallback"></div>
		{/if}
		<div class="vignette"></div>
		<div class="text">
			<div class="era-name">{splashEra.name}</div>
			<div class="era-desc">{splashEra.desc}</div>
		</div>
	</div>
{/if}

<style>
	.splash {
		position: fixed;
		inset: 0;
		z-index: 9000;
		overflow: hidden;
		pointer-events: none;
		animation: splash-in-out 3.5s ease-in-out forwards;
	}
	.landscape {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		object-fit: cover;
		filter: brightness(0.8) contrast(1.05);
	}
	.landscape.fallback {
		background: radial-gradient(
			ellipse at center,
			color-mix(in srgb, var(--era-color) 25%, #030d03) 0%,
			#020602 80%
		);
	}
	.vignette {
		position: absolute;
		inset: 0;
		background:
			radial-gradient(ellipse at center, transparent 30%, rgba(0, 0, 0, 0.65) 85%),
			linear-gradient(180deg, rgba(0,0,0,0) 60%, rgba(0,0,0,0.6) 100%);
	}
	.text {
		position: absolute;
		left: 0;
		right: 0;
		top: 50%;
		transform: translateY(-50%);
		text-align: center;
		font-family: var(--font-mono, 'JetBrains Mono', monospace);
		animation: text-in-out 3.5s ease-in-out forwards;
	}
	.era-name {
		font-size: clamp(2.2rem, 6vw, 5rem);
		font-weight: 200;
		letter-spacing: 0.4em;
		color: var(--era-color);
		text-shadow:
			0 0 20px var(--era-color),
			0 0 60px color-mix(in srgb, var(--era-color) 40%, transparent);
		text-transform: uppercase;
	}
	.era-desc {
		margin-top: 1em;
		font-size: clamp(0.8rem, 1.5vw, 1.1rem);
		font-style: italic;
		color: rgba(255, 255, 255, 0.75);
		letter-spacing: 0.15em;
	}

	@keyframes splash-in-out {
		0%   { opacity: 0; }
		15%  { opacity: 1; }
		75%  { opacity: 1; }
		100% { opacity: 0; }
	}
	@keyframes text-in-out {
		0%   { opacity: 0; transform: translateY(-50%) scale(0.96); }
		18%  { opacity: 1; transform: translateY(-50%) scale(1); }
		72%  { opacity: 1; transform: translateY(-50%) scale(1); }
		100% { opacity: 0; transform: translateY(-50%) scale(1.02); }
	}
</style>
