<section class="py-24 px-6">
	<div class="mx-auto max-w-4xl">
		<div class="text-center mb-12">
			<span class="text-xs font-semibold uppercase tracking-widest text-dl-primary mb-3 block"
				>AI Analysis</span
			>
			<h2 class="text-3xl md:text-4xl font-bold text-dl-text mb-4">
				No Code Required. Just Ask.
			</h2>
			<p class="text-dl-text-muted text-lg max-w-2xl mx-auto">
				DartLab structures the data and feeds it to the LLM. You ask questions in plain language
				&mdash; from your terminal or Python.
			</p>
		</div>

		<div class="grid md:grid-cols-2 gap-5">
			<!-- Terminal -->
			<div
				class="rounded-lg overflow-hidden bg-[#0d1117] border border-dl-border shadow-lg shadow-black/20"
			>
				<div
					class="flex items-center gap-2 px-4 py-2.5 bg-white/[0.03] border-b border-dl-border"
				>
					<div class="flex gap-1.5">
						<span class="w-2.5 h-2.5 rounded-full bg-[#ff5f57]"></span>
						<span class="w-2.5 h-2.5 rounded-full bg-[#febc2e]"></span>
						<span class="w-2.5 h-2.5 rounded-full bg-[#28c840]"></span>
					</div>
					<span class="text-xs text-dl-text-dim font-mono ml-2">Terminal</span>
				</div>
				<div class="p-4 font-mono text-xs leading-relaxed">
					<div class="text-dl-text-muted">
						<span class="text-dl-accent">$</span> dartlab ask "삼성전자 재무건전성 분석해줘"
					</div>
					<br />
					<div class="text-dl-text-dim">Analyzing Samsung Electronics (005930)...</div>
					<div class="text-dl-text-dim mb-2">Loading financials, ratios, insights...</div>
					<br />
					<div class="text-dl-text">
						Samsung Electronics shows <span class="text-dl-primary">strong financial health</span
						>:
					</div>
					<div class="text-dl-text-muted mt-1">
						&bull; Debt ratio: 31.8% (sector avg: 45.2%)
					</div>
					<div class="text-dl-text-muted">
						&bull; Current ratio: 258.6% &mdash; well above safety
					</div>
					<div class="text-dl-text-muted">
						&bull; ROE recovery: 1.6% &rarr; 10.2% over 4 quarters
					</div>
					<div class="text-dl-text-muted">&bull; Interest coverage: 22.1x</div>
				</div>
			</div>

			<!-- Python -->
			<div
				class="rounded-lg overflow-hidden bg-[#0d1117] border border-dl-border shadow-lg shadow-black/20"
			>
				<div
					class="flex items-center gap-2 px-4 py-2.5 bg-white/[0.03] border-b border-dl-border"
				>
					<div class="flex gap-1.5">
						<span class="w-2.5 h-2.5 rounded-full bg-[#ff5f57]"></span>
						<span class="w-2.5 h-2.5 rounded-full bg-[#febc2e]"></span>
						<span class="w-2.5 h-2.5 rounded-full bg-[#28c840]"></span>
					</div>
					<span class="text-xs text-dl-text-dim font-mono ml-2">Python</span>
				</div>
				<div class="p-4 font-mono text-xs leading-relaxed">
					<div>
						<span class="text-purple-400">import</span>
						<span class="text-dl-text">dartlab</span>
					</div>
					<br />
					<div class="text-dl-text-dim"># one-liner &mdash; streams to stdout</div>
					<div>
						<span class="text-dl-text">dartlab</span><span class="text-dl-text-muted"
							>.</span
						><span class="text-cyan-400">ask</span><span class="text-dl-text-muted"
							>(</span
						><span class="text-emerald-400">"AAPL risk analysis"</span><span
							class="text-dl-text-muted">)</span
						>
					</div>
					<br />
					<div class="text-dl-text-dim"># with options</div>
					<div>
						<span class="text-dl-text">dartlab</span><span class="text-dl-text-muted"
							>.</span
						><span class="text-cyan-400">ask</span><span class="text-dl-text-muted"
							>(</span
						>
					</div>
					<div class="pl-4">
						<span class="text-emerald-400">"삼성전자 배당 분석"</span><span
							class="text-dl-text-muted">,</span
						>
					</div>
					<div class="pl-4">
						<span class="text-dl-text">provider</span><span class="text-dl-text-muted"
							>=</span
						><span class="text-emerald-400">"openai"</span><span class="text-dl-text-muted"
							>,</span
						>
					</div>
					<div class="pl-4">
						<span class="text-dl-text">include</span><span class="text-dl-text-muted"
							>=[</span
						><span class="text-emerald-400">"dividend"</span><span
							class="text-dl-text-muted">,</span
						>
						<span class="text-emerald-400">"IS"</span><span class="text-dl-text-muted"
							>]</span
						>
					</div>
					<div><span class="text-dl-text-muted">)</span></div>
					<br />
					<div class="text-dl-text-dim"># 5 providers: ollama, openai,</div>
					<div class="text-dl-text-dim"># oauth-codex, codex, custom</div>
				</div>
			</div>
		</div>

		<!-- AI as active analyst: override engine assumptions mid-conversation -->
		<div class="mt-6 rounded-lg overflow-hidden bg-[#0d1117] border border-dl-border shadow-lg shadow-black/20">
			<div class="flex items-center gap-2 px-4 py-2.5 bg-white/[0.03] border-b border-dl-border">
				<span class="w-2 h-2 rounded-full bg-dl-primary"></span>
				<span class="text-xs text-dl-text-dim font-mono ml-1">AI is not read-only &mdash; engine assumptions are negotiable</span>
			</div>
			<div class="p-4 font-mono text-xs leading-relaxed space-y-2">
				<div>
					<span class="text-dl-accent">you</span>
					<span class="text-dl-text-dim">›</span>
					<span class="text-dl-text">삼성전자 DCF 계산해봐</span>
				</div>
				<div>
					<span class="text-dl-primary">ai</span>
					<span class="text-dl-text-dim">›</span>
					<span class="text-dl-text-muted">c.analysis("valuation")</span>
					<span class="text-dl-text-dim">&rarr;</span>
					<span class="text-dl-warning">implied WACC 18.2% looks high for this profile</span>
				</div>
				<div>
					<span class="text-dl-accent">you</span>
					<span class="text-dl-text-dim">›</span>
					<span class="text-dl-text">WACC 9%로 재계산</span>
				</div>
				<div>
					<span class="text-dl-primary">ai</span>
					<span class="text-dl-text-dim">›</span>
					<span class="text-dl-text-muted">c.analysis(</span><span class="text-emerald-400">"valuation"</span><span class="text-dl-text-muted">, overrides=&#123;</span><span class="text-emerald-400">"wacc"</span><span class="text-dl-text-muted">:</span>
					<span class="text-dl-accent">0.09</span><span class="text-dl-text-muted">&#125;)</span>
				</div>
				<div class="pl-6 text-dl-text">
					<span class="text-dl-text-dim">&rarr;</span> revised fair value band: <span class="text-dl-success">91.2k ~ 115.4k KRW / share</span>
				</div>
			</div>
			<div class="px-4 py-3 border-t border-dl-border text-[11px] text-dl-text-dim leading-relaxed">
				The AI is not a read-only summarizer. It can <span class="text-dl-text">override engine assumptions</span> &mdash;
				WACC, growth rate, peer group, discount period &mdash; and recompute inside the same session. You stay in the driver's seat.
			</div>
		</div>

		<div class="text-center mt-8">
			<p class="text-dl-text-dim text-xs">
				The 2-tier architecture feeds structured company data to any LLM. Basic analysis works
				with every provider. Tool-calling providers go deeper.
			</p>
		</div>
	</div>
</section>
