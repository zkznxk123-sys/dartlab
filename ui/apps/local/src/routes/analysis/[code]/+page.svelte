<script lang="ts">
	// /analysis/[code] 는 +page.ts load 에서 /terminal/[code] 로 redirect 한다 — 이 컴포넌트는 정상 흐름에서
	// 렌더되지 않는다(redirect 가 렌더 이전에 발생). 만일의 경우를 위한 최소 fallback.
</script>

<p class="redir">터미널로 이동 중…</p>

<style>
	.redir {
		height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--dl-ink-mute, #6b7280);
		font-family: var(--dl-font-mono, ui-monospace, monospace);
		font-size: 12px;
	}
</style>
