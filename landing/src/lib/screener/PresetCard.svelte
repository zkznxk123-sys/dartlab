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
	class="preset-card cat-{preset.category}"
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
		position: relative;
		transition:
			background 0.18s ease,
			border-color 0.18s ease,
			transform 0.15s ease,
			box-shadow 0.18s ease;
	}
	.preset-card::before {
		content: '';
		position: absolute;
		left: 0;
		top: 12px;
		bottom: 12px;
		width: 3px;
		border-radius: 2px;
		background: var(--cat-color, #60a5fa);
		opacity: 0.6;
		transition: opacity 0.18s ease;
	}
	.preset-card.cat-theme { --cat-color: #ea4647; }
	.preset-card.cat-price { --cat-color: #fb923c; }
	.preset-card.cat-verified { --cat-color: #a78bfa; }
	.preset-card:hover {
		background: #0b1120;
		border-color: #334155;
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35);
	}
	.preset-card:hover::before {
		opacity: 1;
	}
	.preset-card.active {
		background: linear-gradient(135deg, rgba(234, 70, 71, 0.12), rgba(251, 146, 60, 0.06));
		border-color: rgba(234, 70, 71, 0.55);
		box-shadow: 0 0 0 1px rgba(234, 70, 71, 0.35), 0 6px 16px rgba(234, 70, 71, 0.18);
	}
	.preset-card.active::before {
		opacity: 1;
		background: linear-gradient(180deg, #ea4647, #fb923c);
	}
	.title {
		font-size: 13px;
		font-weight: 700;
		color: #f1f5f9;
		letter-spacing: -0.01em;
		padding-left: 8px;
	}
	.subtitle {
		font-size: 10px;
		color: var(--cat-color, #60a5fa);
		font-family: monospace;
		letter-spacing: 0.02em;
		padding-left: 8px;
	}
	.preset-card.active .subtitle {
		color: #fb923c;
	}
	.desc {
		font-size: 11px;
		color: #64748b;
		line-height: 1.5;
		padding-left: 8px;
	}
	.preset-card.active .desc {
		color: #94a3b8;
	}
</style>
