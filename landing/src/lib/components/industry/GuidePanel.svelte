<script lang="ts">
	interface Props {
		open: boolean;
		onClose: () => void;
	}
	let { open, onClose }: Props = $props();

	type Tab = 'view' | 'color' | 'tips' | 'data';
	let activeTab: Tab = $state('view');

	function handleKey(e: KeyboardEvent) {
		if (e.key === 'Escape') onClose();
	}
</script>

<svelte:window onkeydown={handleKey} />

{#if open}
	<div
		class="backdrop"
		role="dialog"
		aria-modal="true"
		aria-label="지도 보는 법"
		onclick={onClose}
		onkeydown={(e) => e.key === 'Escape' && onClose()}
		tabindex="-1"
	>
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions a11y_click_events_have_key_events -->
		<div class="panel" role="document" onclick={(e) => e.stopPropagation()} tabindex="-1">
			<header>
				<h2>산업지도 사용 가이드</h2>
				<button class="close" onclick={onClose} aria-label="닫기">✕</button>
			</header>

			<nav class="tabs">
				<button class:active={activeTab === 'view'} onclick={() => (activeTab = 'view')}>
					뷰 3종
				</button>
				<button class:active={activeTab === 'color'} onclick={() => (activeTab = 'color')}>
					색상 기준
				</button>
				<button class:active={activeTab === 'tips'} onclick={() => (activeTab = 'tips')}>
					분석 팁
				</button>
				<button class:active={activeTab === 'data'} onclick={() => (activeTab = 'data')}>
					데이터 출처
				</button>
			</nav>

			<div class="body">
				{#if activeTab === 'view'}
					<section>
						<h3>산업 지도 (기본 뷰)</h3>
						<p>
							한국 상장사가 속한 <strong>34개 산업</strong>을 버블로, 산업 간
							<strong>supplier 공급 흐름</strong>을 엣지로 표시합니다. 버블 크기 = 소속 회사 수,
							테두리 빛나는 흰 원 = <strong>허브 산업</strong>(연결 상위 20%).
						</p>
						<p class="cta">버블 클릭 → 해당 산업 <strong>내부 드릴다운</strong>.</p>
					</section>
					<section>
						<h3>전 회사 (Cosmograph)</h3>
						<p>
							2,664 상장사 + 18,418 공급망 엣지 전체. 좌측 <strong>산업 토글/신뢰도 필터/금액 공개
								엣지만</strong> 으로 줄여 보세요. 줌인 시 회사명 자동 표시.
						</p>
					</section>
					<section>
						<h3>산업 내부 (드릴다운)</h3>
						<p>
							한 산업의 회사들을 <strong>공정(stage)</strong>별로 클러스터링해 배치. 마우스 휠 줌,
							드래그 팬 지원. 테두리 색은 <strong>업스트림(보라) / 미드(흰) / 다운(주황)</strong>.
						</p>
					</section>
				{:else if activeTab === 'color'}
					<section>
						<h3>산업 팔레트 (기본)</h3>
						<p>각 산업 고유 색. 공급망 덩어리를 시각적으로 구분할 때.</p>
					</section>
					<section>
						<h3>ROE (자기자본수익률)</h3>
						<div class="scale">
							<span class="sw" style="background:#ef4444"></span>≤ -10%
							<span class="sw" style="background:#f59e0b"></span>0%
							<span class="sw" style="background:#84cc16"></span>10%
							<span class="sw" style="background:#10b981"></span>≥ 20%
						</div>
						<p>주주 자본 대비 수익성. 투자 효율의 대표 지표. 산업 평균 편차 크므로 동일 산업 내 비교가 의미 있음.</p>
					</section>
					<section>
						<h3>영업이익률</h3>
						<div class="scale">
							<span class="sw" style="background:#ef4444"></span>≤ -5%
							<span class="sw" style="background:#f59e0b"></span>0%
							<span class="sw" style="background:#84cc16"></span>10%
							<span class="sw" style="background:#10b981"></span>≥ 20%
						</div>
						<p>본업 수익성. 재무 레버리지/세금 영향 전 단계. 업종 특성(제조 vs 유통)에 따라 절대 수준 차이 큼.</p>
					</section>
					<section>
						<h3>부채비율 (역방향 스케일)</h3>
						<div class="scale">
							<span class="sw" style="background:#10b981"></span>≤ 50%
							<span class="sw" style="background:#84cc16"></span>100%
							<span class="sw" style="background:#f59e0b"></span>200%
							<span class="sw" style="background:#ef4444"></span>≥ 400%
						</div>
						<p>부채 / 자본. 낮을수록 안전. 금융업은 구조상 높으므로 해석 주의.</p>
					</section>
					<section>
						<h3>매출 CAGR (3년)</h3>
						<p>복리 매출 성장률. 고성장 vs 정체 판별.</p>
					</section>
					<section>
						<h3>매출 규모</h3>
						<p>로그 스케일 파란 계열. 대기업 vs 중소 시각화.</p>
					</section>
				{:else if activeTab === 'tips'}
					<section>
						<h3>A. 이 산업이 지금 어떤 모양인가?</h3>
						<ol>
							<li>atlas 뷰에서 색상 기준을 <strong>"매출 CAGR"</strong>로 → 성장 산업 즉시 판별</li>
							<li>색상 기준을 <strong>"ROE"</strong> → 수익성 산업 군집 확인</li>
							<li>두 기준 모두 초록인 산업 = 성장+수익 동시 우량</li>
						</ol>
					</section>
					<section>
						<h3>B. 이 안에서 누가 강자/약자인가?</h3>
						<ol>
							<li>산업 버블 클릭 → 드릴다운 진입</li>
							<li>좌측 색상 기준을 "ROE"로 → 공정별로 색 분포 비교</li>
							<li>큰 원 + 초록 = 매출 큰 우량, 큰 원 + 빨강 = 매출은 크지만 수익성 약</li>
							<li>회사 클릭 → 우측 카드에서 <strong>산업 내 분위(percentile)</strong> 확인</li>
						</ol>
					</section>
					<section>
						<h3>C. 이 회사의 핵심 거래는?</h3>
						<ol>
							<li>회사 클릭 → 우측 카드 <strong>"핵심 거래 (정밀 Top 5)"</strong> 섹션</li>
							<li>공급사 중 Top1 비중이 50% 넘으면 의존 리스크</li>
							<li>HHI 게이지 "집중" (빨강) → 공급망 다각화 필요 신호</li>
						</ol>
					</section>
					<section>
						<h3>D. 비교</h3>
						<ol>
							<li>첫 회사 선택 → "+ 비교에 추가" 클릭</li>
							<li>두 번째 회사 클릭 → 우측 패널 자동 2분할</li>
							<li>공통 공급사/고객사가 많으면 <strong>같은 밸류체인</strong>의 경쟁자</li>
						</ol>
					</section>
					<section class="warn">
						<h3>⚠ 주의</h3>
						<ul>
							<li>ROE > 100% 는 자본잠식 or 1회성 이익 가능성. 반드시 추세 확인</li>
							<li>amount=null 엣지는 "관계 있음"만 의미. 거래 규모 모름</li>
							<li>매핑 신뢰도 &lt; 0.6 인 회사는 자동분류 추정 — 분류 신고 버튼 활용</li>
						</ul>
					</section>
				{:else if activeTab === 'data'}
					<section>
						<h3>데이터 소스</h3>
						<ul>
							<li>
								<strong>공시 원본</strong>: DART (금감원 전자공시) + EDGAR (SEC, 해외 상장사). 사업보고서 + XBRL 재무제표
							</li>
							<li>
								<strong>재무 지표</strong>: dartlab <code>scan</code> 엔진 — profitability / debt / growth 축. 전 종목 사전 계산
							</li>
							<li>
								<strong>공급망 엣지</strong>: 사업보고서 원재료/매출처 섹션에서 상장사명 매칭. 숫자 추출된 것만 "정밀 엣지"
							</li>
							<li>
								<strong>산업 분류</strong>: KSIC → 주요제품 → docs 매칭 3단계 파이프라인. 사람 검수 override 반영
							</li>
							<li><strong>AI 인사이트</strong>: dartlab AI (Claude/Gemini) 분석 결과. 블로그 포스트 verdict 연동</li>
						</ul>
					</section>
					<section>
						<h3>한계</h3>
						<ul>
							<li>enriched 데이터는 매출 상위 500사만 — 우측 카드의 5년 차트/AI 인사이트 한정</li>
							<li>분기 갱신 주기 — 최신 이벤트(인수/합병)는 반영 지연 가능</li>
							<li>KS/KQ 상장사만. 비상장/외국법인 제외</li>
						</ul>
					</section>
				{/if}
			</div>
		</div>
	</div>
{/if}

<style>
	.backdrop {
		position: fixed;
		inset: 0;
		background: rgba(5, 8, 17, 0.7);
		backdrop-filter: blur(4px);
		z-index: 100;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 24px;
	}
	.panel {
		width: 100%;
		max-width: 720px;
		max-height: 90vh;
		background: #0f1219;
		border: 1px solid #1e2433;
		border-radius: 12px;
		color: #f1f5f9;
		display: flex;
		flex-direction: column;
		box-shadow: 0 24px 48px rgba(0, 0, 0, 0.6);
	}
	header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 18px 24px;
		border-bottom: 1px solid #1e2433;
	}
	header h2 {
		margin: 0;
		font-size: 18px;
	}
	.close {
		background: none;
		border: none;
		font-size: 18px;
		color: #64748b;
		cursor: pointer;
	}
	.close:hover {
		color: #f1f5f9;
	}
	.tabs {
		display: flex;
		gap: 4px;
		padding: 8px 16px 0;
		border-bottom: 1px solid #1e2433;
	}
	.tabs button {
		background: none;
		border: none;
		color: #94a3b8;
		padding: 10px 14px;
		font-size: 13px;
		cursor: pointer;
		border-bottom: 2px solid transparent;
		margin-bottom: -1px;
	}
	.tabs button:hover {
		color: #f1f5f9;
	}
	.tabs button.active {
		color: #60a5fa;
		border-bottom-color: #60a5fa;
	}
	.body {
		padding: 18px 24px;
		overflow-y: auto;
		font-size: 13px;
		line-height: 1.7;
		color: #cbd5e1;
	}
	section {
		margin-bottom: 18px;
		padding-bottom: 14px;
		border-bottom: 1px dashed #1e2433;
	}
	section:last-child {
		border-bottom: none;
	}
	section.warn {
		background: rgba(239, 68, 68, 0.06);
		border: 1px solid rgba(239, 68, 68, 0.18);
		border-radius: 6px;
		padding: 10px 14px;
	}
	section h3 {
		margin: 0 0 6px;
		font-size: 14px;
		color: #f1f5f9;
		font-weight: 600;
	}
	section p {
		margin: 4px 0;
	}
	section p.cta {
		color: #60a5fa;
	}
	section ol,
	section ul {
		margin: 6px 0;
		padding-left: 22px;
	}
	section li {
		margin: 4px 0;
	}
	section strong {
		color: #f1f5f9;
	}
	.scale {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 12px;
		color: #94a3b8;
		margin: 6px 0 8px;
	}
	.sw {
		width: 16px;
		height: 10px;
		border-radius: 3px;
		display: inline-block;
	}
	code {
		background: #1e2433;
		padding: 1px 5px;
		border-radius: 3px;
		font-size: 12px;
	}
</style>
