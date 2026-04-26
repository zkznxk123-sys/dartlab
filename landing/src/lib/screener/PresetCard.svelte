<script lang="ts">
	import type { Preset } from './presets';

	interface Props {
		preset: Preset;
		active: boolean;
		onClick: (id: string) => void;
	}

	let { preset, active, onClick }: Props = $props();
</script>

<button
	type="button"
	class="preset-card"
	class:active
	onclick={() => onClick(preset.id)}
	title={preset.desc}
>
	<div class="title">{preset.title}</div>
	<div class="subtitle">{preset.subtitle}</div>
	<div class="desc">{preset.desc}</div>
</button>

<style>
	.preset-card {
		display: flex;
		flex-direction: column;
		gap: 4px;
		text-align: left;
		padding: 12px 14px;
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 8px;
		color: #cbd5e1;
		cursor: pointer;
		transition:
			background 0.15s,
			border-color 0.15s,
			transform 0.15s;
	}
	.preset-card:hover {
		background: #0b1120;
		border-color: #334155;
		transform: translateY(-1px);
	}
	.preset-card.active {
		background: rgba(96, 165, 250, 0.12);
		border-color: #60a5fa;
		box-shadow: 0 0 0 1px rgba(96, 165, 250, 0.4);
	}
	.title {
		font-size: 13px;
		font-weight: 700;
		color: #f1f5f9;
		letter-spacing: -0.01em;
	}
	.subtitle {
		font-size: 10px;
		color: #60a5fa;
		font-family: monospace;
		letter-spacing: 0.02em;
	}
	.preset-card.active .subtitle {
		color: #93c5fd;
	}
	.desc {
		font-size: 11px;
		color: #64748b;
		line-height: 1.5;
	}
</style>
