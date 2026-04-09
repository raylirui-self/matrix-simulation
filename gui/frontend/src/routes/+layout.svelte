<script lang="ts">
	import '../app.css';

	let { children } = $props();
</script>

<svelte:head>
	<title>The Nexus — Cognitive Matrix Simulator</title>
	<meta name="description" content="Matrix civilization simulator" />
</svelte:head>

{@render children()}
