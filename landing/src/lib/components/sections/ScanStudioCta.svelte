<script lang="ts">
	import { base } from '$app/paths';
	import { Button } from '$lib/components/ui/button';
</script>

<section class="scan-cta" aria-labelledby="scan-cta-title">
	<div class="inner">
		<div class="copy">
			<div class="kicker">전종목 스크리닝</div>
			<h2 id="scan-cta-title">2,600개 회사를 한 테이블에서 바로 비교</h2>
			<p class="lead">
				산업·수익성·재무건전성·가치·공시 변화까지 같은 화면에서 정렬하고,
				자동 발굴 신호로 후보군을 먼저 좁힌 뒤 회사별 재무 그래프와 최근 정기공시를 확인한다.
			</p>
			<div class="ctas">
				<Button href="{base}/scan">Scan Studio 열기 →</Button>
				<Button variant="secondary" href="{base}/docs/">문서 보기</Button>
			</div>
		</div>

		<div class="preview" aria-hidden="true">
			<div class="preview-top">
				<span class="status-dot"></span>
				<span>데이터 활성</span>
				<span class="pill">재무건전성</span>
				<span class="pill">이익질</span>
				<span class="pill hot">가치</span>
			</div>
			<div class="preview-grid">
				<div class="table">
					<div class="thead">
						<span>회사명</span>
						<span>시장</span>
						<span>ROE</span>
						<span>부채비율</span>
						<span>등급</span>
					</div>
					{#each [
						['삼성전자', 'KOSPI', '68.5%', '29.9%', '양호'],
						['SK하이닉스', 'KOSPI', '10.0%', '45.9%', '양호'],
						['풍강', 'KOSDAQ', '3.1%', '30.1%', '양호'],
						['유한양행', 'KOSPI', '0.5%', '36.8%', '관찰']
					] as row, i}
						<div class="trow" class:active={i === 3}>
							<span><i></i>{row[0]}</span>
							<span>{row[1]}</span>
							<span class="num">{row[2]}</span>
							<span class="num">{row[3]}</span>
							<span class="grade">{row[4]}</span>
						</div>
					{/each}
				</div>
				<div class="side">
					<div class="side-title">자동 발굴 신호</div>
					<div class="signal"><span>ROE 급상승</span><strong>119.4%</strong></div>
					<div class="signal"><span>영업이익률 개선</span><strong>111.6%</strong></div>
					<div class="signal warn"><span>부채비율 급증</span><strong>497.4%</strong></div>
				</div>
			</div>
			<div class="detail">
				<div class="chart">
					<span class="bar a"></span><span class="bar b"></span><span class="bar c"></span><span class="line"></span>
				</div>
				<div class="chart">
					<span class="stack r"></span><span class="stack o"></span><span class="stack g"></span><span class="stack t"></span>
				</div>
				<div class="filings">
					<span>사업보고서 (2025.12)</span>
					<span>분기보고서 (2025.09)</span>
					<span>반기보고서 (2025.06)</span>
				</div>
			</div>
		</div>
	</div>
</section>

<style>
	.scan-cta {
		padding: 80px 24px;
		background: #050811;
		color: #f1f5f9;
	}
	.inner {
		max-width: 1200px;
		margin: 0 auto;
		display: grid;
		grid-template-columns: minmax(0, 0.78fr) minmax(0, 1.22fr);
		gap: 44px;
		align-items: center;
	}
	.kicker {
		font-size: 11px;
		color: #22c55e;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		font-weight: 700;
		margin-bottom: 12px;
	}
	h2 {
		font-size: 36px;
		line-height: 1.22;
		margin: 0 0 18px;
		font-weight: 800;
	}
	.lead {
		margin: 0 0 22px;
		color: #cbd5e1;
		font-size: 15px;
		line-height: 1.72;
	}
	.ctas {
		display: flex;
		gap: 10px;
		flex-wrap: wrap;
	}
	.preview {
		border: 1px solid #1e293b;
		border-radius: 8px;
		background: #070b14;
		box-shadow: 0 22px 52px rgba(0, 0, 0, 0.42);
		overflow: hidden;
	}
	.preview-top {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 10px 12px;
		border-bottom: 1px solid #1e293b;
		color: #94a3b8;
		font-size: 11px;
	}
	.status-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: #22c55e;
	}
	.pill {
		margin-left: 4px;
		padding: 3px 8px;
		border: 1px solid #243044;
		border-radius: 4px;
		color: #cbd5e1;
	}
	.pill.hot {
		color: #34d399;
		border-color: rgba(52, 211, 153, 0.45);
	}
	.preview-grid {
		display: grid;
		grid-template-columns: minmax(0, 1fr) 210px;
		min-height: 230px;
	}
	.table {
		min-width: 0;
		border-right: 1px solid #1e293b;
	}
	.thead,
	.trow {
		display: grid;
		grid-template-columns: 1.2fr 0.7fr 0.7fr 0.85fr 0.6fr;
		align-items: center;
	}
	.thead {
		height: 34px;
		padding: 0 12px;
		background: #0b1120;
		color: #94a3b8;
		font-size: 10px;
		font-weight: 700;
		border-bottom: 1px solid #1e293b;
	}
	.trow {
		height: 42px;
		padding: 0 12px;
		border-bottom: 1px solid rgba(30, 41, 59, 0.7);
		color: #dbeafe;
		font-size: 12px;
	}
	.trow.active {
		background: rgba(34, 197, 94, 0.09);
	}
	.trow span:first-child {
		display: inline-flex;
		align-items: center;
		gap: 7px;
		font-weight: 700;
		color: #f8fafc;
	}
	.trow i {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: #38bdf8;
	}
	.num {
		font-family: 'JetBrains Mono', 'Fira Code', monospace;
		color: #bbf7d0;
		text-align: right;
	}
	.grade {
		justify-self: start;
		padding: 2px 7px;
		border: 1px solid #22c55e;
		border-radius: 3px;
		color: #22c55e;
		font-size: 10px;
		font-weight: 700;
	}
	.side {
		padding: 13px;
		background: #050811;
	}
	.side-title {
		color: #64748b;
		font-size: 10px;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		margin-bottom: 12px;
	}
	.signal {
		display: flex;
		justify-content: space-between;
		gap: 12px;
		padding: 11px 0;
		border-bottom: 1px solid #1e293b;
		font-size: 12px;
		color: #cbd5e1;
	}
	.signal strong {
		color: #22c55e;
		font-family: 'JetBrains Mono', 'Fira Code', monospace;
	}
	.signal.warn strong {
		color: #f87171;
	}
	.detail {
		display: grid;
		grid-template-columns: 1fr 1fr 1.1fr;
		gap: 8px;
		padding: 8px;
		border-top: 1px solid #1e293b;
		background: #030712;
	}
	.chart,
	.filings {
		height: 78px;
		border: 1px solid #1e293b;
		border-radius: 5px;
		background: #070b14;
		position: relative;
		overflow: hidden;
	}
	.bar {
		position: absolute;
		bottom: 14px;
		width: 22px;
		background: #2563eb;
		border-radius: 2px 2px 0 0;
	}
	.bar.a { left: 24%; height: 32px; }
	.bar.b { left: 43%; height: 42px; }
	.bar.c { left: 62%; height: 52px; }
	.line {
		position: absolute;
		left: 20%;
		right: 18%;
		top: 30px;
		height: 2px;
		background: #22c55e;
		transform: rotate(-8deg);
	}
	.stack {
		position: absolute;
		left: 42%;
		width: 42px;
	}
	.stack.r { bottom: 14px; height: 15px; background: #ef4444; }
	.stack.o { bottom: 29px; height: 19px; background: #f97316; }
	.stack.g { bottom: 48px; height: 18px; background: #22c55e; }
	.stack.t { bottom: 66px; height: 9px; background: #14b8a6; }
	.filings {
		display: flex;
		flex-direction: column;
		justify-content: center;
		padding: 0 12px;
		gap: 7px;
	}
	.filings span {
		color: #cbd5e1;
		font-size: 11px;
		border-bottom: 1px solid rgba(30, 41, 59, 0.75);
		padding-bottom: 5px;
	}
	@media (max-width: 960px) {
		.inner,
		.preview-grid,
		.detail {
			grid-template-columns: 1fr;
		}
		.table {
			border-right: 0;
			border-bottom: 1px solid #1e293b;
		}
		h2 {
			font-size: 28px;
		}
	}
</style>
