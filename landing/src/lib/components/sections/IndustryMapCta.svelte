<script lang="ts">
	import { base } from '$app/paths';
</script>

<section class="dl-map-cta" aria-labelledby="map-cta-title">
	<div class="inner">
		<div class="left">
			<div class="kicker">Live Visualization</div>
			<h2 id="map-cta-title">한국 상장사들이 서로 어떻게 얽혀 있는지, <br />10초 안에 보는 지도</h2>
			<p class="lead">
				2,664개 상장사 · 34개 산업 · 공급망 18,418개 관계를 한 화면에서. 버블 클릭으로
				산업 내부 드릴다운, 회사 선택 시 5년 재무·공급망 HHI·AI 분석·심층 리포트
				한 카드에. <strong>이번 회계연도 급변 회사도 자동 감지.</strong>
			</p>
			<div class="ctas">
				<a class="primary" href="{base}/map">산업지도 열기 →</a>
				<a class="ghost" href="{base}/changes">이번 분기 급변 보기</a>
			</div>
			<p class="disclaimer">
				dartlab 은 공시·재무 데이터를 시각화합니다. 투자 자문 아닙니다.
				해석은 DART 원본·증권사 리포트와 함께 내리세요.
			</p>
		</div>
		<div class="right">
			<div class="preview">
				<div class="preview-head">
					<span class="dot r"></span>
					<span class="dot y"></span>
					<span class="dot g"></span>
					<span class="url">dartlab.io/map</span>
				</div>
				<div class="preview-body">
					<div class="preview-row">
						<span class="bubble" style="width:54px;height:54px;background:#0ea5e9;left:12%;top:8%"></span>
						<span class="bubble" style="width:72px;height:72px;background:#f97316;left:34%;top:22%"></span>
						<span class="bubble" style="width:48px;height:48px;background:#10b981;left:58%;top:10%"></span>
						<span class="bubble" style="width:60px;height:60px;background:#8b5cf6;left:70%;top:48%"></span>
						<span class="bubble" style="width:40px;height:40px;background:#ec4899;left:20%;top:60%"></span>
						<span class="bubble" style="width:52px;height:52px;background:#fbbf24;left:46%;top:62%"></span>
						<span class="bubble small" style="width:20px;height:20px;background:#60a5fa;left:82%;top:22%"></span>
						<span class="bubble small" style="width:18px;height:18px;background:#34d399;left:8%;top:38%"></span>
						<svg class="flows" viewBox="0 0 400 240">
							<path d="M 60 40 Q 140 80 150 70" stroke="#fbbf24" stroke-width="2" fill="none" opacity="0.6" />
							<path d="M 170 70 Q 230 40 250 30" stroke="#fbbf24" stroke-width="3" fill="none" opacity="0.75" />
							<path d="M 265 35 Q 280 100 310 120" stroke="#fbbf24" stroke-width="2" fill="none" opacity="0.5" />
							<path d="M 150 70 Q 130 140 110 160" stroke="#fb923c" stroke-width="2" fill="none" opacity="0.4" />
						</svg>
					</div>
					<div class="preview-chips">
						<span class="chip g">● 데이터 3h 전</span>
						<span class="chip n">반도체 · 348사</span>
						<span class="chip w">⚠ 이번 분기 급변 12사</span>
					</div>
				</div>
			</div>
		</div>
	</div>
</section>

<style>
	.dl-map-cta {
		padding: 80px 24px;
		background: linear-gradient(180deg, #050811 0%, #0f1219 100%);
		color: #f1f5f9;
	}
	.inner {
		max-width: 1200px;
		margin: 0 auto;
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 48px;
		align-items: center;
	}
	.kicker {
		font-size: 11px;
		color: #60a5fa;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		font-weight: 600;
		margin-bottom: 12px;
	}
	h2 {
		font-size: 38px;
		font-weight: 700;
		line-height: 1.25;
		margin: 0 0 20px;
		letter-spacing: -0.02em;
	}
	.lead {
		font-size: 15px;
		line-height: 1.7;
		color: #cbd5e1;
		margin: 0 0 24px;
	}
	.lead strong {
		color: #fbbf24;
	}
	.ctas {
		display: flex;
		gap: 10px;
		flex-wrap: wrap;
	}
	.primary {
		padding: 12px 22px;
		background: #60a5fa;
		color: #050811;
		border-radius: 8px;
		text-decoration: none;
		font-weight: 700;
		font-size: 14px;
	}
	.primary:hover {
		background: #93c5fd;
	}
	.ghost {
		padding: 12px 22px;
		background: transparent;
		color: #cbd5e1;
		border: 1px solid #334155;
		border-radius: 8px;
		text-decoration: none;
		font-size: 14px;
	}
	.ghost:hover {
		background: #1e2433;
		color: #f1f5f9;
	}
	.disclaimer {
		margin-top: 16px;
		font-size: 11px;
		color: #64748b;
		line-height: 1.6;
	}

	.preview {
		background: #0f1219;
		border: 1px solid #1e2433;
		border-radius: 12px;
		overflow: hidden;
		box-shadow: 0 24px 48px rgba(0, 0, 0, 0.4);
	}
	.preview-head {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 10px 14px;
		background: #050811;
		border-bottom: 1px solid #1e2433;
	}
	.preview-head .dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
	}
	.preview-head .dot.r {
		background: #f87171;
	}
	.preview-head .dot.y {
		background: #fbbf24;
	}
	.preview-head .dot.g {
		background: #34d399;
	}
	.preview-head .url {
		margin-left: auto;
		font-family: monospace;
		font-size: 11px;
		color: #64748b;
	}
	.preview-body {
		position: relative;
		height: 280px;
		background: radial-gradient(ellipse at center, rgba(30, 41, 59, 0.3) 0%, transparent 70%),
			#050811;
		overflow: hidden;
	}
	.bubble {
		position: absolute;
		border-radius: 50%;
		opacity: 0.85;
		filter: blur(0.3px);
	}
	.bubble.small {
		opacity: 0.6;
	}
	.flows {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		pointer-events: none;
	}
	.preview-chips {
		position: absolute;
		bottom: 12px;
		left: 12px;
		display: flex;
		gap: 6px;
		flex-wrap: wrap;
	}
	.chip {
		padding: 4px 10px;
		background: rgba(5, 8, 17, 0.85);
		border: 1px solid #1e2433;
		border-radius: 999px;
		font-size: 11px;
		color: #cbd5e1;
		backdrop-filter: blur(6px);
	}
	.chip.g {
		color: #34d399;
	}
	.chip.w {
		color: #fbbf24;
		border-color: rgba(251, 191, 36, 0.4);
	}

	@media (max-width: 900px) {
		.inner {
			grid-template-columns: 1fr;
		}
		h2 {
			font-size: 28px;
		}
	}
</style>
