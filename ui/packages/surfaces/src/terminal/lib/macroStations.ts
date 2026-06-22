// 매크로 분석 가이드 흐름 — 6 스테이션 스펙 (top-down 순서).
// 설계: macro-flow-station-spec 워크플로(6 병렬 거시 애널리스트 + 적대 검증). 적대 교정 반영:
//  ③국면=quadOf 좌표만(자산가중치·평면 재현 금지) · ①UNRATE 부호 반전(상승=감속) · overlay=z 정규화 · divergence=현재 z-격차(롤링상관 아님).
// ⛔ 무판정: question/insight/tests/why 어디에도 호재/매수/비중확대 류 0. 흐름·질문·관계까지만, 판단은 사용자.

export interface StationOverlay {
	a: string;
	b: string;
	tests: string; // 이 겹침이 검증하는 질문(무판정)
}
export interface StationDivergence {
	a: string;
	b: string;
	why: string; // 이 쌍을 감시하는 이유(교육)
}
export interface MacroStation {
	key: string;
	order: number;
	titleKr: string;
	titleEn: string;
	questionKr: string;
	questionEn: string;
	seriesIds: string[];
	overlays: StationOverlay[];
	divergences: StationDivergence[];
	insightKr: string;
	insightEn: string;
	feedsNextKr: string;
	honestyKr: string;
	synthesis?: boolean; // ③ 컴팩트 합성(지표 표 아님)
}

// breadth 방향집계 시 부호 반전(상승=둔화). 적대 교정 #4.
export const INVERT_SERIES = new Set<string>(['UNRATE']);

// 6-station 흐름 밖(정직 누락 — 좌패널 보드에서 개별 조회). 적대 교정 #5.
export const FLOW_OMITTED_NOTE =
	'HOUSE_PRICE(부동산)·M2(통화)·교차환율(JPY/EUR)·중간만기 금리(DGS10/30 등)는 본 6단계 흐름 밖 — 좌측 패널 보드에서 개별 조회. KR 고용 시계열 부재로 한·미 노동시장 직접 비교는 불가.';

export const MACRO_STATIONS: MacroStation[] = [
	{
		key: 'growth', order: 1,
		titleKr: '성장 — 경기는 가속하나 감속하나', titleEn: 'Growth — accelerating or decelerating?',
		questionKr: '선행(CLI·CSI)이 동행(생산·고용)보다 먼저 방향을 틀었나? 한국 외수(수출)와 내수생산(산업생산)은 같이 가나, 벌어지나?',
		questionEn: 'Have leads (CLI·CSI) turned before coincident (output·jobs)? Are KR exports and domestic production moving together or diverging?',
		seriesIds: ['CLI', 'CSI', 'EXPORT', 'IPI', 'EXPORT_PRICE', 'INDPRO', 'PAYEMS', 'UNRATE'],
		overlays: [
			{ a: 'CLI', b: 'IPI', tests: '선행지수(CLI)의 고·저점이 산업생산(IPI)보다 몇 개월 앞서나? CLI가 이미 꺾였는데 IPI가 버틴다면 그 시차가 뭘 예고하는지 스스로 물어라.' },
			{ a: 'EXPORT', b: 'IPI', tests: '한국 외수(수출)와 내수생산(IPI)이 같이 가나, 벌어지나? 갈라진다면 어느 쪽이 먼저 도는지 확인하라.' },
			{ a: 'PAYEMS', b: 'INDPRO', tests: '미국 고용과 산업생산의 둔화 순서 — 생산이 먼저 식고 고용이 뒤따르는 평소 패턴이 유지되나?' }
		],
		divergences: [
			{ a: 'EXPORT', b: 'IPI', why: '평소 동행하는 외수·내수생산이 벌어지면 어느 쪽이 엔진인지 점검(현재 z-격차로 표시).' },
			{ a: 'CLI', b: 'CSI', why: '선행지수와 소비자심리가 갈라지면 기업·통계 선행 vs 가계 체감 중 누가 먼저 신호 주는지 감시.' }
		],
		insightKr: '선행(CLI·CSI)과 동행(IPI·INDPRO·PAYEMS)의 방향이 같은지 다른지를 먼저 보라. 선행이 꺾였는데 동행이 버티면 "가속의 끝물", 반대면 "바닥 통과" 가능성을 스스로 물어라. 다음 수출 vs 산업생산 갭으로 외수·내수 중 엔진을 확인. ⚠ UNRATE는 상승=둔화(역방향). 단정 말고 "지금 사이클이 어디인가"를 다음으로.',
		insightEn: 'Check if leads (CLI·CSI) and coincident (IPI·INDPRO·PAYEMS) point the same way. Leads rolled over while coincident holds → late-cycle; reverse → trough. Then use exports vs IP to see the engine. UNRATE reads inversely (up = slowing). Carry "where in the cycle?" forward.',
		feedsNextKr: '여기서 읽은 성장 방향을 들고 ②물가로 — "성장 둔화인데 물가는 같이 식나, 끈적한가(스태그 위험)". 성장×물가 조합이 ③국면 사분면 입력이 된다.',
		honestyKr: '침체 음영은 US NBER만(KR 공식 dating 없음). CLI·CSI는 pt-level(수준·전환점으로), 나머지는 이미 YoY. UNRATE는 %level·역방향. KR 고용 시계열 없음 — 한미 노동 직접비교 불가.'
	},
	{
		key: 'inflation', order: 2,
		titleKr: '물가 — 오르나 내리나, 어디서 시작되나', titleEn: 'Inflation — rising or falling, and where it starts',
		questionKr: '물가 압력은 가속인가 감속인가, 넓게 퍼졌나 일부에 갇혔나, 그리고 생산자물가(PPI)가 소비자물가(CPI)를 앞서 끄나?',
		questionEn: 'Is inflation accelerating or cooling, broad or narrow, and is PPI momentum leading CPI?',
		seriesIds: ['CPI', 'CPIAUCSL', 'CPILFESL', 'PCEPI', 'T10YIE', 'PPI_MFG', 'PPI_CHEM', 'PPI_STEEL', 'DCOILWTICO'],
		overlays: [
			{ a: 'PPI_MFG', b: 'CPI', tests: '제조업 PPI의 변곡이 CPI보다 몇 개월 앞서나? PPI가 먼저 꺾였다면 CPI는 아직 반영 안 했나 — 어느 쪽을 선행 단서로 볼지 점검.' },
			{ a: 'DCOILWTICO', b: 'PPI_CHEM', tests: '유가(z)의 등락이 화학 PPI로 얼마나·몇 개월 시차로 전가되나? 최근 유가가 아직 화학 PPI에 도달 안 했다면 그 시차를 어떻게 읽나.' },
			{ a: 'T10YIE', b: 'CPIAUCSL', tests: '시장 기대인플레(z)가 실제 미 CPI를 앞서나 뒤따르나? 벌어졌다면 어느 쪽이 먼저 돌았나.' }
		],
		divergences: [
			{ a: 'CPIAUCSL', b: 'CPILFESL', why: '헤드라인 vs 근원 CPI가 벌어지면 에너지·식품 주도(일시적)인지, 좁혀지면 근원의 끈적한 압력인지.' },
			{ a: 'PPI_MFG', b: 'CPI', why: '생산자물가와 소비자물가가 벌어지면 기업 마진(전가 여력) 압박/완화 방향 신호.' }
		],
		insightKr: '세 가지를 스스로 확인하라. (1) 방향: 가속 지표가 감속보다 많나 — 넓게 오르나 식나. (2) 폭: PPI 업종이 함께 가속하면 광범위, 한둘이면 국지적(breadth 개수로). (3) 선후: PPI→CPI 선행이 지금도 성립하나. 헤드라인 vs 근원으로 "일시적이냐 끈적하냐", 기대 vs 실현으로 "기대가 앞서나" — 결론은 네가.',
		insightEn: 'Check three: (1) direction — more accelerating or cooling? (2) breadth — PPI subsectors together = broad, one or two = localized. (3) lead-lag — does PPI→CPI still hold? Headline vs core = transitory or sticky; breakeven vs realized = do expectations lead. You decide.',
		feedsNextKr: '물가의 방향·폭·선행성을 들고 ③국면(합성)으로 — ①성장 방향과 겹쳐 어느 사분면(리플레/골디락스/스태그/디플)인지. PPI 선행이 다음 전환을 예고하나.',
		honestyKr: '대부분(CPI·PPI_*)은 이미 YoY — 가속/감속은 YoY의 추가변화. DCOILWTICO($)·T10YIE(%)는 레벨이라 YoY와 동축 겹칠 땐 z로만. PPI 업종은 KR(ECOS)만 — PPI→CPI 선행은 KR 쌍이 핵심. ⚠ KR PPI·CPI 월간·forward-fill 계단(일봉 시차 ≠ 실제 선행개월).'
	},
	{
		key: 'regime', order: 3, synthesis: true,
		titleKr: '국면 — 성장 × 물가 합성', titleEn: 'Regime — growth × inflation synthesis',
		questionKr: '①성장 방향 × ②물가 방향을 겹치면 지금 어느 사분면(골디락스·리플레이션·스태그플레이션·디플레이션)으로 *향하나*? 한국과 미국은 같은 칸인가, 엇갈리나?',
		questionEn: 'Overlaying growth × inflation direction, which quadrant is it heading toward — and are KR and US in the same cell or diverging?',
		seriesIds: ['CLI', 'CPI', 'INDPRO', 'CPIAUCSL'],
		overlays: [
			{ a: 'CLI', b: 'CPI', tests: '한국 성장 모멘텀(CLI)과 물가 모멘텀(CPI)을 z로 겹쳐 — 같이 가속하나 갈라지나? 만드는 사분면 칸이 지난 분기와 같나, 옆 칸으로 넘어가나?' },
			{ a: 'CLI', b: 'INDPRO', tests: '한국 선행(CLI)과 미국 실물생산(INDPRO) 성장 모멘텀이 같은 방향인가 — 한·미 동조인가 디커플링인가.' },
			{ a: 'CPI', b: 'CPIAUCSL', tests: '한국 물가(CPI)와 미국 물가(CPIAUCSL)가 같이 가나 — 사분면 물가 축이 어느 쪽에서 먼저 움직이나.' }
		],
		divergences: [
			{ a: 'CLI', b: 'CPI', why: '성장 축과 물가 축이 함께 가다 한쪽만 틀면 사분면이 대각 이동(리플레→스태그 등) — 국면 전환 핵심 신호(현재 z-격차).' },
			{ a: 'CLI', b: 'INDPRO', why: '한국 선행 성장과 미국 실물 성장이 반대로 벌어지면 한·미 국면 엇갈림 — "같은 국면" 손쉬운 결론을 깨는 신호.' }
		],
		insightKr: '"좋다/나쁘다" 판정 말고 *화살표*를 보라: 성장·물가 축이 각각 가속/감속인지, 그 조합이 어느 사분면이며 지난 분기 대비 칸을 넘어가는 중(전환)인지. 한국(CLI·CPI)과 미국(INDPRO·CPIAUCSL)이 같은 칸인지, 한쪽이 먼저 이동 중인지 — divergence가 "한·미 같은 국면" 결론을 깨는지 확인. 한 점이 아니라 "어디서 와서 어디로"가 다음(정책) 질문을 정한다.',
		insightEn: 'Read the arrow, not a single point: are growth and inflation each accelerating or decelerating, which quadrant, and is it crossing into a new cell (transition)? Are KR and US in the same cell or is one migrating? "Where it came from and where it heads" sets the policy question.',
		feedsNextKr: '사분면 방향과 한·미 정렬/엇갈림을 들고 ④정책으로 — 성장↓물가↑(스태그 쪽)이면 "기준금리가 이 국면에 정합인가 뒤처지나", 리플레/골디락스면 "정책이 완화로 돌았나". 국면 좌표가 정책 정합/지연의 기준점.',
		honestyKr: '사분면은 성장·물가 *모멘텀 z좌표*이지 침체/호황 판정 아님(quadOf=부호 분류). ⛔ 자산 비중·추천 비표시(좌패널 자산표와 별개). KR 성장=CLI(레벨→z), 미국=INDPRO(YoY)로 성격이 달라 한·미는 동조/선후행 관찰용. probit·수익률곡선 국면확률은 US 전용이라 제외.'
	},
	{
		key: 'policy', order: 4,
		titleKr: '정책 — 중앙은행은 이 국면에 맞게 움직이나', titleEn: 'Policy — moving with the regime?',
		questionKr: '성장·물가·국면을 들고, 정책금리가 그 압력에 맞게(혹은 뒤처져) 움직이나? 인플레를 뺀 "실질" 정책 강도는 완화적인가 긴축적인가?',
		questionEn: 'Are policy rates moving with (or lagging) the pressure? Is the real stance (net of inflation) easy or tight?',
		seriesIds: ['BASE_RATE', 'FEDFUNDS', 'DGS2', 'CPI', 'CPIAUCSL'],
		overlays: [
			{ a: 'FEDFUNDS', b: 'CPIAUCSL', tests: '정책금리가 인플레 위/아래 어디고 간격이 좁나 벌어지나 — 인플레가 먼저 꺾인 뒤 정책이 따라오나(behind the curve)?' },
			{ a: 'BASE_RATE', b: 'CPI', tests: '한은 기준금리 − CPI = 실질 정책금리가 +인가 −인가, 부호가 최근 어디로 — 인플레 대비 조이나 푸나?' },
			{ a: 'DGS2', b: 'FEDFUNDS', tests: '2년물이 정책금리보다 높나 낮나 — 시장이 담은 정책 경로(추가 인상 vs 인하)가 실제와 같은 쪽인가.' }
		],
		divergences: [
			{ a: 'DGS2', b: 'FEDFUNDS', why: '시장금리(2Y)와 정책금리가 벌어지면 시장이 피벗을 먼저 반영하기 시작한 신호일 수 있어 어느 쪽이 앞서나.' },
			{ a: 'FEDFUNDS', b: 'BASE_RATE', why: '한·미 정책금리가 반대 방향이면 정책 디커플링 — 환율·자본흐름 압력.' }
		],
		insightKr: '세 질문을 짚어라. (1) 정책금리가 인플레 위인가 아래인가 — 실질금리 부호·방향? (2) 인플레가 꺾인 뒤에도 정책이 머물러 "뒤처져" 있나, 앞서 움직였나? (3) 시장(DGS2)과 한·미 정책 방향이 같나 갈라지나? ②물가 방향·③국면과 나란히 놓고 "정책이 이 국면에 맞나"를 스스로.',
		insightEn: 'Three questions: (1) is the rate above or below inflation — real-rate sign/direction? (2) is policy behind the curve or ahead? (3) do market path (DGS2) and KR/US policy align or diverge? Place next to inflation direction and regime, then judge fit.',
		feedsNextKr: '실질금리 부호·정책 방향·시장-정책 간격을 들고 ⑤금융여건으로 — "정책 스탠스가 실제 여건(스프레드·금융상황)으로 전달되나, 따로 노나".',
		honestyKr: '실질금리는 명목(%level) − 인플레(YoY) 근사 — 단위 비동질, 추세 부호 판독용(별도 실질금리 시계열 없음). DGS2−FEDFUNDS 간격은 시장 경로 시사일 뿐 예측 아님. KR은 BASE_RATE·CPI만(KR 단기 시장금리 없음) — 시장-정책 간격은 US만.'
	},
	{
		key: 'conditions', order: 5,
		titleKr: '금융여건·신용 — 돈이 도나 막히나', titleEn: 'Financial conditions & credit — flowing or jammed?',
		questionKr: '정책금리 위에서 시장·신용에 전달된 여건은 완화되나 조여지나? 수익률곡선·스프레드는 침체 선행으로 알려졌는데, 지금 신호들이 같은 방향인가 엇갈리나?',
		questionEn: 'On top of the policy rate, are transmitted conditions loosening or tightening? Are the curve/spread signals aligned or diverging?',
		seriesIds: ['T10Y3M', 'T10Y2Y', 'BAMLH0A0HYM2', 'BAA10Y', 'NFCI', 'VIXCLS', 'M2'],
		overlays: [
			{ a: 'T10Y3M', b: 'BAMLH0A0HYM2', tests: '곡선이 먼저 평탄·역전된 뒤 하이일드 스프레드가 벌어지나, 같이 움직이나? 선행(곡선)과 실현 스트레스(신용)의 시차를 눈으로.' },
			{ a: 'NFCI', b: 'BAMLH0A0HYM2', tests: '종합 금융상황(NFCI) 긴축이 신용스프레드 확대와 동행하나? NFCI가 먼저 조이는데 HY가 잠잠하면 어느 쪽이 아직 반영 안 됐나.' },
			{ a: 'T10Y3M', b: 'T10Y2Y', tests: '두 곡선 측정(10Y-3M vs 10Y-2Y)이 같이 0선을 넘나, 한쪽만 역전인가 — 어느 구간(단기·중기)이 신호를 끄나.' }
		],
		divergences: [
			{ a: 'VIXCLS', b: 'BAMLH0A0HYM2', why: '주식 변동성(VIX)과 신용스프레드는 보통 같이 움직인다. 한쪽만 벌어지면 위험이 한 자산군에 국한인지 전이 전 단계인지.' },
			{ a: 'BAMLH0A0HYM2', b: 'BAA10Y', why: '하이일드(투기)와 BAA(투자등급)가 벌어지면 스트레스가 저신용에 집중인지 등급 전반으로 번지는지.' }
		],
		insightKr: '판정 아니라 신호 정합성. (1) 방향집계로 긴축/완화 어느 쪽이 다수인가. (2) 곡선이 0선에 얼마나 가깝나/역전인가 — 단 역전은 "시점"이 아니라 "선행 신호", 신용스프레드(실제 조달비용)가 잠잠한지 벌어지는지 함께. (3) 곡선→신용→변동성 전이가 어디까지 왔나 겹쳐보기로. 같은 방향이면 신호 강화, 엇갈리면 "뭐가 아직 반영 안 됐나"를 다음으로.',
		insightEn: 'Signal consistency, not verdict. (1) breadth — tightening or easing majority? (2) how inverted is the curve — but inversion is a lead, not timing; read with credit spreads. (3) trace curve→credit→volatility transmission via overlays. Aligned = reinforced; diverging = "what isn\'t priced yet".',
		feedsNextKr: '"여건이 조이나 풀리나 + 신용/변동성에 반영된 위험"을 들고 ⑥시장으로 — 곡선·신용의 선행 신호가 주가·달러·원자재에 이미 반영됐나, 시장이 여건과 엇갈리나.',
		honestyKr: '곡선·신용스프레드·NFCI·VIX는 US(FRED) 전용 — KR은 동일 지표 없음(BASE_RATE·M2로 통화여건 일부만 보조). 침체 음영은 US NBER만. 곡선 역전의 침체 선행은 통계 경향일 뿐 시점·확정 예측 아님(예측 컬럼 없음).'
	},
	{
		key: 'markets', order: 6,
		titleKr: '시장 — 가격은 뭘 반영했나, 거시 진단과 맞나', titleEn: 'Markets — what prices priced in, and do they agree?',
		questionKr: '①~⑤에서 읽은 거시 그림을 시장 가격(주식·변동성·달러·원자재)이 같은 방향으로 반영하나, 어긋나나? 어긋나면 시장이 아직 못 본 기회인가, 거시가 놓친 위험을 시장이 먼저 본 것인가?',
		questionEn: 'Do prices reflect the macro read from stations 1–5, or clash? If they clash — an opportunity unpriced, or a risk the macro lens missed?',
		seriesIds: ['SP500', 'NASDAQCOM', 'VIXCLS', 'DTWEXBGS', 'USDKRW', 'DCOILWTICO', 'PCOPPUSDM', 'BAMLH0A0HYM2'],
		overlays: [
			{ a: 'SP500', b: 'VIXCLS', tests: '주가와 공포지수(VIX)를 z로 겹쳐 평소 역동행(주가↑·VIX↓)이 유지되나? 주가 신고가인데 VIX가 안 내리고 들리면 가격 신호가 갈라지는 건 아닌지.' },
			{ a: 'PCOPPUSDM', b: 'DCOILWTICO', tests: '구리·유가를 겹쳐 둘 다 ①성장의 수출·산업생산 가속과 같은 방향인가? 구리(수요민감)는 오르는데 유가가 못 따르면 어느 쪽이 ①진단과 맞나.' },
			{ a: 'DTWEXBGS', b: 'USDKRW', tests: '달러지수와 원/달러를 겹쳐 — 원화 약세가 글로벌 달러 강세 일부인가, 달러지수는 잠잠한데 원화만 따로(한국 고유)인가.' }
		],
		divergences: [
			{ a: 'SP500', b: 'BAMLH0A0HYM2', why: '주식과 하이일드는 평소 반대(주가↑·스프레드↓). 동시에 오르며 벌어지면 ⑤신용 경고가 주가에 아직 안 들어온 건지.' },
			{ a: 'PCOPPUSDM', b: 'SP500', why: '구리(실물 수요)와 주가는 보통 동행. 주가는 오르는데 구리가 빠지면 주가가 ①성장보다 ④정책(유동성)에 기댄 건 아닌지.' },
			{ a: 'DTWEXBGS', b: 'SP500', why: '달러 강세와 미 주식 동반 상승은 안전선호·위험선호 공존의 모순 — 어느 자산이 ③국면과 일치하나.' }
		],
		insightKr: '"사라/팔아"가 아니라 *내 거시 진단과 시장 가격의 합치/괴리 지도*. (1) ①~⑤ 방향을 한 줄로 적고 시장 8개를 하나씩 대조. (2) 정합이면 시장이 이미 반영 — 가격에 새 정보가 얼마나 남았나. (3) 괴리면 둘 중 하나 — 시장이 *아직 안 본 것*(기회/위험)인가, *먼저 본 것*(거시가 놓침)인가. (4) 가장 크게 벌어진 발산 쌍이 괴리의 진앙 — 그 쌍을 ①~⑤ 중 어느 스테이션이 설명하나 되짚어라.',
		insightEn: 'Not "buy/sell" but a map of agreement/clash between your macro read and prices. (1) write the 1–5 read, check each of 8 prices. (2) agree → already priced. (3) clash → unpriced (opportunity/risk) or seen-first (lens missed). (4) the widest divergence pair is the epicenter — trace it back to a station.',
		feedsNextKr: 'top-down 순환의 닫는 고리 — 발견한 괴리 쌍을 설명하는 앞 스테이션으로 되돌아가라(신용 발산→⑤, 성장-가격 괴리→①, 달러-원화→④). 개별 종목으로 내려갈 땐 이 시장 국면(risk-on/off·달러·유가·구리)을 그 종목 전제로.',
		honestyKr: '침체 음영은 US만(USDKRW엔 음영 기준 없음). 빈도 상이(구리=월간, 주가·VIX·달러=일간) — z 겹침은 forward-fill 정렬(저빈도 계단 주의). VIX·HY의 "역사적 극단"은 표본 내 상대 위치일 뿐 절대 임계 아님. 상관은 과거 경향 — 인과/지속 보장 아님(평소 동행이 깨지는 것 자체가 관찰 대상).'
	}
];
