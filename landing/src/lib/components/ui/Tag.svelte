<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		tone?: 'neutral' | 'good' | 'warn' | 'bad' | 'info' | 'up' | 'down';
		filled?: boolean;
		children?: Snippet;
	}

	let { tone = 'neutral', filled = false, children }: Props = $props();
</script>

<span class="tag tone-{tone}" class:filled>
	{#if children}{@render children()}{/if}
</span>

<style>
	.tag {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 3px 9px;
		border: 1px solid var(--dl-line);
		border-radius: var(--dl-r-pill);
		background: transparent;
		color: var(--dl-ink-mute);
		font-family: var(--dl-font-ui);
		font-size: 11px;
		font-weight: 500;
		letter-spacing: 0.01em;
		line-height: 1.5;
		white-space: nowrap;
	}

	.tone-good { color: var(--dl-good); border-color: rgba(52, 211, 153, 0.32); }
	.tone-warn { color: var(--dl-warn); border-color: rgba(251, 191, 36, 0.32); }
	.tone-bad { color: var(--dl-bad); border-color: rgba(239, 68, 68, 0.32); }
	.tone-info { color: var(--dl-info); border-color: rgba(96, 165, 250, 0.32); }
	.tone-up { color: var(--dl-up); border-color: rgba(228, 63, 63, 0.32); }
	.tone-down { color: var(--dl-down); border-color: rgba(29, 100, 220, 0.32); }

	.filled.tone-good { background: rgba(52, 211, 153, 0.1); }
	.filled.tone-warn { background: rgba(251, 191, 36, 0.1); }
	.filled.tone-bad { background: rgba(239, 68, 68, 0.1); }
	.filled.tone-info { background: rgba(96, 165, 250, 0.1); }
	.filled.tone-up { background: var(--dl-up-soft); }
	.filled.tone-down { background: var(--dl-down-soft); }
	.filled.tone-neutral { background: rgba(255, 255, 255, 0.04); }
</style>
