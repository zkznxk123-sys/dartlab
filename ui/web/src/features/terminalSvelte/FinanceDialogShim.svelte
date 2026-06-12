<script lang="ts">
	let {
		open = false,
		onclose,
	}: {
		code?: string;
		corpName?: string;
		open?: boolean;
		onclose?: () => void;
	} = $props();
</script>

{#if open}
	<div class="backdrop" role="presentation" onclick={() => onclose?.()}>
		<div
			class="panel"
			role="dialog"
			aria-modal="true"
			tabindex="-1"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.key === 'Escape' && onclose?.()}
		>
			<div class="bar">
				<span>재무제표</span>
				<button type="button" onclick={() => onclose?.()}>×</button>
			</div>
			<div class="body">로컬 터미널의 재무 패널에서 정량 재무제표를 확인하세요.</div>
		</div>
	</div>
{/if}

<style>
	.backdrop {
		position: fixed;
		inset: 0;
		z-index: 120;
		display: grid;
		place-items: center;
		background: rgba(0, 0, 0, 0.66);
	}
	.panel {
		width: min(420px, calc(100vw - 32px));
		border: 1px solid rgba(255, 255, 255, 0.12);
		background: #0f0f10;
		color: #e8eaef;
		border-radius: 4px;
		overflow: hidden;
	}
	.bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 9px 12px;
		border-bottom: 1px solid rgba(255, 255, 255, 0.1);
		font: 700 11px/1 ui-monospace, SFMono-Regular, Menlo, monospace;
		color: #fb923c;
	}
	button {
		border: 0;
		background: transparent;
		color: #a3a8b3;
		font-size: 18px;
		cursor: pointer;
	}
	.body {
		padding: 18px 12px;
		font: 13px/1.5 ui-sans-serif, system-ui, sans-serif;
		color: #a3a8b3;
	}
</style>
