import { base } from '$app/paths';
import { readJsonCache, writeJsonCache } from './cacheStore';

// HF resolve base URL 은 origin.ts SSOT 에서 (내부 사용 + consumers 호환 위해 re-export).
import { HF_RESOLVE } from './origin';
export { HF_RESOLVE };
const DEFAULT_TTL_MS = 6 * 60 * 60 * 1000;

export type FetchLike = typeof fetch;

export interface LoadJsonOptions {
	fetchFn: FetchLike;
	ttlMs?: number;
	required?: boolean;
	preferLocal?: boolean;
}

function normalizePath(path: string): string {
	return path.replace(/^\/+/, '');
}

function hasHfLandingJson(path: string): boolean {
	return (
		// dashboards — mapBuild 가 매일 HF publish (git 정적 사본 4/22 동결 사고 후 신설 경로)
		path === 'dashboards/finance.json' ||
		path === 'dashboards/quarters.json' ||
		path === 'dashboards/macro.json' ||
		path === 'dashboards/meta.json' ||
		path === 'map/atlas.json' ||
		path === 'map/ecosystem.json' ||
		path === 'map/industryStats.json' ||
		path === 'map/insights.json' ||
		path === 'map/meta.json' ||
		path === 'map/movers.json' ||
		path === 'map/prices-snapshot.json' ||
		path === 'map/search-index.json' ||
		path === 'map/timeline.json' ||
		path.startsWith('map/companies/') ||
		path.startsWith('map/industries/')
	);
}

function shouldCacheJson(path: string): boolean {
	return (
		path !== 'map/ecosystem.json' &&
		path !== 'map/prices-snapshot.json' &&
		path !== 'landing/map/ecosystem.json' &&
		path !== 'landing/map/prices-snapshot.json'
	);
}

async function fetchJson<T>(url: string, fetchFn: FetchLike): Promise<T | null> {
	try {
		const resp = await fetchFn(url);
		if (!resp.ok) return null;
		return (await resp.json()) as T;
	} catch {
		return null;
	}
}

export async function loadJson<T>(
	path: string,
	{ fetchFn, ttlMs = DEFAULT_TTL_MS, required = false, preferLocal = false }: LoadJsonOptions
): Promise<T | null> {
	const normalized = normalizePath(path);
	const cacheable = shouldCacheJson(normalized);
	const cached = cacheable ? await readJsonCache<T>(normalized, ttlMs) : null;
	if (cached != null) return cached;

	if (preferLocal) {
		const local = await fetchJson<T>(`${base}/${normalized}`, fetchFn);
		if (local != null) {
			if (cacheable) void writeJsonCache(normalized, local);
			return local;
		}
	}

	if (hasHfLandingJson(normalized)) {
		const hf = await fetchJson<T>(`${HF_RESOLVE}/landing/${normalized}`, fetchFn);
		if (hf != null) {
			if (cacheable) void writeJsonCache(normalized, hf);
			return hf;
		}
	}

	if (!preferLocal) {
		const local = await fetchJson<T>(`${base}/${normalized}`, fetchFn);
		if (local != null) {
			if (cacheable) void writeJsonCache(normalized, local);
			return local;
		}
	}

	if (!hasHfLandingJson(normalized)) {
		const hf = await fetchJson<T>(`${HF_RESOLVE}/landing/${normalized}`, fetchFn);
		if (hf != null) {
			if (cacheable) void writeJsonCache(normalized, hf);
			return hf;
		}
	}

	const stale = cacheable ? await readJsonCache<T>(normalized, ttlMs, { allowStale: true }) : null;
	if (stale != null) return stale;

	if (required) throw new Error(`${normalized} 로드 실패`);
	return null;
}

export async function loadHfJson<T>(
	path: string,
	{ fetchFn, ttlMs = DEFAULT_TTL_MS, required = false }: LoadJsonOptions
): Promise<T | null> {
	const normalized = normalizePath(path);
	const cacheKey = `hf/${normalized}`;
	const cacheable = shouldCacheJson(normalized);
	const cached = cacheable ? await readJsonCache<T>(cacheKey, ttlMs) : null;
	if (cached != null) return cached;

	const hf = await fetchJson<T>(`${HF_RESOLVE}/${normalized}`, fetchFn);
	if (hf != null) {
		if (cacheable) void writeJsonCache(cacheKey, hf);
		return hf;
	}

	const stale = cacheable ? await readJsonCache<T>(cacheKey, ttlMs, { allowStale: true }) : null;
	if (stale != null) return stale;

	if (required) throw new Error(`${normalized} HF 로드 실패`);
	return null;
}

export function prewarmJson(paths: string[], fetchFn: FetchLike, ttlMs = DEFAULT_TTL_MS): void {
	for (const path of paths) {
		void loadJson(path, { fetchFn, ttlMs, required: false });
	}
}
