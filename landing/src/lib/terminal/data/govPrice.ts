// 공공데이터포털 금융위원회_주식시세정보(공공누리/KOGL, 비상업+출처표시 재배포 가능) 기반 주가 캐시.
// KRX OpenAPI(제3자 제공 금지)와 달리 dartlab(비상업)은 출처표시 조건으로 공개 재배포·표시 합법.
//
// 파이프라인 (프리빌드 아님 — 런타임 온디맨드):
//   1. 읽기 — HF `gov/prices/{code}.json` (공개·토큰 0, origin.ts HF_RESOLVE 경유).
//   2. 미스 & 로컬 dev — Vite dev 미들웨어 `/__gov` 가 data.go.kr 라이브 호출 → 정규화 → HF 업로드 → 반환.
//   3. 프로덕션 — 캐시 읽기 전용(미스 시 호출측이 KRX 폴백). 운영자가 로컬에서 열며 공유 HF 캐시를 채운다.
// 출처표시 의무(공공누리): gov 데이터 표시 시 GOV_ATTRIBUTION 노출.
import { browser } from '$app/environment';
import { readParquetWholeFile } from '@dartlab/ui-runtime/data/hfRange';
import type { Candle } from './priceSeries';
import { localTerminalAdapter } from './localAdapter';

export const GOV_ATTRIBUTION = '출처: 금융위원회·한국거래소 (공공데이터포털)';

export interface GovCandleFile {
	source: string;
	code: string;
	asOf: string;
	candles: Candle[];
}

const cache = new Map<string, Candle[] | null>();
const inflight = new Map<string, Promise<Candle[] | null>>();

// HF 캐시 = 회사별 parquet (gov/prices/company 동일 schema). 필요한 OHLCV+등락률 컬럼만 projection.
// fluctuationRate = 기준가 대비 등락률 — 수정주가(adjustCandles) 체이닝 입력.
const GOV_PARQUET_COLUMNS = ['date', 'open', 'high', 'low', 'close', 'volume', 'fluctuationRate', 'tradedValue'];
interface GovRow extends Record<string, unknown> {
	date?: string | null;
	open?: number | null;
	high?: number | null;
	low?: number | null;
	close?: number | null;
	volume?: number | null;
	fluctuationRate?: number | null;
	tradedValue?: number | null;
}
function rowToCandle(r: GovRow): Candle | null {
	const c = Number(r.close);
	const t = r.date == null ? '' : String(r.date);
	if (!t || !Number.isFinite(c) || c <= 0) return null;
	const fr = Number(r.fluctuationRate);
	const tv = Number(r.tradedValue);
	return { t, o: Number(r.open) || c, h: Number(r.high) || c, l: Number(r.low) || c, c, v: Number(r.volume) || 0, r: Number.isFinite(fr) ? fr : null, tv: Number.isFinite(tv) ? tv : null };
}
function pick(j: unknown): Candle[] | null {
	const f = j as GovCandleFile | null;
	return f && Array.isArray(f.candles) && f.candles.length ? f.candles : null;
}

async function readHf(code: string): Promise<Candle[] | null> {
	try {
		// 회사별 파일은 작다(~100KB) — HEAD probe 없이 GET 1 회 통파일 (핫패스 RTT 최소화)
		const rows = await readParquetWholeFile<GovRow>(`gov/prices/company/${code}.parquet`, { columns: GOV_PARQUET_COLUMNS });
		if (!rows) return null;
		const candles = rows.map(rowToCandle).filter((x): x is Candle => x != null);
		return candles.length ? candles : null;
	} catch {
		return null;
	}
}

async function fillViaDev(code: string): Promise<Candle[] | null> {
	if (!import.meta.env.DEV) return null; // 프로덕션: 토큰 없음 → 읽기 전용
	try {
		const res = await fetch(`/__gov?code=${encodeURIComponent(code)}`);
		if (!res.ok) return null;
		return pick(await res.json());
	} catch {
		return null;
	}
}

// 최근 30거래일 전종목 슬림 1파일 — 회사 파일(주간 파생)과 병합하는 신선 tail.
// 전 종목이 한 파일을 공유 → 첫 다운로드 후 회사 전환 시 tail 비용 0.
let recentPromise: Promise<Map<string, Candle[]> | null> | null = null;
const RECENT_COLUMNS = ['stockCode', 'date', 'open', 'high', 'low', 'close', 'volume', 'fluctuationRate', 'tradedValue'];

/** 최근 거래일 tail (code → 캔들 오름차순). null = recent 파일 미존재. */
export function loadGovRecent(): Promise<Map<string, Candle[]> | null> {
	if (!browser) return Promise.resolve(null);
	const local = localTerminalAdapter()?.loadGovRecent;
	if (local) return local();
	if (recentPromise) return recentPromise;
	recentPromise = (async () => {
		try {
			const { readParquetWholeFile } = await import('@dartlab/ui-runtime/data/hfRange');
			const rows = await readParquetWholeFile<GovRow & { stockCode?: string | null }>('gov/prices/recent.parquet', { columns: RECENT_COLUMNS });
			if (!rows) return null;
			const map = new Map<string, Candle[]>();
			for (const r of rows) {
				const codeKey = r.stockCode == null ? '' : String(r.stockCode);
				const c = rowToCandle(r);
				if (!codeKey || !c) continue;
				let arr = map.get(codeKey);
				if (!arr) map.set(codeKey, (arr = []));
				arr.push(c);
			}
			return map;
		} catch {
			return null;
		}
	})();
	return recentPromise;
}

/** gov 캐시 주가(전체 이력, 오름차순). null = 미캐시·미지원. 동시 호출 dedup. */
export function loadGovCandles(code: string): Promise<Candle[] | null> {
	if (!browser) return Promise.resolve(null);
	const c = code.trim();
	const local = localTerminalAdapter()?.loadGovCandles;
	if (local) return local(c);
	if (cache.has(c)) return Promise.resolve(cache.get(c) ?? null);
	const hit = inflight.get(c);
	if (hit) return hit;
	const p = (async () => {
		let candles = await readHf(c);
		if (!candles) candles = await fillViaDev(c);
		cache.set(c, candles);
		return candles;
	})().finally(() => inflight.delete(c));
	inflight.set(c, p);
	return p;
}
