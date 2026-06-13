<script lang="ts">
	// 디자인 토큰 SSOT — landing 과 동일 3종(@dartlab/ui-design). 터미널 surface 의 자급 terminal.css 가
	// 참조하는 --dl-* 커스텀 프로퍼티를 여기서 1회 주입한다. tailwind 불요(surface 는 시맨틱 클래스).
	import '@dartlab/ui-design/styles/v2-tokens.css';
	import '@dartlab/ui-design/styles/tokens.css';
	import '@dartlab/ui-design/styles/typography.css';

	let { children } = $props();
</script>

{@render children()}

<style>
	/* 공동배선 — landing 루트 +layout 의 글로벌 가드를 미러한다. 로컬 터미널이 GitHub Pages 와 동일하게
	   보이려면(가로 스크롤바 reflow 차단·한글 줄바꿈 동일·10px 다크 scrollbar) 이 reset 이 필수다.
	   없으면 로컬은 브라우저 기본 ~17px scrollbar + word-break 차이로 wrap 패널 높이가 어긋난다. */
	:global(html) {
		max-width: 100vw;
		overflow-x: clip;
		scrollbar-color: #334155 transparent;
		scrollbar-width: thin;
	}
	:global(body) {
		max-width: 100vw;
		overflow-x: clip;
		word-break: keep-all;
		overflow-wrap: anywhere;
	}
	:global(body > div) {
		max-width: 100vw;
	}
	:global(*::-webkit-scrollbar) {
		width: 10px;
		height: 10px;
	}
	:global(*::-webkit-scrollbar-track) {
		background: transparent;
	}
	:global(*::-webkit-scrollbar-thumb) {
		background: #334155;
		border-radius: 5px;
		border: 2px solid transparent;
		background-clip: padding-box;
	}
	:global(*::-webkit-scrollbar-thumb:hover) {
		background: #475569;
		background-clip: padding-box;
		border: 2px solid transparent;
	}
	:global(*::-webkit-scrollbar-corner) {
		background: transparent;
	}
</style>
