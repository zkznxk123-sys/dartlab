import type { AsyncBuffer, FileMetaData, ParquetQueryFilter } from 'hyparquet';

const DEFAULT_HF_RESOLVE = 'https://huggingface.co/datasets/eddmpython/dartlab-data/resolve/main';
const HF_RESOLVE = (import.meta.env.VITE_DARTLAB_HF_RESOLVE ?? DEFAULT_HF_RESOLVE).replace(/\/+$/, '');
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

export async function headHfObject(path: string, fetchFn: FetchLike = fetch): Promise<HfObjectRef> {
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
	try {
		return await fetchFn(input, init);
	} catch {
		return await fetchFn(input, { ...init, cache: 'reload' });
	}
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
