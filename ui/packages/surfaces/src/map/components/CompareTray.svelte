<script lang="ts">
	interface Props {
		// [{ node: {id, label, industryName, color, ...}, detail?: any }]
		items: any[];
		maxItems?: number;
		onRemove?: (stockCode: string) => void;
		onClear?: () => void;
		onOpenFull?: () => void;
	}

	let { items, maxItems = 4, onRemove, onClear, onOpenFull }: Props = $props();
</script>

{#if items.length > 0}
	<div class="tray">
		<div class="tray-left">
			<span class="tray-label">비교 ({items.length}/{maxItems})</span>
		</div>
		<div class="chips">
			{#each items as item (item.node?.id)}
				<span class="chip">
					<span class="chip-dot" style:background={item.node?.color || '#64748b'}></span>
					<span class="chip-name" title={item.node?.label}>{item.node?.label || '-'}</span>
					<button class="chip-x" onclick={() => onRemove?.(item.node?.id)} aria-label="제거">✕</button>
				</span>
			{/each}
			{#each Array(maxItems - items.length) as _, i}
				<span class="chip placeholder">+ 슬롯 {items.length + i + 1}</span>
			{/each}
		</div>
		<div class="tray-actions">
			<button class="act-ghost" onclick={() => onClear?.()}>모두 지우기</button>
			<button class="act-primary" disabled={items.length < 2} onclick={() => onOpenFull?.()}>
				비교 열기 ({items.length}사) →
			</button>
		</div>
	</div>
{/if}

<style>
	.tray {
		position: fixed;
		bottom: 12px;
		left: 50%;
		transform: translateX(-50%);
		display: flex;
		align-items: center;
		gap: 16px;
		padding: 10px 14px;
		background: rgba(15, 18, 25, 0.95);
		border: 1px solid #334155;
		border-radius: 12px;
		box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5);
		backdrop-filter: blur(10px);
		z-index: 50;
		max-width: calc(100vw - 24px);
	}
	.tray-label {
		font-size: 11px;
		color: #94a3b8;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		font-weight: 600;
		white-space: nowrap;
	}
	.chips {
		display: flex;
		gap: 6px;
		align-items: center;
	}
	.chip {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 4px 8px 4px 6px;
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 6px;
		font-size: 12px;
		color: #f1f5f9;
		max-width: 140px;
	}
	.chip.placeholder {
		color: #475569;
		background: transparent;
		border-style: dashed;
	}
	.chip-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.chip-name {
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.chip-x {
		background: none;
		border: none;
		color: #64748b;
		cursor: pointer;
		font-size: 11px;
		padding: 0 2px;
	}
	.chip-x:hover {
		color: #f87171;
	}
	.tray-actions {
		display: flex;
		gap: 6px;
	}
	.act-ghost,
	.act-primary {
		padding: 6px 12px;
		font-size: 12px;
		border-radius: 6px;
		cursor: pointer;
	}
	.act-ghost {
		background: transparent;
		border: 1px solid #334155;
		color: #94a3b8;
	}
	.act-ghost:hover {
		color: #f1f5f9;
		background: #1e2433;
	}
	.act-primary {
		background: #60a5fa;
		color: #050811;
		font-weight: 600;
		border: 1px solid #60a5fa;
	}
	.act-primary:hover:not(:disabled) {
		background: #93c5fd;
	}
	.act-primary:disabled {
		background: #1e2433;
		color: #475569;
		border-color: #1e2433;
		cursor: not-allowed;
	}

	@media (max-width: 900px) {
		.tray {
			flex-wrap: wrap;
			padding: 8px 10px;
			gap: 8px;
		}
		.chip {
			max-width: 100px;
			font-size: 11px;
		}
	}
</style>
