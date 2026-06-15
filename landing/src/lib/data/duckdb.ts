/**
 * DuckDB-WASM lazy 로더 — HF parquet 직접 query.
 *
 * dartlab 의 데이터 SSOT 는 HF dataset (`eddmpython/dartlab-data`, public). 이 파일은
 * 브라우저에서 DuckDB-WASM 을 lazy 로드하고, HF parquet 을 HTTPS 로 직접 query 하는
 * 단일 진입점이다. 결과는 row 배열 (JS 객체) 로 반환해 frontend 가 그대로 렌더한다.
 *
 * 핵심 전략:
 *   - 첫 호출 시 CDN (jsdelivr) 에서 DuckDB-WASM 동적 import (~1MB, 캐시됨)
 *   - 싱글톤 — 페이지 내 한 번만 인스턴스화
 *   - httpfs 자동 활성 — `read_parquet('https://...')` 패턴 그대로 사용
 *   - 작은 JSON (ecosystem.json 등) 은 fetch 후 `registerJson()` 으로 임시 테이블화
 *   - iOS Safari (메모리 제한) 는 null 반환 → 호출자 JS fallback
 *
 * 사용 예::
 *
 *   import { loadDartDb, hfParquetUrl } from '$lib/data/duckdb';
 *
 *   const db = await loadDartDb();
 *   if (!db) return; // iOS or 로드 실패 — JS fallback
 *
 *   await db.registerHfParquet('prices2024', 'gov/prices/date/2024.parquet');
 *   const rows = await db.query<{ ISU_CD: string; close: number }>(
 *     `SELECT ISU_CD, TDD_CLSPRC AS close FROM prices2024 WHERE ISU_CD = '005930' ORDER BY BAS_DD DESC LIMIT 10`
 *   );
 */

import { browser } from '$app/environment';
import { attachOpfs, OPFS_DB_ALIAS } from './duckdbOpfs';

const DUCKDB_VERSION = '1.29.0';
const CDN_BASE = `https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@${DUCKDB_VERSION}/dist/`;
const CDN_ESM = `https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@${DUCKDB_VERSION}/+esm`;

const HF_REPO = 'eddmpython/dartlab-data';
const HF_RESOLVE = `https://huggingface.co/datasets/${HF_REPO}/resolve/main/`;

export interface DartDb {
	/** OPFS persistent DB attached 여부. true 면 결과 영속화 가능. */
	readonly persisted: boolean;
	/** OPFS DB 의 schema mismatch 로 자동 rebuild 발생했는지 (이번 init). */
	readonly opfsRebuilt: boolean;
	/** SQL 실행 → row 배열 (JS 객체). 빈 결과는 빈 배열. */
	query<T = Record<string, unknown>>(sql: string): Promise<T[]>;
	/** SQL 실행 → batch 단위 streaming. 첫 batch 가 즉시 도달, 점진 progressive UI 가능.
	 *
	 * @example
	 *   for await (const rows of db.queryStream<MyRow>(sql)) {
	 *     // rows = up to 2048 records per batch
	 *     for (const r of rows) map.set(r.id, r);
	 *   }
	 */
	queryStream<T = Record<string, unknown>>(sql: string): AsyncGenerator<T[], void, void>;
	/** HF parquet 을 view 로 등록 (httpfs 원격 range 직독). 대형·범위읽기용. */
	registerHfParquet(viewName: string, hfPath: string): Promise<void>;
	/** 소형 parquet(회사 재무 등 ~수백KB)을 통파일 1회 GET(프록시·엣지캐시·403 흡수)으로 받아 DuckDB
	 *  버퍼로 등록 → 이후 모든 쿼리를 로컬에서. httpfs 매 쿼리 원격 range 왕복·콜드403 회피. */
	registerHfParquetBuffer(viewName: string, hfPath: string): Promise<void>;
	/** JS 객체 배열을 임시 테이블로 등록 (작은 메타 JSON 용). */
	registerJson(tableName: string, rows: unknown[]): Promise<void>;
	/** 연결 종료 (페이지 unmount 시 호출 권장, optional). */
	close(): Promise<void>;
}

let _initPromise: Promise<DartDb | null> | null = null;
let _conn: any = null;
let _db: any = null;
let _worker: Worker | null = null;
let _persisted = false;
let _opfsRebuilt = false;

/** HF parquet 절대 URL 생성. 상대 경로 (`gov/prices/date/2024.parquet`) 또는 full URL 모두 받음. */
export function hfParquetUrl(pathOrUrl: string): string {
	if (pathOrUrl.startsWith('http://') || pathOrUrl.startsWith('https://')) return pathOrUrl;
	return HF_RESOLVE + pathOrUrl.replace(/^\/+/, '');
}

// 소형 통파일 GET 용 base — CF 프록시(VITE_DARTLAB_HF_RESOLVE) 우선(엣지캐시·콜드403 흡수·CORS echo),
// 미설정 시 HF 직결. 통파일 GET 은 origin.ts 가 명시한 "프록시의 강점" 경로(206 range 아님).
const _viteHfResolve = (import.meta as { env?: Record<string, string | undefined> }).env?.VITE_DARTLAB_HF_RESOLVE;
const WHOLE_BASE = (_viteHfResolve || HF_RESOLVE).replace(/\/+$/, '');

// 소형 parquet(회사 재무 ~수백KB) 통파일 캐시 — httpfs 매 쿼리 원격 range 왕복·콜드403 대신 1회 GET 후
// DuckDB 버퍼 등록. path 별 바이트 캐시(재방문 무네트워크) + DuckDB 파일 누적 캡(LRU drop).
const _bufBytes = new Map<string, Uint8Array>();
const _bufFiles = new Set<string>();
const _BUF_CAP = 12;
const _bufFileName = (hfPath: string): string => `dlbuf_${hfPath.replace(/[^A-Za-z0-9]/g, '_')}`;

async function _fetchWholeParquet(hfPath: string): Promise<Uint8Array> {
	const url = `${WHOLE_BASE}/${hfPath.replace(/^\/+/, '')}`;
	let lastErr: unknown;
	for (let attempt = 0; attempt < 3; attempt++) {
		try {
			const res = await fetch(url, { cache: 'force-cache' });
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			return new Uint8Array(await res.arrayBuffer());
		} catch (err) {
			lastErr = err;
			await new Promise((r) => setTimeout(r, 200 * (attempt + 1)));
		}
	}
	throw lastErr instanceof Error ? lastErr : new Error(String(lastErr));
}

/** SQL 문자열 escape — 단일 인용부 안전. */
export function sqlEscape(value: string): string {
	return value.replace(/'/g, "''");
}

function _detectMobileSafari(): boolean {
	if (!browser || typeof navigator === 'undefined') return false;
	const ua = navigator.userAgent;
	// iOS WebKit (Safari, Chrome iOS, Firefox iOS 모두 동일 엔진) — 메모리 제한
	const isIos = /iPad|iPhone|iPod/.test(ua);
	const isIosChrome = /CriOS/.test(ua);
	const isIosFirefox = /FxiOS/.test(ua);
	// Chrome/FF on iOS 도 WebKit 이라 동일하게 가드. 단 Chrome iOS 는 약간 더 안정적.
	return isIos && !isIosChrome && !isIosFirefox;
}

async function _instantiate(): Promise<DartDb | null> {
	if (!browser) return null;

	// iOS Safari 가드 — DuckDB WASM 이 1GB 까지 메모리 요청 가능, iOS 는 200~512MB 한계
	if (_detectMobileSafari()) {
		console.info('[duckdb] iOS Safari 감지 — DuckDB-WASM 비활성, JS fallback 권장');
		return null;
	}

	try {
		// Vite/SvelteKit 가 remote URL import 를 번들에 포함 안 하도록 vite-ignore
		const duckdb = await import(/* @vite-ignore */ CDN_ESM);

		const bundles = {
			mvp: {
				mainModule: `${CDN_BASE}duckdb-mvp.wasm`,
				mainWorker: `${CDN_BASE}duckdb-browser-mvp.worker.js`
			},
			eh: {
				mainModule: `${CDN_BASE}duckdb-eh.wasm`,
				mainWorker: `${CDN_BASE}duckdb-browser-eh.worker.js`
			}
		};

		const bundle = await (duckdb as any).selectBundle(bundles);

		// GitHub Pages 같은 cross-origin 환경에서 Worker 직접 생성 불가 (SecurityError).
		// jsdelivr 의 worker script 를 fetch → Blob URL 로 same-origin 처럼 wrap → Worker 생성.
		const workerScriptText = await (await fetch(bundle.mainWorker as string)).text();
		const workerBlobUrl = URL.createObjectURL(
			new Blob([workerScriptText], { type: 'application/javascript' })
		);
		_worker = new Worker(workerBlobUrl);

		const logger = new (duckdb as any).ConsoleLogger();
		_db = new (duckdb as any).AsyncDuckDB(logger, _worker);
		await _db.instantiate(bundle.mainModule, bundle.pthreadWorker);
		_conn = await _db.connect();

		// Blob URL revoke (worker 가 이미 인스턴스화됐으니 해제 가능)
		URL.revokeObjectURL(workerBlobUrl);

		// httpfs 활성 — HF parquet HTTPS query 핵심
		// (DuckDB-WASM 표준 빌드는 httpfs 가 자동 포함되지만 명시적 LOAD 안전)
		try {
			await _conn.query('INSTALL httpfs');
			await _conn.query('LOAD httpfs');
		} catch {
			// 이미 로드됐거나 빌드에 포함 — 무시
		}

		// OPFS attach — 임시 비활성. v1.29 의 BROWSER_FSACCESS protocol 작동 검증 후 재활성.
		// const opfsResult = await attachOpfs(_db, _conn, duckdb);
		// _persisted = opfsResult.ok;
		// _opfsRebuilt = opfsResult.rebuilt;
		_persisted = false;
		_opfsRebuilt = false;
	} catch (err) {
		console.warn('[duckdb] 인스턴스화 실패 — JS fallback', err);
		await _cleanup();
		return null;
	}

	const api: DartDb = {
		get persisted() {
			return _persisted;
		},
		get opfsRebuilt() {
			return _opfsRebuilt;
		},
		async query(sql: string) {
			if (!_conn) throw new Error('DuckDB 연결이 없습니다');
			const result = await _conn.query(sql);
			return _toRowObjects(result);
		},

		queryStream<T = Record<string, unknown>>(sql: string) {
			return _streamRows<T>(sql);
		},

		async registerHfParquet(viewName: string, hfPath: string) {
			if (!_conn) throw new Error('DuckDB 연결이 없습니다');
			const url = hfParquetUrl(hfPath);
			const safeView = _safeIdent(viewName);
			await _conn.query(
				`CREATE OR REPLACE VIEW ${safeView} AS SELECT * FROM read_parquet('${sqlEscape(url)}')`
			);
		},

		async registerHfParquetBuffer(viewName: string, hfPath: string) {
			if (!_db || !_conn) throw new Error('DuckDB 연결이 없습니다');
			const fileName = _bufFileName(hfPath);
			let bytes = _bufBytes.get(hfPath);
			if (!bytes) {
				bytes = await _fetchWholeParquet(hfPath);
				_bufBytes.set(hfPath, bytes);
			}
			if (!_bufFiles.has(fileName)) {
				await _db.registerFileBuffer(fileName, bytes);
				_bufFiles.add(fileName);
			}
			// 캡 초과 → 가장 오래된 버퍼 drop (현재 path 제외) — WASM 메모리 누적 가드
			while (_bufBytes.size > _BUF_CAP) {
				const oldest = _bufBytes.keys().next().value;
				if (!oldest || oldest === hfPath) break;
				_bufBytes.delete(oldest);
				const f = _bufFileName(oldest);
				if (_bufFiles.delete(f)) {
					try { await _db.dropFile(f); } catch { /* view 가 참조 중이면 무시 */ }
				}
			}
			const safeView = _safeIdent(viewName);
			await _conn.query(`CREATE OR REPLACE VIEW ${safeView} AS SELECT * FROM read_parquet('${sqlEscape(fileName)}')`);
		},

		async registerJson(tableName: string, rows: unknown[]) {
			if (!_db || !_conn) throw new Error('DuckDB 연결이 없습니다');
			const safeTable = _safeIdent(tableName);
			const fileName = `${tableName}.json`;
			const json = JSON.stringify(rows ?? []);
			await _db.registerFileText(fileName, json);
			await _conn.query(
				`CREATE OR REPLACE TABLE ${safeTable} AS SELECT * FROM read_json_auto('${sqlEscape(fileName)}')`
			);
		},

		async close() {
			await _cleanup();
		}
	};

	return api;
}

async function _cleanup() {
	try {
		if (_conn) await _conn.close();
	} catch {
		/* ignore */
	}
	try {
		if (_db) await _db.terminate();
	} catch {
		/* ignore */
	}
	if (_worker) {
		_worker.terminate();
	}
	_conn = null;
	_db = null;
	_worker = null;
	_persisted = false;
	_opfsRebuilt = false;
	_initPromise = null;
}

function _toRowObjects<T>(arrowResult: any): T[] {
	// Arrow 결과는 row proxy. JSON-serializable plain object 로 변환.
	if (!arrowResult || typeof arrowResult.toArray !== 'function') return [];
	const rows = arrowResult.toArray() as any[];
	return rows.map((row: any) => _normalizeRow<T>(row));
}

function _normalizeRow<T>(row: any): T {
	const obj: Record<string, unknown> = {};
	for (const key of Object.keys(row)) {
		const v = row[key];
		if (v == null) {
			obj[key] = v;
		} else if (typeof v === 'bigint') {
			obj[key] = Number(v);
		} else if (typeof v === 'object') {
			// Arrow ListVector / Vector — `.toArray()` 로 native 추출 후 Array.from 으로 plain JS 배열
			let extracted: any = v;
			if (typeof (v as any).toArray === 'function') {
				try {
					extracted = (v as any).toArray();
				} catch {
					extracted = v;
				}
			}
			// Float64Array / Int32Array / Array 모두 Array.from 으로 plain Array 로 변환
			if (extracted && typeof extracted !== 'string' && typeof (extracted as any)[Symbol.iterator] === 'function') {
				try {
					obj[key] = Array.from(extracted as Iterable<any>, (x: any) =>
						typeof x === 'bigint' ? Number(x) : x
					);
				} catch {
					obj[key] = extracted;
				}
			} else {
				obj[key] = extracted;
			}
		} else {
			obj[key] = v;
		}
	}
	return obj as T;
}

/** Arrow RecordBatch 또는 Table 을 JS row 배열로. */
function _batchToRows<T>(batch: any): T[] {
	if (!batch) return [];
	// RecordBatch 는 toArray() 또는 Symbol.iterator 지원
	if (typeof batch.toArray === 'function') {
		const rows = batch.toArray() as any[];
		return rows.map((r) => _normalizeRow<T>(r));
	}
	// fallback — iterator
	const out: T[] = [];
	try {
		for (const r of batch as Iterable<any>) {
			out.push(_normalizeRow<T>(r));
		}
	} catch {
		/* ignore */
	}
	return out;
}

/** SQL streaming — connection.send() 시도, 실패 시 query() 로 fallback.
 *
 * DuckDB-WASM v1.29 의 send() 가 일부 SQL (특히 GROUP BY · CTE 다단) 에서
 * reject 하는 경우가 있음. streaming 효과를 잃더라도 정확한 결과 우선.
 */
async function* _streamRows<T>(sql: string): AsyncGenerator<T[], void, void> {
	if (!_conn) throw new Error('DuckDB 연결이 없습니다');
	// 1) streaming 시도 — 성공하면 batch 단위 yield
	try {
		const reader = await _conn.send(sql);
		if (reader && typeof reader[Symbol.asyncIterator] === 'function') {
			let yielded = false;
			for await (const batch of reader as AsyncIterable<any>) {
				const rows = _batchToRows<T>(batch);
				if (rows.length > 0) {
					yielded = true;
					yield rows;
				}
			}
			if (yielded) return;
			// streaming 이 0 batch 줬을 수도 — query() 로 재시도
		}
	} catch (err) {
		console.info('[duckdb] streaming 미지원 SQL → query() fallback');
	}
	// 2) fallback — non-streaming.
	const result = await _conn.query(sql);
	const all = _toRowObjects<T>(result);
	if (all.length > 0) yield all;
}

function _safeIdent(name: string): string {
	// SQL 식별자 — 영문·숫자·밑줄만 허용. 충돌 시 throw.
	if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(name)) {
		throw new Error(`invalid SQL identifier: ${name}`);
	}
	return `"${name}"`;
}

/**
 * DuckDB-WASM 인스턴스 lazy 로드. 싱글톤 — 한 페이지 내 1회만 실제 로드.
 *
 * @returns DartDb 인스턴스. iOS Safari 또는 로드 실패 시 null.
 */
export function loadDartDb(): Promise<DartDb | null> {
	if (!_initPromise) {
		_initPromise = _instantiate();
	}
	return _initPromise;
}

/** 페이지 unmount 시 정리 (optional). */
export async function unloadDartDb(): Promise<void> {
	await _cleanup();
}
