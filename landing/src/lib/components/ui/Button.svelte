<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		variant?: 'primary' | 'secondary' | 'ghost';
		size?: 'sm' | 'md' | 'lg';
		href?: string;
		disabled?: boolean;
		fullWidth?: boolean;
		onclick?: (e: MouseEvent) => void;
		children?: Snippet;
		type?: 'button' | 'submit';
	}

	let {
		variant = 'secondary',
		size = 'md',
		href,
		disabled = false,
		fullWidth = false,
		onclick,
		children,
		type = 'button'
	}: Props = $props();
</script>

{#if href}
	<a
		{href}
		class="btn variant-{variant} size-{size}"
		class:full={fullWidth}
		class:disabled
		aria-disabled={disabled}
	>
		{#if children}{@render children()}{/if}
	</a>
{:else}
	<button
		{type}
		{disabled}
		{onclick}
		class="btn variant-{variant} size-{size}"
		class:full={fullWidth}
	>
		{#if children}{@render children()}{/if}
	</button>
{/if}

<style>
	.btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: var(--dl-s-2);
		font-family: var(--dl-font-ui);
		font-weight: 600;
		letter-spacing: -0.005em;
		border-radius: var(--dl-r-md);
		border: 1px solid transparent;
		text-decoration: none;
		cursor: pointer;
		transition: background var(--dl-dur-hover) var(--dl-ease),
			border-color var(--dl-dur-hover) var(--dl-ease),
			color var(--dl-dur-hover) var(--dl-ease),
			transform 80ms var(--dl-ease);
		white-space: nowrap;
		user-select: none;
	}
	.btn:active { transform: scale(0.98); }
	.btn:focus-visible {
		outline: 2px solid var(--dl-focus);
		outline-offset: var(--dl-focus-offset);
	}

	.size-sm { padding: 5px 10px; font-size: 12px; }
	.size-md { padding: 8px 14px; font-size: 13px; }
	.size-lg { padding: 11px 18px; font-size: 14px; }

	.variant-primary {
		background: var(--dl-grad-heat);
		color: white;
	}
	.variant-primary:hover:not(:disabled):not(.disabled) { filter: brightness(1.08); }

	.variant-secondary {
		background: var(--dl-bg-overlay);
		border-color: var(--dl-line);
		color: var(--dl-ink);
	}
	.variant-secondary:hover:not(:disabled):not(.disabled) {
		background: var(--dl-bg-modal);
		border-color: var(--dl-line-strong);
	}

	.variant-ghost {
		background: transparent;
		color: var(--dl-ink-mute);
	}
	.variant-ghost:hover:not(:disabled):not(.disabled) {
		color: var(--dl-ink);
		background: var(--dl-bg-raised);
	}

	.full { width: 100%; }

	.btn:disabled, .btn.disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}
</style>
