<!--
  AmbientLandscape.svelte — dim era landscape behind the Code Rain (zoom 0).
  ~20% opacity so the rain stays primary; fades out on other zoom levels.
  Gracefully degrades to a solid dark background when the image 404s.
-->
<script lang="ts">
	import { api } from '$lib/api/rest';
	import { runId } from '$lib/stores/simulation';
	import { currentEra } from '$lib/stores/era';
	import { zoomLevel } from '$lib/stores/ui';

	let imgLoadFailed = $state(false);
	let lastSlug: string | null = null;

	let imgUrl = $derived.by(() => {
		const rid = $runId;
		const slug = $currentEra.slug;
		if (slug !== lastSlug) {
			lastSlug = slug;
			imgLoadFailed = false;
		}
		return rid ? api.getLandscapeUrl(rid, slug) : null;
	});

	let visible = $derived($zoomLevel === 0);

	function onImgError() {
		imgLoadFailed = true;
	}
</script>

<div class="ambient" class:visible aria-hidden="true">
	{#if imgUrl && !imgLoadFailed}
		<img class="bg" src={imgUrl} alt="" onerror={onImgError} />
	{:else}
		<div class="bg fallback"></div>
	{/if}
</div>

<style>
	.ambient {
		position: fixed;
		inset: 0;
		z-index: -1;
		opacity: 0;
		pointer-events: none;
		transition: opacity 1s ease;
		overflow: hidden;
	}
	.ambient.visible {
		opacity: 0.2;
	}
	.bg {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		object-fit: cover;
		filter: blur(1.5px) brightness(0.7) saturate(0.8);
	}
	.bg.fallback {
		background: #020602;
	}
</style>
