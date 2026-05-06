<script lang="ts">
	import { base } from '$app/paths';
	import { Badge } from '$lib/components/ui/badge';
	import { Card } from '$lib/components/ui/card';

	const tiers = [
		{
			tier: 'Stable',
			badge: 'success' as const,
			color: 'border-dl-success/30',
			items: [
				'Company facade',
				'DART sections / show / trace / diff',
				'DART docs / finance / report',
				'search / listing',
				'BS · IS · CF · ratios · timeseries'
			]
		},
		{
			tier: 'Beta',
			badge: 'accent' as const,
			color: 'border-dl-accent/30',
			items: [
				'EDGAR Company (sections · finance)',
				'insights (7 영역 등급)',
				'rank / sector',
				'Excel export',
				'Server API (FastAPI 40+ 엔드포인트)',
				'MCP 서버 (60 도구)'
			]
		},
		{
			tier: 'Experimental',
			badge: 'warning' as const,
			color: 'border-dl-warning/30',
			items: [
				'AI 분석 (7 provider)',
				'AI GUI (Desktop)',
				'네트워크 스캐너 (신규)'
			]
		}
	];

	const roadmap = [
		{ quarter: '지금', label: 'v0.6', items: ['sections 텍스트 구조', 'EDGAR sections 100%', '네트워크 스캐너'] },
		{ quarter: '다음', label: 'v0.7', items: ['profile.sections 머지 뷰', 'TopicView 구현', 'show() 완성'] },
		{ quarter: '이후', label: 'v0.8+', items: ['EDINET 엔진', 'AI GUI 개선', 'Rust 파이프라인 (sections)'] }
	];
</script>

<section class="py-24 px-6 bg-dl-bg-darker/50">
	<div class="max-w-5xl mx-auto">
		<div class="text-center mb-12">
			<span class="text-xs font-semibold uppercase tracking-widest text-dl-primary mb-3 block">안정성 & 로드맵</span>
			<h2 class="text-3xl md:text-4xl font-bold text-dl-text mb-3">투명한 안정성 등급</h2>
			<p class="text-dl-text-muted text-lg">무엇이 안정이고 무엇이 실험인지 명확히</p>
		</div>

		<!-- Stability Tiers -->
		<div class="grid md:grid-cols-3 gap-5 mb-16">
			{#each tiers as t}
				<Card hover={false} class="{t.color}">
					<div class="mb-4">
						<Badge variant={t.badge}>{t.tier}</Badge>
					</div>
					<ul class="space-y-2">
						{#each t.items as item}
							<li class="flex items-center gap-2 text-sm text-dl-text-muted">
								<span class="w-1 h-1 rounded-full {t.badge === 'success' ? 'bg-dl-success' : t.badge === 'accent' ? 'bg-dl-accent' : 'bg-dl-warning'}"></span>
								{item}
							</li>
						{/each}
					</ul>
				</Card>
			{/each}
		</div>

		<!-- 로드맵 -->
		<div class="text-center mb-8">
			<h3 class="text-xl font-bold text-dl-text">로드맵</h3>
		</div>

		<div class="grid md:grid-cols-3 gap-4">
			{#each roadmap as phase, i}
				<div class="relative">
					{#if i < roadmap.length - 1}
						<div class="hidden md:block absolute top-6 -right-2 w-4 h-px bg-dl-border z-10"></div>
						<div class="hidden md:block absolute top-[22px] right-[-4px] w-0 h-0 border-t-[3px] border-t-transparent border-b-[3px] border-b-transparent border-l-[5px] border-l-dl-border z-10"></div>
					{/if}

					<div class="rounded-lg border border-dl-border bg-dl-bg-card/50 p-5 {i === 0 ? 'border-dl-primary/20' : ''}">
						<div class="flex items-center gap-2 mb-3">
							<span class="text-xs font-bold uppercase tracking-wider {i === 0 ? 'text-dl-primary' : 'text-dl-text-dim'}">{phase.quarter}</span>
							<span class="text-xs font-mono text-dl-text-dim">{phase.label}</span>
						</div>
						<ul class="space-y-1.5">
							{#each phase.items as item}
								<li class="text-sm text-dl-text-muted flex items-center gap-2">
									<span class="w-1 h-1 rounded-full {i === 0 ? 'bg-dl-primary' : 'bg-dl-text-dim/40'}"></span>
									{item}
								</li>
							{/each}
						</ul>
					</div>
				</div>
			{/each}
		</div>

		<div class="mt-6 text-center">
			<a href="{base}/skills/operation.stability" class="text-xs text-dl-text-dim hover:text-dl-text transition-colors no-underline">
				안정성 문서 전체 →
			</a>
		</div>
	</div>
</section>
