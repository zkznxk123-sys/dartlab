// 시장 라우팅 SSOT — 식별자(KR 종목코드 / US 티커·CIK) → 시장 분류 단일 진입점.
//
// 라이브러리(Python) 라우팅은 provider *priority* 기반이라(예: EDGAR canHandle 은 6자리
// 숫자도 True 를 반환하고 dart<edgar priority 로 분기) 프론트가 식별자 *모양*만으로 베끼면
// 6자리 KR 코드(005930)와 6자리 US CIK(Apple=320193)를 못 가른다. 따라서 프론트 규칙은
// **명시 market override 1순위 + 모호 신호**로 비대칭 설계한다.
//
// 이 함수는 산재된 `/^\d{6}$/ ? 'KR' : 'US'`(viewer/dartUrl · finance/annual · compare/targets)
// 를 대체할 정본이다. market 미지정 기본값은 'KR'(무회귀 불변식 — CLAUDE.md).

/** 단일 시장 리터럴 — indexPort/macro 의 'KR'|'US' 와 동형. */
export type Market = 'KR' | 'US';

/** resolveMarket 결과 — 시장 + 이중키(KR=code · US=ticker/cik). */
export interface MarketRef {
	market: Market;
	/** KR 6자리 종목코드 (market='KR'). */
	code?: string;
	/** US 티커 (대문자, ticker 입력 시). */
	ticker?: string;
	/** US CIK (숫자 입력 + market='US' override, 또는 비-6자리 숫자 자동판정). zero-pad 는 소비자(edgar/tickers)에서. */
	cik?: string;
	/** 입력이 6자리 숫자라 KR코드 ∩ US CIK 모양 충돌 — 자동판정은 KR 로 떨어뜨림. US CIK 면 {market:'US'} 명시 필요. */
	ambiguous?: boolean;
}

const RE_KR_CODE = /^\d{6}$/;
const RE_NUMERIC = /^\d+$/;
const RE_HAS_ALPHA = /[A-Za-z]/;

/**
 * 식별자를 시장으로 분류한다(priority-비대칭, 이중키).
 *
 * 규칙 ① 명시 `opts.market` override 1순위 ② 자동판정: 6자리 숫자→KR(모호 플래그),
 * 비-6자리 숫자→US CIK, 영문 포함→US 티커, 그 외/빈→KR 기본(무회귀).
 *
 * 숫자 CIK 는 6자리 KR 코드와 모양이 충돌하므로(Apple=320193) US 로 라우팅하려면
 * `{market:'US'}` 를 명시해야 한다.
 *
 * @example resolveMarket('005930') // { market:'KR', code:'005930', ambiguous:true }
 * @example resolveMarket('AAPL')   // { market:'US', ticker:'AAPL' }
 * @example resolveMarket('320193', { market:'US' }) // { market:'US', cik:'320193' }
 */
export function resolveMarket(id: string, opts?: { market?: Market }): MarketRef {
	const raw = String(id ?? '').trim();
	const override = opts?.market;

	// ① 명시 market override 1순위
	if (override === 'US') {
		return RE_NUMERIC.test(raw)
			? { market: 'US', cik: raw }
			: { market: 'US', ticker: raw.toUpperCase() };
	}
	if (override === 'KR') {
		return { market: 'KR', code: raw };
	}

	// ② 자동판정 (override 없음)
	if (RE_KR_CODE.test(raw)) {
		// 6자리 숫자 = KR코드 ∩ US CIK 모양 충돌 → 기본 KR, 모호 플래그(US 면 명시 필요).
		return { market: 'KR', code: raw, ambiguous: true };
	}
	if (RE_NUMERIC.test(raw)) {
		// 비-6자리 순수 숫자(예: 10자리 CIK 0000320193) → US CIK (KR 코드는 6자리뿐).
		return { market: 'US', cik: raw };
	}
	if (RE_HAS_ALPHA.test(raw)) {
		return { market: 'US', ticker: raw.toUpperCase() };
	}
	// 빈 문자열·기타 → KR 기본(무회귀).
	return { market: 'KR', code: raw };
}
