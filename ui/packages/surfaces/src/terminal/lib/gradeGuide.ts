// 스캔 등급 설명 다이얼로그용 큐레이션 맵 — ★사람 작성(자동 생성 금지, feedback_no_docstring_auto_sweep 정합).
// 각 등급 축이 *무엇을* 보는지(what) + 등급이 매겨지는 근거(basis). 사다리 자체는 engine.ts GRADE_SCALE 가 SSOT.
// 금지: 인과 단정("…면 주가 상승")·매수/매도 신호·"좋은 주식". 등급 = fact 아닌 *판정*이므로 근거+기준만 기술한다.
//
// 키 = co.grades[].key (engine.ts:513-521): prof·growth·gov·qual·liq·audit·stab.
// radar(6축)·analysis.tracks(5축)·grades(7축)는 서로 다른 축 집합이라 *섞지 않고* 각자 라벨한다(오독 방지).

export interface GradeGuideEntry {
	kr: { what: string; basis: string };
	en: { what: string; basis: string };
}

export const GRADE_GUIDE: Record<string, GradeGuideEntry> = {
	prof: {
		kr: { what: '돈을 버는 힘 — 영업이익률·ROE 수준', basis: '최근 영업이익률과 자기자본이익률을 등급 사다리에 대응(공시 재무 기준)' },
		en: { what: 'Earning power — OP margin & ROE level', basis: 'Latest OP margin and ROE mapped to the ladder (from filed financials)' }
	},
	growth: {
		kr: { what: '외형 성장 — 매출 추세', basis: '다년 매출 증가율(CAGR/YoY)을 사다리에 대응' },
		en: { what: 'Top-line growth — revenue trajectory', basis: 'Multi-year revenue growth (CAGR/YoY) mapped to the ladder' }
	},
	gov: {
		kr: { what: '거버넌스 — 지배구조·공시 충실도', basis: 'scan ecosystem 거버넌스 신호를 A~E 5단으로 대응' },
		en: { what: 'Governance — ownership & disclosure quality', basis: 'Scan ecosystem governance signals mapped to A–E' }
	},
	qual: {
		kr: { what: '이익의 질 — 이익이 현금·본업으로 뒷받침되는 정도', basis: '발생액·현금화·일회성 비중 신호를 사다리에 대응' },
		en: { what: 'Earnings quality — how cash- and core-backed profit is', basis: 'Accrual / cash-conversion / one-off signals mapped to the ladder' }
	},
	liq: {
		kr: { what: '단기 지급 능력 — 유동성', basis: '유동비율 등 단기 상환 여력 신호를 사다리에 대응' },
		en: { what: 'Short-term solvency — liquidity', basis: 'Current ratio and short-term coverage signals mapped to the ladder' }
	},
	audit: {
		kr: { what: '감사 위험 — 회계·감사 측면 경고 신호', basis: '감사의견·계속기업 등 신호를 3단(저/중/고위험)으로 대응. ※3단이라 좌측 스파이더에선 제외' },
		en: { what: 'Audit risk — accounting/audit warning signals', basis: 'Audit-opinion / going-concern signals mapped to 3 tiers. Note: excluded from the radar (only 3 tiers)' }
	},
	stab: {
		kr: { what: '경영 안정 — 재무 안정성 종합', basis: '부채·자본·변동성 신호를 6단으로 대응' },
		en: { what: 'Management stability — overall financial stability', basis: 'Leverage / capital / volatility signals mapped to 6 tiers' }
	}
};
