<script lang="ts">
	import { Copy, X } from 'lucide-svelte';

	/** TableView 의 row 클릭 시 raw JSON view 모달. */
	interface Props {
		row: Record<string, unknown> | null;
		onClose: () => void;
	}

	let { row, onClose }: Props = $props();

	function formatValue(v: unknown): string {
		if (v === null || v === undefined) return 'null';
		if (Array.isArray(v)) {
			if (v.length === 0) return '[]';
			if (v.length > 20) return `[${v.length} items]\n${JSON.stringify(v.slice(0, 20), null, 2)}\n…`;
			return JSON.stringify(v, null, 2);
		}
		if (typeof v === 'object') return JSON.stringify(v, null, 2);
		return String(v);
	}

	function copyJson() {
		if (!row) return;
		const text = JSON.stringify(row, null, 2);
		void navigator.clipboard.writeText(text);
	}

	function handleKey(e: KeyboardEvent) {
		if (e.key === 'Escape') onClose();
	}

	function backdropClick(e: MouseEvent) {
		if (e.target === e.currentTarget) onClose();
	}
</script>

<svelte:window onkeydown={handleKey} />

{#if row}
	<div
		class="rj-backdrop"
		role="dialog"
		aria-modal="true"
		aria-label="Row JSON view"
		onclick={backdropClick}
		onkeydown={handleKey}
		tabindex="-1"
	>
		<div class="rj-modal" role="document">
			<header class="rj-head">
				<span class="rj-title">Row 상세</span>
				<div class="rj-actions">
					<button type="button" class="rj-btn" onclick={copyJson}>
						<Copy size={11} />
						<span>JSON 복사</span>
					</button>
					<button type="button" class="rj-close" onclick={onClose} aria-label="닫기 (Esc)">
						<X size={14} />
					</button>
				</div>
			</header>
			<div class="rj-body">
				<table>
					<tbody>
						{#each Object.entries(row) as [key, value] (key)}
							<tr>
								<th>{key}</th>
								<td><pre>{formatValue(value)}</pre></td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	</div>
{/if}

<style>
	.rj-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.7);
		backdrop-filter: blur(4px);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1500;
		padding: 40px;
	}
	.rj-modal {
		width: min(720px, 90vw);
		max-height: 80vh;
		display: flex;
		flex-direction: column;
		background: #0f172a;
		border: 1px solid #334155;
		border-radius: 8px;
		box-shadow: 0 24px 48px -12px rgba(0, 0, 0, 0.7);
		overflow: hidden;
	}
	.rj-head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 12px 16px;
		border-bottom: 1px solid #1e2433;
	}
	.rj-title {
		font-size: 13px;
		font-weight: 600;
		color: #f1f5f9;
	}
	.rj-actions {
		display: flex;
		gap: 6px;
		align-items: center;
	}
	.rj-btn {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		padding: 5px 10px;
		font-size: 11px;
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 3px;
		color: #cbd5e1;
		cursor: pointer;
		font-family: inherit;
	}
	.rj-btn:hover {
		border-color: var(--amber);
		color: var(--amber);
	}
	.rj-close {
		background: transparent;
		border: none;
		color: #64748b;
		cursor: pointer;
		font-size: 14px;
		padding: 4px 6px;
	}
	.rj-close:hover {
		color: var(--amber);
	}
	.rj-body {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		padding: 4px 0;
	}
	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 11px;
		font-variant-numeric: tabular-nums;
	}
	th {
		text-align: left;
		padding: 6px 16px;
		color: #94a3b8;
		font-weight: 500;
		font-family: monospace;
		font-size: 11px;
		vertical-align: top;
		min-width: 140px;
		border-bottom: 1px solid rgba(30, 36, 51, 0.5);
		background: #0a0e18;
	}
	td {
		padding: 6px 16px;
		color: #cbd5e1;
		font-family: 'JetBrains Mono', monospace;
		border-bottom: 1px solid rgba(30, 36, 51, 0.5);
		word-break: break-word;
	}
	pre {
		margin: 0;
		white-space: pre-wrap;
		font-family: inherit;
	}
</style>
