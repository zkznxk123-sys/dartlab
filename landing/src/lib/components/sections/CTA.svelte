<script lang="ts">
	import { base } from '$app/paths';
	import { brand } from '$lib/brand';
	import { Button } from '$lib/components/ui/button';
</script>

<section class="py-24 px-6">
	<div class="mx-auto max-w-2xl text-center">
		<div
			class="p-8 md:p-12 rounded-lg bg-dl-bg-card border border-dl-border relative overflow-hidden"
		>
			<div
				class="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(234,70,71,0.05)_0%,_transparent_70%)]"
			></div>
			<div class="relative">
				<div class="mb-6 flex justify-center">
					<picture>
						<source srcset="{base}/avatar-discover.webp" type="image/webp" />
						<img
							src="{base}/avatar-discover.png"
							alt="DartLab mascot"
							width="120"
							height="120"
							loading="lazy"
							decoding="async"
							class="drop-shadow-[0_0_24px_rgba(234,70,71,0.35)] animate-float"
						/>
					</picture>
				</div>
				<h2 class="text-2xl md:text-3xl font-bold text-dl-text mb-3">PDF 가 아니라 기업을 읽는다</h2>
				<p class="text-dl-text-muted mb-3 text-lg">
					종목코드 하나. 모든 공시 구조화. 모든 기간 비교 가능.
				</p>
				<p class="text-sm text-dl-text-dim mb-8">PDF 며칠 분량의 작업이 Python 한 줄로 끝난다.</p>

				<div class="flex flex-wrap items-center justify-center gap-4">
					<Button href={brand.desktop}>Windows 런처 →</Button>
					<Button variant="secondary" href={brand.colab}>Colab 열기</Button>
					<Button variant="secondary" href={brand.molab}>Molab 열기</Button>
				</div>
			</div>
		</div>
	</div>
</section>
