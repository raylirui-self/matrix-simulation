<script lang="ts">
	interface Scenario {
		name: string;
		description: string;
		preview: string;
		highlights: string[];
	}

	let {
		scenarios,
		selected = $bindable(''),
		oncreate
	}: {
		scenarios: Scenario[];
		selected: string;
		oncreate: () => void;
	} = $props();

	function select(name: string) {
		selected = selected === name ? '' : name;
	}

	const icons: Record<string, string> = {
		awakening: '\u{1F441}',
		warworld: '\u{2694}',
		dark_ages: '\u{1F56F}',
		prophet_era: '\u{2728}',
		harsh_world: '\u{1F480}',
		peaceful: '\u{1F54A}',
	};
</script>

<div class="scenario-cards">
	{#each scenarios as s}
		<button
			class="card"
			class:selected={selected === s.name}
			onclick={() => select(s.name)}
		>
			<div class="card-header">
				<span class="card-icon">{icons[s.name] || '\u{1F3AE}'}</span>
				<span class="card-name">{s.name.replace(/_/g, ' ')}</span>
			</div>
			<p class="card-desc">{s.description}</p>
			{#if s.highlights?.length}
				<div class="card-highlights">
					{#each s.highlights as h}
						<span class="highlight">{h}</span>
					{/each}
				</div>
			{/if}
			{#if s.preview && selected === s.name}
				<p class="card-preview">{s.preview}</p>
			{/if}
		</button>
	{/each}
</div>

{#if selected}
	<button class="btn-launch" onclick={oncreate}>
		ENTER THE MATRIX
	</button>
{/if}

<style>
	.scenario-cards {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
		gap: 10px;
		margin-bottom: 12px;
	}

	.card {
		text-align: left;
		padding: 14px;
		background: var(--bg-secondary);
		border: 1px solid var(--green-dim);
		color: var(--green-primary);
		font-family: var(--font-mono);
		cursor: pointer;
		transition: all 0.15s ease;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.card:hover {
		border-color: var(--green-muted);
		background: rgba(0, 255, 136, 0.03);
	}
	.card.selected {
		border-color: var(--green-primary);
		background: var(--green-dim);
		box-shadow: 0 0 12px rgba(0, 255, 136, 0.15);
	}

	.card-header {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.card-icon {
		font-size: 18px;
	}
	.card-name {
		font-size: 12px;
		font-weight: 500;
		letter-spacing: 1.5px;
		text-transform: uppercase;
	}

	.card-desc {
		font-size: 11px;
		color: var(--text-dim);
		line-height: 1.4;
		margin: 0;
	}

	.card-highlights {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
	}
	.highlight {
		font-size: 9px;
		padding: 2px 6px;
		background: rgba(0, 255, 136, 0.08);
		border: 1px solid rgba(0, 255, 136, 0.15);
		color: var(--green-primary);
		letter-spacing: 0.5px;
	}

	.card-preview {
		font-size: 10px;
		color: var(--cyan);
		font-style: italic;
		margin: 0;
		padding-top: 4px;
		border-top: 1px solid rgba(0, 255, 136, 0.1);
	}

	.btn-launch {
		width: 100%;
		padding: 12px;
		background: var(--green-dim);
		border: 1px solid var(--green-primary);
		color: var(--green-primary);
		font-family: var(--font-mono);
		font-size: 13px;
		letter-spacing: 2px;
		cursor: pointer;
		transition: all 0.15s ease;
	}
	.btn-launch:hover {
		background: var(--green-primary);
		color: var(--bg-primary);
	}

	@media (max-width: 768px) {
		.scenario-cards {
			grid-template-columns: 1fr;
		}
	}
</style>
