// 결정론 답변 조립기 (Tier 0) — 질문 의도 분류 + financeSignals/search/constraint 출력을 인용 달린
// 한국어 완성문으로 조립한다. 0모델·0다운로드·환각 0(숫자는 결정론 SSOT 직접). 공시뷰어 질문의 다수
// (숫자·추세·유무·규모·조건)는 여기서 즉답된다. LLM(Tier 1)은 "왜?/종합/본문해석" 소수에만 opt-in.
//
// 재사용: searchIndex.parseConstraint, diff.FinanceSignal. 새 데이터구조 0 — 기존 출력 필드만 소비.

import { parseConstraint, type SearchHit } from './searchIndex';
import type { FinanceSignal } from './diff';

export type Intent = 'constraint' | 'trend' | 'flip' | 'magnitude' | 'existence' | 'lookup';

export interface ComposeResult {
	intent: Intent;
	answer: string; // 결정론 한국어 답 (lookup 은 안내 문구)
	citedSignal: FinanceSignal | null; // 재무 인용(있으면 칩으로 다이얼로그 연결)
	suggestLlm: boolean; // "왜/종합/해석" → LLM 확장 권유
}

function won(v: number): string {
	const a = Math.abs(v);
	const sign = v < 0 ? '-' : '';
	if (a >= 1e12) return `${sign}${(a / 1e12).toFixed(2)}조`;
	if (a >= 1e8) return `${sign}${(a / 1e8).toFixed(1)}억`;
	if (a >= 1e4) return `${sign}${(a / 1e4).toFixed(0)}만`;
	return `${sign}${a.toLocaleString()}`;
}

// bounded 의도 패턴 — 끝없이 늘면 덕지덕지 신호(searchIndex.parseConstraint 규율과 동일).
const FLIP_RE = /전환|흑자|적자|돌아|마이너스|손실로/;
const TREND_RE = /추세|증감|늘|줄|변화|증가|감소|성장|하락|개선|악화|나아|어때|어떻/;
const MAG_RE = /규모|얼마|금액|총액|몇\s*(억|조|원)|수준|크기|많/;
const EXIST_RE = /있나|있는지|여부|존재|했나|하나요|있습니까|없나|있어/;
const WHY_RE = /왜|이유|원인|때문|배경|어째/;
const SYNTH_RE = /종합|전반|평가|요약|설명|정리|건전|어떤\s*회사|투자/;

export function classifyIntent(q: string, hasConstraint: boolean): Intent {
	if (hasConstraint) return 'constraint';
	if (FLIP_RE.test(q)) return 'flip';
	if (TREND_RE.test(q)) return 'trend';
	if (MAG_RE.test(q)) return 'magnitude';
	if (EXIST_RE.test(q)) return 'existence';
	return 'lookup';
}

// 질문어 → 재무계정 매칭 (label 부분일치 + 경량 동의어). 더 구체(긴) 라벨 우선.
const ACCT_SYN: Record<string, string> = {
	판관비: '판매비와관리비',
	순이익: '당기순이익',
	영업현금: '영업활동현금흐름',
	영업현금흐름: '영업활동현금흐름',
	매출: '매출액',
	차입금: '차입금',
	이익잉여: '이익잉여금'
};
// 라벨 정규화 — DART 괄호 접미사("(손실)"·"(주석)" 등)·공백 제거. "영업이익(손실)" → "영업이익".
function normLabel(s: string): string {
	return s.replace(/\([^)]*\)/g, '').replace(/\s/g, '');
}
function matchSignal(q: string, signals: FinanceSignal[]): FinanceSignal | null {
	const nq = q.replace(/\s/g, '');
	let probe = nq;
	for (const [k, v] of Object.entries(ACCT_SYN)) if (nq.includes(k)) probe += v;
	let best: FinanceSignal | null = null;
	let bestLen = 0;
	for (const s of signals) {
		const label = normLabel(s.label);
		if (label.length >= 2 && probe.includes(label) && label.length > bestLen) {
			best = s;
			bestLen = label.length;
		}
	}
	return best;
}

function dirWord(d: FinanceSignal['direction']): string {
	return d === 'up' ? '증가' : d === 'down' ? '감소' : d === 'flat' ? '거의 변화 없음' : '등락 혼조';
}

export function composeAnswer(q: string, hits: SearchHit[], addedTerms: string[], signals: FinanceSignal[]): ComposeResult {
	const { c } = parseConstraint(q);
	const intent = classifyIntent(q, !!c);
	const suggestLlm = WHY_RE.test(q) || SYNTH_RE.test(q);
	const sig = intent === 'trend' || intent === 'flip' || intent === 'magnitude' ? matchSignal(q, signals) : null;

	// 조건(금액) — search 가 이미 amount 필터+내림차순
	if (intent === 'constraint') {
		if (!hits.length) return { intent, answer: `'${q}' 조건을 만족하는 항목을 색인에서 찾지 못했습니다.`, citedSignal: null, suggestLlm: false };
		const top = hits.slice(0, 4).map((h) => h.block || h.section).filter(Boolean).join(', ');
		return { intent, answer: `조건을 만족하는 항목 ${hits.length}건을 찾았습니다: ${top}${hits.length > 4 ? ' 등' : ''}. 근거를 클릭해 금액을 확인하세요.`, citedSignal: null, suggestLlm: false };
	}

	// 재무 정렬숫자에서 직접 답(가장 정확) — TREND/FLIP/MAGNITUDE
	if (sig) {
		if (intent === 'flip') {
			const ans = sig.signFlip
				? `${sig.label}은(는) ${sig.flipAt} 기간에 ${sig.latest < 0 ? '흑자 → 적자' : '적자 → 흑자'}로 전환됐습니다. 최근값 ${won(sig.latest)}원(${sig.points[0].period}).`
				: `${sig.label}은(는) 조회 기간 내 흑↔적자 전환이 없습니다. 최근값 ${won(sig.latest)}원(${sig.points[0].period}, ${sig.latest < 0 ? '적자' : '흑자'}).`;
			return { intent, answer: ans, citedSignal: sig, suggestLlm };
		}
		if (intent === 'trend') {
			const oldest = sig.points[sig.points.length - 1];
			const pct = sig.deltaPct == null ? '' : `, 직전 대비 ${sig.deltaPct > 0 ? '+' : ''}${Math.round(sig.deltaPct * 100)}%`;
			const streak = (sig.direction === 'up' || sig.direction === 'down') && sig.monotoneRun >= 3 ? ` (${sig.monotoneRun}개 기간 연속 ${dirWord(sig.direction)})` : '';
			return {
				intent,
				answer: `${sig.label}은(는) ${oldest.period}~${sig.points[0].period} ${dirWord(sig.direction)} 추세입니다. 최근값 ${won(sig.latest)}원${pct}${streak}.`,
				citedSignal: sig,
				suggestLlm
			};
		}
		// magnitude
		return {
			intent,
			answer: `${sig.label} 최근 보고값은 ${won(sig.latest)}원입니다(${sig.points[0].period})${sig.prev != null ? `, 직전 ${won(sig.prev)}원` : ''}.`,
			citedSignal: sig,
			suggestLlm
		};
	}

	// 유무
	if (intent === 'existence') {
		if (hits.length) {
			const t = hits[0];
			const syn = addedTerms.length ? `, 동의어 ${addedTerms.slice(0, 3).join('·')} 포함` : '';
			return { intent, answer: `관련 공시가 있습니다 — ${[t.section, t.block].filter(Boolean).join(' > ')}: ${t.snippet}… (관련 ${hits.length}건${syn}).`, citedSignal: null, suggestLlm };
		}
		const syn = addedTerms.length ? ` (동의어 ${addedTerms.slice(0, 3).join('·')}까지 검색)` : '';
		return { intent, answer: `색인에서 '${q}' 관련 항목은 확인되지 않았습니다${syn}. 표 본문은 라벨만 색인되므로 부재를 단정하지 않습니다.`, citedSignal: null, suggestLlm: false };
	}

	// 규모(재무 매칭 실패) → 본문 근거 폴백
	if (intent === 'magnitude' && hits.length) {
		return { intent, answer: `'${q}' 관련 공시 본문 ${hits.length}건을 찾았습니다. 최상위: ${[hits[0].section, hits[0].block].filter(Boolean).join(' > ')}. 근거에서 금액을 확인하세요.`, citedSignal: null, suggestLlm };
	}

	// lookup / 폴백
	if (hits.length) return { intent: 'lookup', answer: `관련 근거 ${hits.length}건을 찾았습니다. 근거를 클릭하면 해당 위치로 이동합니다.`, citedSignal: null, suggestLlm: true };
	return { intent: 'lookup', answer: `'${q}' 관련 근거를 찾지 못했습니다. 다른 표현으로 질문해 보세요.`, citedSignal: null, suggestLlm: false };
}
