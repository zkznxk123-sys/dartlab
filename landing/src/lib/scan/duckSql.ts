/**
 * Scan Studio — DuckDB-WASM 으로 HF parquet 직접 query.
 *
 * 3 source 별 lazy 로드:
 *   - prices  : krx/prices/raw-{year}.parquet + raw-{year-1}.parquet UNION → 1Y window
 *               currentPrice/marketCap/ma20/high-low/return1m/3m/1y/volatility1y/spark
 *   - valuation: dart/scan/valuation.parquet → per/pbr/dividendYield/marketCap (Naver)
 *   - changes  : dart/scan/changes.parquet → 1Y numeric/structural/total 변경 카운트
 *
 * 책임: Map<stockCode|ISU_CD, …> 반환. 호출자가 ScanNode 와 join.
 *
 * 주: PR-B 단계는 현 `/screener` 의 검증된 SQL 를 그대로 lift. 5Y monthly cell hover
 * 시계열은 PR-D 디테일 패널에서. PR-B 는 60일 sparkline 만 활용.
 */

import { loadDartDb, type DartDb } from '$lib/data/duckdb';

export type DbState = 'idle' | 'loading' | 'ready' | 'unsupported' | 'error';

export interface PriceMetrics {
	currentPrice: number | null;
	marketCap: number | null;
	ma20: number | null;
	high60: number | null;
	low60: number | null;
	week52High: number | null;
	week52Low: number | null;
	volumeAvg30d: number | null;
	volatility1y: number | null;
	return1m: number | null;
	return3m: number | null;
	return1y: number | null;
	/** 60거래일 종가 (4일 다운샘플 ≈ 15포인트). cell sparkline + 1Y 컬럼 sparkline 동시 사용 */
	spark: number[];
}

export interface ValuationMetrics {
	per: number | null;
	pbr: number | null;
	dividendYield: number | null;
	marketCap: number | null;
}

export interface ChangeMetrics {
	numericChanges1y: number;
	structuralChanges1y: number;
	totalChanges1y: number;
	recentChangeYear: number | null;
}

const num = (v: unknown): number | null => {
	if (v === null || v === undefined) return null;
	const n = Number(v);
	return Number.isFinite(n) ? n : null;
};

const pctReturn = (curr: number | null, past: number | null): number | null => {
	if (curr == null || past == null || past === 0) return null;
	return (curr / past - 1) * 100;
};

/** ISU_CD → stockCode (A005930 → 005930). */
export function isuCdToStockCode(isuCd: string): string {
	if (!isuCd) return '';
	return isuCd.startsWith('A') ? isuCd.slice(1) : isuCd;
}

/** DuckDB 인스턴스화 + 1Y window prices view 등록. 결과는 stockCode 기반 Map. */
export async function loadPriceMetrics(): Promise<{
	db: DartDb | null;
	state: DbState;
	metrics: Map<string, PriceMetrics>;
	error?: string;
}> {
	console.info('[scan] DuckDB 로드 시작 — HF KRX parquet');
	const t0 = performance.now();
	let db: DartDb | null = null;
	try {
		db = await loadDartDb();
	} catch (err) {
		const message = err instanceof Error ? err.message : String(err);
		console.error('[scan] DuckDB 인스턴스화 예외', err);
		return { db: null, state: 'error', metrics: new Map(), error: message };
	}
	if (!db) {
		console.warn('[scan] DuckDB 사용 불가 (iOS Safari 또는 환경 미지원) → 가격·시총 컬럼 비활성');
		return { db: null, state: 'unsupported', metrics: new Map() };
	}

	const year = new Date().getFullYear();
	try {
		await db.registerHfParquet('krxPricesCurr', `krx/prices/raw-${year}.parquet`);
		try {
			await db.registerHfParquet('krxPricesPrev', `krx/prices/raw-${year - 1}.parquet`);
			await db.query(
				`CREATE OR REPLACE VIEW krxPrices AS SELECT * FROM krxPricesCurr UNION ALL SELECT * FROM krxPricesPrev`
			);
		} catch (errPrev) {
			console.warn(`[scan] 직전 연도 parquet 등록 실패 (현재 연도만 사용)`, errPrev);
			await db.query(`CREATE OR REPLACE VIEW krxPrices AS SELECT * FROM krxPricesCurr`);
		}

		const rows = await db.query<{
			ISU_CD: string;
			currentPrice: number | null;
			marketCap: number | null;
			ma20: number | null;
			high60: number | null;
			low60: number | null;
			week52High: number | null;
			week52Low: number | null;
			volumeAvg30d: number | null;
			volatility1y: number | null;
			prev21: number | null;
			prev63: number | null;
			prev252: number | null;
			spark: number[] | null;
		}>(`
			WITH ranked AS (
				SELECT
					ISU_CD,
					BAS_DD,
					CAST(TDD_CLSPRC AS DOUBLE) AS close,
					CAST(TDD_HGPRC AS DOUBLE) AS high,
					CAST(TDD_LWPRC AS DOUBLE) AS low,
					CAST(ACC_TRDVOL AS DOUBLE) AS volume,
					CAST(MKTCAP AS DOUBLE) AS mktcap,
					ROW_NUMBER() OVER (PARTITION BY ISU_CD ORDER BY BAS_DD DESC) AS rn
				FROM krxPrices
			),
			last252 AS (SELECT * FROM ranked WHERE rn <= 252),
			latest AS (SELECT ISU_CD, close AS currentPrice, mktcap AS marketCap FROM last252 WHERE rn = 1),
			ma20 AS (SELECT ISU_CD, AVG(close) AS ma20 FROM last252 WHERE rn <= 20 GROUP BY ISU_CD),
			bounds60 AS (
				SELECT ISU_CD, MAX(high) AS high60, MIN(low) AS low60
				FROM last252 WHERE rn <= 60 GROUP BY ISU_CD
			),
			bounds252 AS (
				SELECT ISU_CD, MAX(high) AS week52High, MIN(low) AS week52Low
				FROM last252 GROUP BY ISU_CD
			),
			volavg30 AS (
				SELECT ISU_CD, AVG(volume) AS volumeAvg30d
				FROM last252 WHERE rn <= 30 GROUP BY ISU_CD
			),
			prev21 AS (SELECT ISU_CD, close AS prev21 FROM last252 WHERE rn = 21),
			prev63 AS (SELECT ISU_CD, close AS prev63 FROM last252 WHERE rn = 63),
			prev252 AS (SELECT ISU_CD, close AS prev252 FROM last252 WHERE rn = 252),
			logret AS (
				SELECT ISU_CD,
					CASE WHEN close > 0 AND LAG(close) OVER (PARTITION BY ISU_CD ORDER BY BAS_DD) > 0
						THEN LN(close / LAG(close) OVER (PARTITION BY ISU_CD ORDER BY BAS_DD))
						ELSE NULL END AS lnret
				FROM last252
			),
			vol AS (
				SELECT ISU_CD, STDDEV_SAMP(lnret) * SQRT(252) * 100 AS volatility1y
				FROM logret WHERE lnret IS NOT NULL GROUP BY ISU_CD
			),
			spark AS (
				SELECT ISU_CD, ARRAY_AGG(close ORDER BY BAS_DD ASC) AS spark
				FROM last252 WHERE rn <= 60 AND rn % 4 = 0
				GROUP BY ISU_CD
			)
			SELECT
				l.ISU_CD,
				l.currentPrice, l.marketCap,
				m.ma20,
				b60.high60, b60.low60,
				b252.week52High, b252.week52Low,
				va.volumeAvg30d,
				v.volatility1y,
				p21.prev21, p63.prev63, p252.prev252,
				s.spark
			FROM latest l
			LEFT JOIN ma20 m USING (ISU_CD)
			LEFT JOIN bounds60 b60 USING (ISU_CD)
			LEFT JOIN bounds252 b252 USING (ISU_CD)
			LEFT JOIN volavg30 va USING (ISU_CD)
			LEFT JOIN vol v USING (ISU_CD)
			LEFT JOIN prev21 p21 USING (ISU_CD)
			LEFT JOIN prev63 p63 USING (ISU_CD)
			LEFT JOIN prev252 p252 USING (ISU_CD)
			LEFT JOIN spark s USING (ISU_CD)
		`);

		const map = new Map<string, PriceMetrics>();
		for (const r of rows) {
			const code = isuCdToStockCode(r.ISU_CD);
			if (!code) continue;
			const currentPrice = num(r.currentPrice);
			const sparkArr = Array.isArray(r.spark)
				? r.spark.map((v) => Number(v)).filter((v) => Number.isFinite(v))
				: [];
			map.set(code, {
				currentPrice,
				marketCap: num(r.marketCap),
				ma20: num(r.ma20),
				high60: num(r.high60),
				low60: num(r.low60),
				week52High: num(r.week52High),
				week52Low: num(r.week52Low),
				volumeAvg30d: num(r.volumeAvg30d),
				volatility1y: num(r.volatility1y),
				return1m: pctReturn(currentPrice, num(r.prev21)),
				return3m: pctReturn(currentPrice, num(r.prev63)),
				return1y: pctReturn(currentPrice, num(r.prev252)),
				spark: sparkArr
			});
		}
		console.info(
			`[scan] ✅ KRX 가격 메트릭 — ${map.size}사 (${(performance.now() - t0).toFixed(0)}ms)`
		);
		return { db, state: 'ready', metrics: map };
	} catch (err) {
		const message = err instanceof Error ? err.message : String(err);
		console.error('[scan] ❌ DuckDB SQL 실패', err);
		console.info(
			'[scan] HF parquet URL: https://huggingface.co/datasets/eddmpython/dartlab-data/resolve/main/krx/prices/raw-' +
				new Date().getFullYear() +
				'.parquet'
		);
		return { db, state: 'error', metrics: new Map(), error: message };
	}
}

/** valuation.parquet → PER/PBR/배당수익률/시총 (Naver, 매일 KST 04:00 갱신). */
export async function loadValuation(db: DartDb): Promise<Map<string, ValuationMetrics>> {
	const t0 = performance.now();
	try {
		await db.registerHfParquet('valuation', 'dart/scan/valuation.parquet');
		const rows = await db.query<{
			stockCode: string;
			per: number | null;
			pbr: number | null;
			dividendYield: number | null;
			marketCap: number | null;
		}>(`
			SELECT
				stockCode,
				CAST(per AS DOUBLE) AS per,
				CAST(pbr AS DOUBLE) AS pbr,
				CAST(dividendYield AS DOUBLE) AS dividendYield,
				CAST(marketCap AS DOUBLE) AS marketCap
			FROM valuation
		`);
		const map = new Map<string, ValuationMetrics>();
		for (const r of rows) {
			if (!r.stockCode) continue;
			map.set(r.stockCode, {
				per: num(r.per),
				pbr: num(r.pbr),
				dividendYield: num(r.dividendYield),
				marketCap: num(r.marketCap)
			});
		}
		console.info(
			`[scan] ✅ valuation — ${map.size}사 (${(performance.now() - t0).toFixed(0)}ms)`
		);
		return map;
	} catch (err) {
		console.warn('[scan] valuation.parquet 로드 실패', err);
		return new Map();
	}
}

/** changes.parquet → 1Y 공시 변경 카운트 + 최근 변경 연도. */
export async function loadChanges(db: DartDb): Promise<Map<string, ChangeMetrics>> {
	const t0 = performance.now();
	try {
		await db.registerHfParquet('changes', 'dart/scan/changes.parquet');
		const currentYear = new Date().getFullYear();
		const lastYear = currentYear - 1;
		const rows = await db.query<{
			stockCode: string;
			numericChanges1y: number;
			structuralChanges1y: number;
			totalChanges1y: number;
			recentChangeYear: number | null;
		}>(`
			SELECT
				stockCode,
				COUNT(*) FILTER (WHERE changeType = 'numeric' AND CAST(toPeriod AS INTEGER) IN (${currentYear}, ${lastYear})) AS numericChanges1y,
				COUNT(*) FILTER (WHERE changeType = 'structural' AND CAST(toPeriod AS INTEGER) IN (${currentYear}, ${lastYear})) AS structuralChanges1y,
				COUNT(*) FILTER (WHERE CAST(toPeriod AS INTEGER) IN (${currentYear}, ${lastYear})) AS totalChanges1y,
				MAX(CAST(toPeriod AS INTEGER)) AS recentChangeYear
			FROM changes
			WHERE stockCode IS NOT NULL
			GROUP BY stockCode
		`);
		const map = new Map<string, ChangeMetrics>();
		for (const r of rows) {
			map.set(r.stockCode, {
				numericChanges1y: Number(r.numericChanges1y) || 0,
				structuralChanges1y: Number(r.structuralChanges1y) || 0,
				totalChanges1y: Number(r.totalChanges1y) || 0,
				recentChangeYear: r.recentChangeYear != null ? Number(r.recentChangeYear) : null
			});
		}
		console.info(
			`[scan] ✅ changes — ${map.size}사 (${(performance.now() - t0).toFixed(0)}ms)`
		);
		return map;
	} catch (err) {
		console.warn('[scan] changes.parquet 로드 실패', err);
		return new Map();
	}
}

/** 한 회사의 60거래일 종가 (cell hover sparkline). prices map 에 이미 있어 빠른 lookup. */
export function getSparkForCompany(
	priceMap: Map<string, PriceMetrics>,
	stockCode: string
): number[] {
	return priceMap.get(stockCode)?.spark ?? [];
}

// ── Per-company loaders (Detail 패널용) ───────────────

export interface FinanceYear {
	year: number;
	revenue: number | null;
	opProfit: number | null;
	netIncome: number | null;
	assets: number | null;
	liabilities: number | null;
}

export interface CompanyChange {
	fromPeriod: string;
	toPeriod: string;
	sectionTitle: string;
	changeType: string;
	preview: string | null;
}

/** 한 회사의 5Y 연간 재무 (5 계정). finance-lite.parquet long-form → JS pivot. */
export async function loadFinanceTimeseries(
	db: DartDb,
	stockCode: string
): Promise<FinanceYear[]> {
	try {
		await db.registerHfParquet('financeLite', 'dart/scan/finance-lite.parquet');
		// long-form raw — JS 에서 pivot. 5 계정만 추출.
		const rows = await db.query<{
			bsns_year: number;
			reprt_nm: string;
			account_id: string;
			thstrm_amount: number;
		}>(`
			SELECT
				CAST(bsns_year AS INTEGER) AS bsns_year,
				reprt_nm,
				account_id,
				CAST(thstrm_amount AS DOUBLE) AS thstrm_amount
			FROM financeLite
			WHERE stockCode = '${stockCode}'
			  AND account_id IN ('sales', 'operating_profit', 'net_income', 'assets', 'liabilities')
			  AND reprt_nm IN ('연간', '4분기', '사업보고서')
		`);

		// Pivot: year → { revenue, opProfit, netIncome, assets, liabilities }
		const byYear = new Map<number, FinanceYear>();
		for (const r of rows) {
			const y = Number(r.bsns_year);
			if (!Number.isFinite(y)) continue;
			let rec = byYear.get(y);
			if (!rec) {
				rec = {
					year: y,
					revenue: null,
					opProfit: null,
					netIncome: null,
					assets: null,
					liabilities: null
				};
				byYear.set(y, rec);
			}
			const v = num(r.thstrm_amount);
			if (v == null) continue;
			switch (r.account_id) {
				case 'sales':
					rec.revenue = v;
					break;
				case 'operating_profit':
					rec.opProfit = v;
					break;
				case 'net_income':
					rec.netIncome = v;
					break;
				case 'assets':
					rec.assets = v;
					break;
				case 'liabilities':
					rec.liabilities = v;
					break;
			}
		}
		return Array.from(byYear.values()).sort((a, b) => a.year - b.year);
	} catch (err) {
		console.warn('[scan] finance-lite per-company 로드 실패', err);
		return [];
	}
}

/** 한 회사의 최근 공시 변경 N 건. */
export async function loadCompanyChanges(
	db: DartDb,
	stockCode: string,
	limit = 3
): Promise<CompanyChange[]> {
	try {
		await db.registerHfParquet('changes', 'dart/scan/changes.parquet');
		const rows = await db.query<CompanyChange>(`
			SELECT
				fromPeriod,
				toPeriod,
				sectionTitle,
				changeType,
				preview
			FROM changes
			WHERE stockCode = '${stockCode}'
			ORDER BY toPeriod DESC, sectionTitle
			LIMIT ${limit}
		`);
		return rows;
	} catch (err) {
		console.warn('[scan] changes per-company 로드 실패', err);
		return [];
	}
}
