// 시장 전체(cross) 뉴스 피드 — public rss 아카이브(news/public/rss/{market}/{YYYY-MM-DD}.parquet,
// Google News RSS·재배포 가능)의 최근 N일 shard 를 통째로 읽어 합친다. 종목별(loadCompanyNews, naver
// 워커 라이브 read)과 *경로 분리*: 이건 전 시장이라 stock_code 필터 없이 일별 공개 parquet 직독.
//   bake(통합 recent 파일)는 의도적으로 안 만든다 — 시장 뉴스는 매일 조밀해 최근 며칠 shard 면 충분하고,
//   기존 일별 cron 산출물(gather writeDailyParquet)을 그대로 직독하는 게 별도빌드 0 의 정공법. 오늘(UTC)
//   shard 는 cron(어제까지) 직후라 보통 미존재이므로 어제부터 역순으로 읽어 불필요한 404 를 피한다.
//   미존재일(404)은 requestParquetWholeFile 이 null + 음성캐시 → 반복 GET 0.
// 제목+원문링크만(스니펫 없음) — 클릭=외부 기사 이동. rss 는 스키마상 description 이 null 이라 본디 제목만.
import type { MarketNews } from '@dartlab/ui-contracts';
import { moduleFallbackCore, type DataCore } from '../../../data/fetch/request';

interface NewsRow extends Record<string, unknown> {
	date?: unknown;
	title?: unknown;
	url?: unknown;
	source?: unknown;
}

const COLS = ['date', 'title', 'url', 'source'];
const DAYS = 5; // 최근 N UTC 일 shard (어제부터 역순) — 좌측 한눈 피드엔 충분
const CAP = 300; // 렌더 상한 — 최근 윈도우라 무한스크롤 불필요

// core 미주입 경로(레거시/어댑터 무인자 호출) 전용 lazy 폴백 — loadCompanyNews(newsSource) 동형.
const marketCore = moduleFallbackCore();

// pl.Date 컬럼은 hyparquet 가 JS Date 로 준다 — Date/문자열/epoch-days 모두 YYYY-MM-DD 로 정규화.
function toIsoDate(v: unknown): string {
	if (v instanceof Date) return v.toISOString().slice(0, 10);
	const s = String(v ?? '').trim();
	if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, 10);
	const n = Number(s);
	if (Number.isFinite(n) && n > 10_000 && n < 100_000) return new Date(n * 86_400_000).toISOString().slice(0, 10);
	return s;
}

// 어제(UTC)부터 N일 역순 — [어제, 그제, …]. 오늘은 cron 미반영이라 제외(불필요 404 회피).
function recentDays(now: Date, days: number): string[] {
	const out: string[] = [];
	for (let i = 1; i <= days; i++) {
		const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() - i));
		out.push(d.toISOString().slice(0, 10));
	}
	return out;
}

/** 행 정규화 — 제목·url 필수, url dedup, date 내림차순, CAP. 순수 함수(테스트 대상). */
export function normalizeMarketNews(rows: NewsRow[]): MarketNews[] {
	const seen = new Set<string>();
	const out: MarketNews[] = [];
	for (const r of rows) {
		const url = String(r.url ?? '').trim();
		const title = String(r.title ?? '').trim();
		if (!url || !title || seen.has(url)) continue;
		seen.add(url);
		out.push({ date: toIsoDate(r.date), title, source: String(r.source ?? '').trim(), url });
	}
	out.sort((a, b) => b.date.localeCompare(a.date));
	return out.slice(0, CAP);
}

/** 시장 전체 최근 뉴스 — rss 공개 아카이브 최근 N일 shard 직독·합침. 실패/미배선은 []. */
export async function loadMarketNews(core?: DataCore, market = 'KR', now: Date = new Date()): Promise<MarketNews[]> {
	const c = marketCore(core);
	const days = recentDays(now, DAYS);
	try {
		const perDay = await Promise.all(
			days.map((day) =>
				c
					.requestParquetWholeFile<NewsRow>({
						origin: 'hf',
						path: `news/public/rss/${market}/${day}.parquet`,
						columns: COLS,
						cacheKey: `news.market:${market}:${day}`,
						cache: { scope: 'memory', ttlMs: 10 * 60_000, maxEntries: 8 } // 신선도 — 짧은 TTL
					})
					.catch(() => null)
			)
		);
		return normalizeMarketNews(perDay.flatMap((r) => r ?? []));
	} catch {
		return [];
	}
}
