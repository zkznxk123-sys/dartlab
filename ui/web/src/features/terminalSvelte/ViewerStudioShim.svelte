<script lang="ts">
	let { code = '', onclose }: { code?: string; onclose?: () => void } = $props();
</script>

<div class="shim">
	<div>
		<p class="k">LOCAL VIEWER</p>
		<p class="t">{code} 공시뷰어는 로컬 viewer 라우트 iframe으로 열립니다.</p>
		<button type="button" onclick={() => onclose?.()}>닫기</button>
	</div>
</div>

<style>
	.shim {
		height: 100%;
		display: grid;
		place-items: center;
		background: #05070b;
		color: #e8eaef;
		font-family: ui-sans-serif, system-ui, sans-serif;
	}
	.k {
		margin: 0 0 8px;
		color: #fb923c;
		font: 700 11px/1 ui-monospace, SFMono-Regular, Menlo, monospace;
		letter-spacing: 0.14em;
	}
	.t {
		margin: 0 0 14px;
		color: #a3a8b3;
		font-size: 13px;
	}
	button {
		border: 1px solid rgba(255, 255, 255, 0.14);
		background: #16171a;
		color: #e8eaef;
		border-radius: 3px;
		padding: 6px 12px;
		cursor: pointer;
	}
</style>
