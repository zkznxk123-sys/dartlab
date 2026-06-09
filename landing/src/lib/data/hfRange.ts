import type { AsyncBuffer, FileMetaData, ParquetQueryFilter } from 'hyparquet';
import { HF_RESOLVE } from './origin';

export type FetchLike = typeof fetch;

export interface HfObjectRef {
	path: string;
	url: string;
	size: number;
	etag: string | null;
	commit: string | null;
	acceptRanges: boolean;
	contentType: string | null;
}

export interface RangeRequestStat {
	url: string;
	range: string | null;
	status: number;
	bytes: number;
	durationMs: number;
}

export interface ParquetRangeSession {
	ref: HfObjectRef;
	file: AsyncBuffer;
	requests: RangeRequestStat[];
}

export interface ParquetMetadataSummary {
	path: string;
	size: number;
	rows: number;
	rowGroups: number;
	columns: string[];
	requests: RangeRequestStat[];
}

export interface ParquetRowsResult<T extends Record<string, unknown> = Record<string, unknown>> {
	rows: T[];
	requests: RangeRequestStat[];
}

export function hfUrl(path: string): string {
	return `${HF_RESOLVE}/${path.replace(/^\/+/, '')}`;
}

// 동일 파일의 HEAD(범위 probe)는 세션 내 1 회만 — 반복 readParquetRows·lazy 좌측 팬의
// 불필요한 RTT 제거. 파일은 세션 중 불변이므로 ref(size/etag) 캐시 안전.
// 커스텀 fetchFn(측정/프록시 주입)은 캐시하지 않음.
const refCache = new Map<string, Promise<HfObjectRef>>();

export function headHfObject(path: string, fetchFn: FetchLike = fetch): Promise<HfObjectRef> {
	if (fetchFn !== fetch) return headHfObjectFresh(path, fetchFn);
	const hit = refCache.get(path);
	if (hit) return hit;
	const p = headHfObjectFresh(path, fetchFn).catch((e) => {
		refCache.delete(path);
		throw e;
	});
	refCache.set(path, p);
	return p;
}

async function headHfObjectFresh(path: string, fetchFn: FetchLike): Promise<HfObjectRef> {
	const url = hfUrl(path);
	const resp = await fetchResilient(fetchFn, url, { headers: { Range: 'bytes=0-0' } });
	if (!resp.ok && resp.status !== 206) throw new Error(`${path} range probe 실패: ${resp.status}`);
	const linkedSize = Number(resp.headers.get('x-linked-size'));
	const contentLength = Number(resp.headers.get('content-length'));
	const contentRange = resp.headers.get('content-range');
	const rangeSize = contentRange ? Number(contentRange.match(/\/(\d+)$/)?.[1]) : NaN;
	const size =
		Number.isFinite(linkedSize) && linkedSize > 0
			? linkedSize
			: Number.isFinite(rangeSize) && rangeSize > 0
				? rangeSize
				: contentLength;
	if (!Number.isFinite(size) || size <= 0) throw new Error(`${path} 크기 확인 실패`);
	await resp.arrayBuffer();
	return {
		path,
		url: resp.url || url,
		size,
		etag: resp.headers.get('etag') ?? resp.headers.get('x-linked-etag'),
		commit: resp.headers.get('x-repo-commit'),
		acceptRanges: resp.status === 206 || (resp.headers.get('accept-ranges') ?? '').toLowerCase() === 'bytes',
		contentType: resp.headers.get('content-type')
	};
}

export async function probeHfRange(
	path: string,
	range = 'bytes=0-15',
	fetchFn: FetchLike = fetch
): Promise<{ ref: HfObjectRef; status: number; contentRange: string | null; bytes: number }> {
	const ref = await headHfObject(path, fetchFn);
	const resp = await fetchFn(ref.url, { headers: { Range: range } });
	const bytes = (await resp.arrayBuffer()).byteLength;
	return {
		ref,
		status: resp.status,
		contentRange: resp.headers.get('content-range'),
		bytes
	};
}

// 범위요청 + 브라우저 HTTP 캐시 충돌(net::ERR_CACHE_OPERATION_NOT_SUPPORTED 등 — Range 응답이 캐시와 어긋날 때
// Chrome 이 던짐) → 캐시 우회(reload)로 1회 재시도. 잦은 "로드 실패" 가드.
async function fetchResilient(fetchFn: FetchLike, input: Parameters<FetchLike>[0], init?: RequestInit): Promise<Response> {
	// 전이적 CDN 전파(갓 업로드/콜드 캐시)는 403/429/5xx 로 반환되거나 네트워크 throw → 짧은 백오프 재시도.
	// (lazy 이력 로드 시 콜드 parquet 의 transient 403 이 hyparquet throw → unhandled 로 새던 것 차단.)
	const LAST = 3;
	for (let attempt = 0; attempt <= LAST; attempt++) {
		try {
			const resp = await fetchFn(input, attempt === 0 ? init : { ...init, cache: 'reload' });
			if (resp.ok || resp.status === 206) return resp;
			if (attempt < LAST && (resp.status === 403 || resp.status === 429 || resp.status >= 500)) {
				await new Promise((r) => setTimeout(r, 200 + 280 * attempt));
				continue;
			}
			return resp; // 최종 비-OK(404 등)는 그대로 — 호출측이 처리
		} catch {
			if (attempt < LAST) {
				await new Promise((r) => setTimeout(r, 200 + 280 * attempt));
				continue;
			}
			return await fetchFn(input, { ...init, cache: 'reload' });
		}
	}
	return await fetchFn(input, { ...init, cache: 'reload' });
}

export async function openHfParquet(
	path: string,
	fetchFn: FetchLike = fetch
): Promise<ParquetRangeSession> {
	const [{ asyncBufferFromUrl }, ref] = await Promise.all([import('hyparquet'), headHfObject(path, fetchFn)]);
	const requests: RangeRequestStat[] = [];
	const measuredFetch: FetchLike = async (input, init) => {
		const t0 = performance.now();
		const resp = await fetchResilient(fetchFn, input, init);
		const cloned = resp.clone();
		const bytes = Number(resp.headers.get('content-length')) || 0;
		requests.push({
			url: typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url,
			range: new Headers(init?.headers).get('range'),
			status: resp.status,
			bytes,
			durationMs: performance.now() - t0
		});
		return cloned;
	};
	const file = await asyncBufferFromUrl({ url: ref.url, byteLength: ref.size, fetch: measuredFetch });
	return { ref, file, requests };
}

export async function readParquetMetadata(
	path: string,
	fetchFn: FetchLike = fetch
): Promise<ParquetMetadataSummary> {
	const [{ parquetMetadataAsync, parquetSchema }, session] = await Promise.all([
		import('hyparquet'),
		openHfParquet(path, fetchFn)
	]);
	const metadata = (await parquetMetadataAsync(session.file)) as FileMetaData;
	const schema = parquetSchema(metadata);
	return {
		path,
		size: session.ref.size,
		rows: Number(metadata.num_rows),
		rowGroups: metadata.row_groups?.length ?? 0,
		columns: schema.children.map((child) => child.element.name),
		requests: session.requests
	};
}

export async function readParquetRows<T extends Record<string, unknown> = Record<string, unknown>>(
	path: string,
	options: {
		columns?: string[];
		rowStart?: number;
		rowEnd?: number;
		filter?: ParquetQueryFilter;
		filterStrict?: boolean;
		fetchFn?: FetchLike;
	} = {}
): Promise<ParquetRowsResult<T>> {
	const [{ parquetReadObjects }, { compressors }, session] = await Promise.all([
		import('hyparquet'),
		import('hyparquet-compressors'),
		openHfParquet(path, options.fetchFn ?? fetch)
	]);
	const rows = (await parquetReadObjects({
		file: session.file,
		compressors,
		columns: options.columns,
		rowStart: options.rowStart,
		rowEnd: options.rowEnd,
		filter: options.filter,
		filterStrict: options.filterStrict,
		rowFormat: options.filter ? 'object' : undefined
	})) as T[];
	return { rows, requests: session.requests };
}
