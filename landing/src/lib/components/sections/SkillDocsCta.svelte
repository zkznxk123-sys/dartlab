<script lang="ts">
	import { base } from '$app/paths';
	import { BookOpenCheck, Bot, Network, Search, ShieldCheck } from 'lucide-svelte';

	const flows = [
		{
			icon: Search,
			title: '목적 검색',
			desc: '질문을 skill catalog에서 먼저 찾고 절차를 고른다.'
		},
		{
			icon: Network,
			title: 'Capability 연결',
			desc: 'skill이 참조하는 공개 API docstring과 근거 요구사항을 확인한다.'
		},
		{
			icon: ShieldCheck,
			title: 'Runtime 검증',
			desc: 'Local Python, Pyodide, MCP, Web AI에서 실행 가능한 범위를 분리한다.'
		}
	];

	const surfaces = ['자체 AI', '외부 AI', 'MCP', 'Web UI', 'Notebook'];
</script>

<section id="skill-docs" class="py-24 px-6 bg-dl-bg-darker/45">
	<div class="max-w-6xl mx-auto">
		<div class="grid lg:grid-cols-[0.9fr_1.1fr] gap-10 items-start">
			<div>
				<span class="text-xs font-semibold uppercase tracking-widest text-dl-primary mb-3 block">Skill Catalog</span>
				<h2 class="text-3xl md:text-4xl font-bold text-dl-text mb-4 leading-tight">
					분석 절차의 기준은 src/dartlab/skills다
				</h2>
				<p class="text-dl-text-muted text-base leading-relaxed mb-6 max-w-xl">
					DartLab의 API 설명은 docstring에서 나오고, 분석 절차는 SkillSpec에서 나온다.
					사용자 문서, 자체 AI, 외부 AI, MCP, Web UI는 같은 skill resolver를 읽는다.
				</p>
				<div class="flex flex-wrap gap-2 mb-7">
					{#each surfaces as surface}
						<span class="inline-flex items-center gap-1.5 h-7 px-3 rounded-md border border-dl-border bg-dl-bg-card/55 text-xs text-dl-text-muted">
							<Bot class="w-3 h-3 text-dl-primary" />
							{surface}
						</span>
					{/each}
				</div>
				<div class="flex flex-wrap gap-3">
					<a
						href="{base}/skills"
						class="inline-flex items-center gap-2 h-10 px-4 rounded-md bg-dl-primary text-white text-sm font-semibold no-underline hover:bg-dl-primary/90 transition-colors"
					>
						<BookOpenCheck class="w-4 h-4" />
						Skill Catalog 열기
					</a>
					<a
						href="https://github.com/eddmpython/dartlab/blob/master/CAPABILITIES.md"
						target="_blank"
						rel="noopener"
						class="inline-flex items-center gap-2 h-10 px-4 rounded-md border border-dl-border text-dl-text-muted text-sm font-semibold no-underline hover:text-dl-text hover:border-dl-primary/40 transition-colors"
					>
						<Network class="w-4 h-4" />
						Capability 보기
					</a>
				</div>
			</div>

			<div class="grid md:grid-cols-3 gap-3">
				{#each flows as item, index}
					{@const Icon = item.icon}
					<div class="rounded-lg border border-dl-border bg-dl-bg-card/55 p-5 min-h-[190px]">
						<div class="flex items-center justify-between mb-5">
							<div class="w-10 h-10 rounded-md border border-dl-primary/25 bg-dl-primary/10 text-dl-primary flex items-center justify-center">
								<Icon class="w-5 h-5" />
							</div>
							<span class="font-mono text-xs text-dl-text-dim">0{index + 1}</span>
						</div>
						<h3 class="text-base font-bold text-dl-text mb-2">{item.title}</h3>
						<p class="text-sm text-dl-text-muted leading-relaxed m-0">{item.desc}</p>
					</div>
				{/each}
			</div>
		</div>
	</div>
</section>
