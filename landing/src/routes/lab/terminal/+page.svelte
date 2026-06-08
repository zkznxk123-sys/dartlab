<script lang="ts">
	import { base } from '$app/paths';

	// 정적 아티팩트는 build 시 static/terminal → /terminal 로 복사.
	// base 접두로 GitHub Pages(/dartlab) 와 로컬(dev) 모두 정상 해소.
	const src = `${base}/terminal/index.html`;
</script>

<svelte:head>
	<title>dartlab · /lab/terminal — Bloomberg 스타일 터미널 (검증)</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<iframe class="terminal-frame" {src} title="DartLab Terminal" loading="eager"></iframe>

<style>
	/* lab-shell 의 패딩/배경을 넘어 풀뷰포트로 띄운다 — 터미널 자체가 100vh 레이아웃 */
	.terminal-frame {
		display: block;
		width: 100%;
		height: 100vh;
		border: 0;
		margin: 0;
		background: #050811;
	}
</style>
