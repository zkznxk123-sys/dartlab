<script lang="ts">
	import SiteSignalsStudio from '$lib/components/siteSignals/SiteSignalsStudio.svelte';
</script>

<svelte:head>
	<title>사이트 신호 · DartLab</title>
	<meta
		name="description"
		content="DartLab 공개 문서 사이트의 집계 관측 원칙. 페이지뷰, 체류 구간, CTA 클릭 같은 집계 신호와 수집 제외 항목을 공개한다."
	/>
	<link rel="canonical" href="https://eddmpython.github.io/dartlab/site-signals" />
	<meta property="og:type" content="website" />
	<meta property="og:title" content="사이트 신호 · DartLab" />
	<meta
		property="og:description"
		content="공개 문서 사이트의 사용성을 집계 신호로만 관측한다. 원시 IP, 세션 리플레이, 검색어 원문은 수집하지 않는다."
	/>
	<meta property="og:image" content="https://eddmpython.github.io/dartlab/og-image.png" />
	<meta name="twitter:card" content="summary_large_image" />
</svelte:head>

<SiteSignalsStudio />
