<script lang="ts">
	import { base } from '$app/paths';
	import { brand } from '$lib/brand';

	const footerLinks = {
		'제품': [
			{ label: '시작하기', href: `${base}/skills/start.installUv` },
			{ label: 'Skills', href: `${base}/skills` },
			{ label: '릴리즈', href: `${brand.repo}/releases` },
			{ label: 'PyPI', href: brand.pypi }
		],
		'리소스': [
			{ label: '블로그', href: `${base}/blog/` },
			{ label: 'GitHub', href: brand.repo },
			{ label: '이슈', href: `${brand.repo}/issues` },
			{ label: '데이터셋', href: `https://huggingface.co/datasets/${brand.hfRepo}` }
		],
		'커뮤니티': [
			{ label: 'YouTube · @eddmpython', href: brand.youtube },
			{ label: 'Threads · @dartlab.ai', href: brand.threads },
			{ label: 'Instagram · @dartlab.ai', href: brand.instagram },
			{ label: '이메일', href: 'mailto:eddmpython@gmail.com' }
		]
	};
</script>

<footer class="border-t border-dl-border pt-10 pb-6 px-6 bg-dl-bg-darker">
	<div class="max-w-6xl mx-auto">
		<div class="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
			<div class="col-span-2 md:col-span-1">
				<div class="flex items-center gap-1.5 mb-2">
					<picture>
						<source srcset="{base}/avatar.webp" type="image/webp" />
						<img src="{base}/avatar.png" alt="DartLab" width="20" height="20" loading="lazy" decoding="async" class="rounded-full" />
					</picture>
					<span class="text-sm font-semibold text-dl-text">DartLab</span>
				</div>
				<p class="text-xs text-dl-text-dim leading-relaxed mb-3 max-w-[200px]">{brand.description}</p>
				<a href={brand.coffee} target="_blank" rel="noopener" class="inline-block">
					<img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" width="120" height="34" loading="lazy" decoding="async" class="hover:opacity-90 transition-opacity" />
				</a>
			</div>

			{#each Object.entries(footerLinks) as [title, links]}
				<div>
					<h5 class="text-[11px] font-semibold uppercase tracking-wider text-dl-text-muted mb-3">{title}</h5>
					<div class="flex flex-col gap-1.5">
						{#each links as link}
							<a href={link.href}
								target={link.href.startsWith('http') ? '_blank' : undefined}
								rel={link.href.startsWith('http') ? 'noopener' : undefined}
								class="text-xs text-dl-text-dim hover:text-dl-text transition-colors no-underline">
								{link.label}
							</a>
						{/each}
					</div>
				</div>
			{/each}
		</div>

		<div class="flex flex-col md:flex-row justify-between items-center pt-4 border-t border-dl-border text-[11px] text-dl-text-dim gap-1">
			<span>Apache License 2.0</span>
			<span>Made by <a href="https://github.com/eddmpython" class="text-dl-text-muted hover:text-dl-text transition-colors no-underline">eddmpython</a></span>
		</div>
	</div>
</footer>
