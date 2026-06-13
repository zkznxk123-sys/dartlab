<script lang="ts">
	// 진입 즉시 +page.ts 가 /terminal/005930 로 redirect 한다 — 본 화면은 redirect 직전 잠깐만 보인다.
	// (옛 개발용 라우트 목록 메뉴 폐기 — 로컬 UI 첫 화면은 절차 없이 곧장 터미널.)
</script>

<div class="boot">터미널 여는 중 …</div>

<style>
	.boot {
		height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--dl-bg-base, #0f0f10);
		color: var(--dl-ink-mute, #6b7280);
		font-family: var(--dl-font-mono, ui-monospace, monospace);
		font-size: 12px;
	}
</style>
