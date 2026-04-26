<script lang="ts">
	import { base } from '$app/paths';
	import { brand } from '$lib/brand';
	import { Button } from '$lib/components/ui/button';
	import { Download } from 'lucide-svelte';
</script>

<section class="relative pt-32 pb-20 px-6 overflow-hidden">
	<div
		class="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(234,70,71,0.06)_0%,_transparent_60%)]"
	></div>

	<div class="relative mx-auto max-w-4xl text-center">
		<div class="mb-6 flex justify-center">
			<picture>
				<source srcset="{base}/avatar.webp" type="image/webp" />
				<img
					src="{base}/avatar.png"
					alt="DartLab mascot"
					width="180"
					height="180"
					fetchpriority="high"
					class="drop-shadow-[0_0_32px_rgba(234,70,71,0.25)] animate-float"
				/>
			</picture>
		</div>

		<h1 class="text-5xl md:text-7xl font-extrabold tracking-tight leading-[1.1] mb-6 mt-4">
			<span class="text-dl-text">종목코드 하나 →</span><br />
			<span
				class="bg-gradient-to-r from-dl-primary via-dl-primary-light to-dl-primary bg-clip-text text-transparent"
				>기업의 전체 이야기</span
			>
		</h1>

		<p class="text-lg md:text-xl text-dl-text-muted max-w-2xl mx-auto mb-6 leading-relaxed">
			AI 가 dartlab 엔진을 직접 호출해 분석한다. 사람도 같은 엔진을 한 줄로 쓴다.<br />
			한국 DART + 미국 SEC EDGAR 공시, 미리 정리된 데이터.
		</p>

		<div class="mb-10 inline-flex items-center gap-2 px-5 py-3 rounded-lg bg-dl-bg-card/70 border border-dl-border/50 font-mono text-sm md:text-base text-dl-text">
			<span class="text-dl-text-dim">&gt;&gt;&gt;</span>
			<span class="text-dl-primary">dartlab</span><span class="text-dl-text-muted">.ask(</span><span class="text-dl-accent">"삼성전자 재무건전성 분석해줘"</span><span class="text-dl-text-muted">)</span>
		</div>

		<div class="flex flex-wrap items-center justify-center gap-4 mb-16">
			<Button href={brand.desktop} size="lg" class="text-base px-8 py-3">
				<Download class="w-4 h-4 inline mr-1" /> Windows 런처
			</Button>
			<Button variant="secondary" href={brand.colab} size="lg" class="text-base px-8 py-3">
				Colab 열기
			</Button>
			<Button variant="secondary" href={brand.molab} size="lg" class="text-base px-8 py-3">
				Molab 열기
			</Button>
		</div>

		<a
			href="https://huggingface.co/datasets/{brand.hfRepo}"
			target="_blank"
			rel="noopener"
			class="group block max-w-2xl mx-auto px-5 py-4 rounded-lg bg-dl-bg-card/50 border border-dl-border/50 hover:border-dl-primary/30 transition-colors text-left no-underline"
		>
			<div class="flex items-center gap-3 mb-3">
				<span class="text-2xl" aria-hidden="true">🤗</span>
				<div class="min-w-0">
					<div class="text-[10px] font-mono text-dl-text-dim tracking-[0.15em] uppercase">데이터셋 · Hugging Face</div>
					<div class="font-mono text-sm text-dl-text group-hover:text-dl-primary-light transition-colors truncate">
						{brand.hfRepo}
					</div>
				</div>
				<span class="ml-auto text-dl-primary text-xs font-mono opacity-60 group-hover:opacity-100 transition-opacity">View →</span>
			</div>
			<div class="flex flex-wrap gap-1.5">
				{#each Object.values(brand.data) as block}
					<span class="px-2 py-0.5 rounded-md bg-dl-bg-darker/70 border border-dl-border/50 text-[11px] font-mono text-dl-text-muted">
						{block.dir}
					</span>
				{/each}
			</div>
		</a>
	</div>
</section>
