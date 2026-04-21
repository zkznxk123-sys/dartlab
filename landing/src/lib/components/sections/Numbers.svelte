<script lang="ts">
	const features = [
		{ title: 'Korean DART', desc: 'Every filing pre-structured' },
		{ title: 'US EDGAR', desc: 'Same interface, different country' },
		{ title: 'Account resolution', desc: 'One revenue, not dozens of variations' },
		{ title: 'Section canonicals', desc: 'Every variant mapped to the same topic' },
		{ title: 'Auto-structuring', desc: 'Raw filings to DataFrame. No cleaning.' },
		{ title: 'Ratios precomputed', desc: 'Profitability, liquidity, valuation — ready on load' }
	];
</script>

<section class="py-20 px-6 relative overflow-hidden">
	<div class="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(234,70,71,0.04)_0%,_transparent_60%)]"></div>

	<div class="relative max-w-5xl mx-auto">
		<div class="text-center mb-12">
			<span class="text-xs font-semibold uppercase tracking-widest text-dl-primary mb-3 block">What's Already Done</span>
			<h2 class="text-3xl md:text-4xl font-bold text-dl-text">Already Structured, Ready to Use</h2>
		</div>

		<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
			{#each features as f}
				<div class="relative px-5 py-5 rounded-lg border border-dl-border/50 bg-dl-bg-card/30 hover:border-dl-primary/30 hover:bg-dl-bg-card/60 transition-all duration-300">
					<div class="flex items-start gap-3">
						<span class="mt-1 w-1.5 h-1.5 rounded-full bg-dl-primary shrink-0"></span>
						<div>
							<div class="text-sm font-semibold text-dl-text mb-1">{f.title}</div>
							<div class="text-xs text-dl-text-muted leading-relaxed">{f.desc}</div>
						</div>
					</div>
				</div>
			{/each}
		</div>
	</div>
</section>
