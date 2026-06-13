<script lang="ts">
	// 디자인 토큰 SSOT — landing 과 동일 3종(@dartlab/ui-design). 터미널 surface 의 자급 terminal.css 가
	// 참조하는 --dl-* 커스텀 프로퍼티를 여기서 1회 주입한다. tailwind 불요(surface 는 시맨틱 클래스).
	import '@dartlab/ui-design/styles/v2-tokens.css';
	import '@dartlab/ui-design/styles/tokens.css';
	import '@dartlab/ui-design/styles/typography.css';

	let { children } = $props();
</script>

{@render children()}
