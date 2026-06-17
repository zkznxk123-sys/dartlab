// fetch 코어 — 데이터 워크벤치 SSOT 의 단일 호출 진입점. (mainPlan/data-workbench-ssot 02)
// 오리진 해소 + RequestDedup(in-flight 공유) + RuntimeCache(TTL/LRU) + fetchResilient(backoff) 합성.
// ★여기서 RuntimeCache·RequestDedup 를 *처음 인스턴스화*한다 — 그동안 export 만 되고 죽어있던 작업대를 실배선.
// 어댑터당 1 인스턴스(createDataCore) — 전역 싱글턴 금지(04 KILL: 테스트 격리·soft-swap 오염 방지).
import { RuntimeCache } from '../cache/runtimeCache';
import { RequestDedup } from '../cache/requestDedup';
import { fetchResilient, readParquetRows, readParquetWholeFile, type FetchLike } from '../parquet/hfRange';
import type { ParquetQueryFilter } from 'hyparquet';
import { originUrl, originCache, type CachePolicy, type OriginId } from '../origins/registry';

const MIN = 60_000;
const DEFAULT_PARQUET_CACHE: CachePolicy = { scope: 'memory', ttlMs: 60 * MIN, maxEntries: 128 };

export interface RequestSpec<T> {
	origin: OriginId;
	path: string;
	parse: (res: Response) => Promise<T>;
	/** 미지정 시 오리진 기본 정책. */
	cache?: CachePolicy;
	/** 캐시·dedup 키. 미지정 시 `${origin}:${path}`. */
	cacheKey?: string;
	/** 기본 true(동일 키 in-flight 공유). */
	dedup?: boolean;
	init?: RequestInit;
}

export interface ParquetRowsSpec<T> {
	/** parquet 는 hfRange 가 URL 을 만든다(hfRangeUrl) — origin 은 표기용(기본 hfRange). */
	origin?: Extract<OriginId, 'hfRange'>;
	path: string;
	columns?: string[];
	filter?: ParquetQueryFilter;
	cache?: CachePolicy;
	cacheKey: string;
	dedup?: boolean;
}

export interface ParquetWholeFileSpec<T> {
	/** 소형 통파일 GET(readParquetWholeFile) — hf(프록시) URL. origin 은 표기용(기본 hf). */
	origin?: Extract<OriginId, 'hf'>;
	path: string;
	columns?: string[];
	cache?: CachePolicy;
	cacheKey: string;
	dedup?: boolean;
}

export interface DataCore {
	request<T>(spec: RequestSpec<T>): Promise<T>;
	requestParquetRows<T extends Record<string, unknown>>(spec: ParquetRowsSpec<T>): Promise<T[]>;
	/** 소형 단일 parquet 통파일 직독(HEAD probe 생략, GET 1회). 미존재(404)는 null — read 레벨 캐시·dedup 공유. */
	requestParquetWholeFile<T extends Record<string, unknown>>(spec: ParquetWholeFileSpec<T>): Promise<T[] | null>;
	clear(): void;
}

export interface DataCoreOptions {
	/** 주입 가능(테스트·로컬). 기본 전역 fetch. */
	fetchFn?: FetchLike;
	/** 주입 가능(테스트 결정론). 기본 Date.now. */
	now?: () => number;
}

export function createDataCore(opts: DataCoreOptions = {}): DataCore {
	const fetchFn = opts.fetchFn ?? (fetch as FetchLike);
	const now = opts.now ?? Date.now;
	const dedup = new RequestDedup();
	// TTL 별 캐시 버킷 — RuntimeCache 가 인스턴스당 단일 TTL 이라, 정책 TTL 별로 버킷을 분리(maxEntries 는 최초 정책 기준).
	const buckets = new Map<number, RuntimeCache<unknown>>();
	function bucket(p: CachePolicy): RuntimeCache<unknown> {
		let b = buckets.get(p.ttlMs);
		if (!b) {
			b = new RuntimeCache<unknown>({ maxEntries: p.maxEntries ?? 128, ttlMs: p.ttlMs });
			buckets.set(p.ttlMs, b);
		}
		return b;
	}

	async function request<T>(spec: RequestSpec<T>): Promise<T> {
		const policy = spec.cache ?? originCache(spec.origin) ?? { scope: 'none', ttlMs: 0 };
		const key = spec.cacheKey ?? `${spec.origin}:${spec.path}`;
		if (policy.scope === 'memory') {
			const hit = bucket(policy).get(key, now());
			if (hit !== undefined) return hit as T;
		}
		const exec = async (): Promise<T> => {
			const res = await fetchResilient(fetchFn, originUrl(spec.origin, spec.path), spec.init);
			const value = await spec.parse(res); // 에러는 전파(캐시에 안 넣음) — 실패 Promise 캐시 버그 차단
			if (policy.scope === 'memory') bucket(policy).set(key, value, now());
			return value;
		};
		return spec.dedup === false ? exec() : (dedup.run(key, exec) as Promise<T>);
	}

	async function requestParquetRows<T extends Record<string, unknown>>(spec: ParquetRowsSpec<T>): Promise<T[]> {
		const policy = spec.cache ?? DEFAULT_PARQUET_CACHE;
		const key = spec.cacheKey;
		if (policy.scope === 'memory') {
			const hit = bucket(policy).get(key, now());
			if (hit !== undefined) return hit as T[];
		}
		const exec = async (): Promise<T[]> => {
			const { rows } = await readParquetRows<T>(spec.path, { columns: spec.columns, filter: spec.filter, fetchFn });
			if (policy.scope === 'memory') bucket(policy).set(key, rows, now());
			return rows;
		};
		return spec.dedup === false ? exec() : (dedup.run(key, exec) as Promise<T[]>);
	}

	async function requestParquetWholeFile<T extends Record<string, unknown>>(spec: ParquetWholeFileSpec<T>): Promise<T[] | null> {
		const policy = spec.cache ?? DEFAULT_PARQUET_CACHE;
		const key = spec.cacheKey;
		if (policy.scope === 'memory') {
			const hit = bucket(policy).get(key, now());
			if (hit !== undefined) return hit as T[] | null;
		}
		const exec = async (): Promise<T[] | null> => {
			const rows = await readParquetWholeFile<T>(spec.path, { columns: spec.columns, fetchFn });
			// null(404) 도 캐시한다 — 미존재 파일 반복 GET 차단(음성 캐시). 호출측이 빈 결과 캐시 회피가
			// 필요하면(예: 일시 404 poisoning) catch 후 자체 판단(govIndex universe 가 그 예).
			if (policy.scope === 'memory') bucket(policy).set(key, rows, now());
			return rows;
		};
		return spec.dedup === false ? exec() : (dedup.run(key, exec) as Promise<T[] | null>);
	}

	function clear(): void {
		for (const b of buckets.values()) b.clear();
	}

	return { request, requestParquetRows, requestParquetWholeFile, clear };
}

/**
 * 레거시 무인자 포트 경로용 모듈 폴백 코어 — core 미주입 시 1회 lazy 생성(호출마다 self 격리).
 * ui/web(localTerminalData)·core 없는 localCompanyPort 가 포트를 무인자 호출하는 동안만 쓰인다.
 * 어댑터(createXRuntime)가 core 를 주입하면 그걸 그대로 사용. source 가 createDataCore 를 직접
 * 부르지 않게 모아 둔다(가드 rule 4 특례 제거). 정식 해소 = 호출부 core 주입(ui-platform-refactor).
 */
export function moduleFallbackCore(): (core?: DataCore) => DataCore {
	let fallback: DataCore | null = null;
	return (core) => core ?? (fallback ??= createDataCore());
}
