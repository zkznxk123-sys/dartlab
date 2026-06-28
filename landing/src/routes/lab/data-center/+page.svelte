<script lang="ts">
	// 데이터 다운로드 센터 (Tier1 — 브라우저 parquet 직독, 백엔드 0). mainPlan/data-download-center.
	// 카탈로그(노출 SSOT) → dir·id 선택 → cols/tail 슬라이스 → xlsx/CSV 다운로드 + Tier2 라이브 URL 링크빌더.
	// 전부 기존 자산 재사용: 카탈로그(runtime), readParquet*(runtime), buildWorkbook·downloadBlob(viewer), toCsv(scan).
	import { DOWNLOAD_CATALOG, isTier2Eligible } from '@dartlab/ui-runtime/data/catalog/downloadCatalog';
	import { readParquetMetadata, readParquetRows } from '@dartlab/ui-runtime/data/parquet/hfRange';
	import { buildWorkbook, downloadBlob, type GridCell } from '@dartlab/ui-surfaces/viewer';
	import { downloadCsv } from '@dartlab/ui-surfaces/scan';

	const XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
	const CELL_CAP = 45000; // Tier2 라이브 셀 상한 (Sheets IMPORTDATA ~5만 셀, 01-api-contract §4).
	// Tier2 워커 호스트 — 미배포 시 placeholder(03-tier2-live-worker). env 설정 시 실 URL.
	const CSV_HOST =
		(import.meta as { env?: Record<string, string> }).env?.VITE_DARTLAB_CSV_PROXY || 'https://〈데이터-워커〉';

	const PLACEHOLDER: Record<string, string> = {
		company: '종목코드/ticker (예 005930 · AAPL)',
		series: '시리즈/지수/월 ID (예 DGS10)',
		dateShard: '날짜/연도 (예 2024)',
		bulk: '파일명 (예 valuation)'
	};

	let selectedDir = $state(DOWNLOAD_CATALOG[0].dir);
	let id = $state('005930');
	let schema = $state<{ columns: string[]; rows: number } | null>(null);
	let selectedCols = $state<string[]>([]);
	let tail = $state<number | null>(null);
	let loadingSchema = $state(false);
	let working = $state<'' | 'csv' | 'xlsx'>('');
	let error = $state('');

	const entry = $derived(DOWNLOAD_CATALOG.find((e) => e.dir === selectedDir) ?? DOWNLOAD_CATALOG[0]);
	const path = $derived(`${selectedDir}/${id.trim()}.parquet`);
	const effectiveCols = $derived(selectedCols.length ? selectedCols : (schema?.columns ?? []));
	const effectiveRows = $derived(
		schema ? (tail ? Math.min(tail, schema.rows) : schema.rows) : 0
	);
	const cellCount = $derived(effectiveCols.length * effectiveRows);

	const liveUrl = $derived.by(() => {
		// 쿼리를 손수 조립 — 컬럼명은 단순 식별자라 콤마를 인코딩(%2C)하지 않고 리터럴로(추측가능 URL).
		const qs: string[] = [];
		if (schema && selectedCols.length && selectedCols.length < schema.columns.length)
			qs.push(`cols=${selectedCols.join(',')}`);
		if (tail) qs.push(`tail=${tail}`);
		return `${CSV_HOST}/v1/${selectedDir}/${id.trim()}.csv${qs.length ? '?' + qs.join('&') : ''}`;
	});

	function onDirChange() {
		schema = null;
		selectedCols = [];
		tail = null;
		error = '';
	}

	function toggleCol(col: string) {
		selectedCols = selectedCols.includes(col)
			? selectedCols.filter((c) => c !== col)
			: [...selectedCols, col];
	}

	async function loadSchema() {
		if (!id.trim()) return;
		loadingSchema = true;
		error = '';
		schema = null;
		selectedCols = [];
		try {
			const meta = await readParquetMetadata(path);
			schema = { columns: meta.columns, rows: meta.rows };
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			loadingSchema = false;
		}
	}

	async function fetchRows(): Promise<{ cols: string[]; rows: Record<string, unknown>[] }> {
		const cols = effectiveCols;
		const opts: Parameters<typeof readParquetRows>[1] = { columns: cols };
		if (tail && schema) {
			opts.rowStart = Math.max(0, schema.rows - tail);
			opts.rowEnd = schema.rows;
		}
		const { rows } = await readParquetRows(path, opts);
		return { cols, rows };
	}

	function fileStem(ext: string): string {
		const slug = `${selectedDir.replace(/\//g, '_')}_${id.trim()}`;
		return `dartlab_${slug}${tail ? `_tail${tail}` : ''}.${ext}`;
	}

	function rowsToGrid(cols: string[], rows: Record<string, unknown>[]): GridCell[][] {
		const header: GridCell[] = cols.map((c) => ({ text: c, colspan: 1, rowspan: 1, align: '', isHeader: true }));
		const body: GridCell[][] = rows.map((r) =>
			cols.map((c) => ({ text: r[c] == null ? '' : String(r[c]), colspan: 1, rowspan: 1, align: '', isHeader: false }))
		);
		return [header, ...body];
	}

	async function downloadCsvFile() {
		working = 'csv';
		error = '';
		try {
			const { cols, rows } = await fetchRows();
			downloadCsv(fileStem('csv'), cols, rows);
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			working = '';
		}
	}

	async function downloadXlsxFile() {
		working = 'xlsx';
		error = '';
		try {
			const { cols, rows } = await fetchRows();
			const bytes = buildWorkbook([{ label: id.trim() || selectedDir, grid: rowsToGrid(cols, rows) }]);
			downloadBlob(bytes, fileStem('xlsx'), XLSX_MIME);
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			working = '';
		}
	}

	async function copyLive() {
		try {
			await navigator.clipboard.writeText(liveUrl);
		} catch {
			/* clipboard 미지원 — 무시 */
		}
	}
</script>

<svelte:head><title>데이터 다운로드 센터 · DartLab</title></svelte:head>

<main class="dc">
	<header class="dc-head">
		<h1>데이터 다운로드 센터</h1>
		<p>
			HuggingFace 공개 데이터(parquet)를 브라우저에서 바로 <b>Excel·CSV</b>로 받습니다. 서버 0 — 데이터가
			브라우저로 직접 와서 변환됩니다. <span class="muted">Tier1 (라이브 시트 연결은 곧)</span>
		</p>
	</header>

	<section class="card">
		<div class="row">
			<label class="field">
				<span>데이터셋</span>
				<select bind:value={selectedDir} onchange={onDirChange}>
					{#each DOWNLOAD_CATALOG as e (e.dir)}
						<option value={e.dir}>{e.label} — {e.dir}</option>
					{/each}
				</select>
			</label>
			<label class="field id">
				<span>ID <em>({entry.shardKind})</em></span>
				<input
					bind:value={id}
					placeholder={PLACEHOLDER[entry.shardKind] ?? 'ID'}
					onkeydown={(ev) => ev.key === 'Enter' && loadSchema()}
				/>
			</label>
			<button class="btn" onclick={loadSchema} disabled={loadingSchema || !id.trim()}>
				{loadingSchema ? '조회 중…' : '조회'}
			</button>
		</div>
		<div class="hint">경로 <code>{path}</code></div>
	</section>

	{#if error}
		<div class="err">⚠ {error}</div>
	{/if}

	{#if schema}
		<section class="card">
			<div class="schema-head">
				<span><b>{schema.rows.toLocaleString()}</b> 행 · <b>{schema.columns.length}</b> 열</span>
				<label class="tail">
					최근 N행
					<input type="number" min="1" bind:value={tail} placeholder="전체" />
				</label>
			</div>

			<div class="cols">
				<div class="cols-head">
					컬럼 선택 <span class="muted">(미선택 = 전체)</span>
					{#if selectedCols.length}
						<button class="link" onclick={() => (selectedCols = [])}>초기화</button>
					{/if}
				</div>
				<div class="chips">
					{#each schema.columns as col (col)}
						<button
							class="chip"
							class:on={selectedCols.includes(col)}
							onclick={() => toggleCol(col)}>{col}</button
						>
					{/each}
				</div>
			</div>

			<div class="estimate">
				받을 데이터 ≈ <b>{cellCount.toLocaleString()}</b> 셀
				({effectiveCols.length} 열 × {effectiveRows.toLocaleString()} 행)
			</div>

			<div class="actions">
				<button class="btn primary" onclick={downloadXlsxFile} disabled={!!working}>
					{working === 'xlsx' ? '생성 중…' : 'Excel (.xlsx)'}
				</button>
				<button class="btn primary" onclick={downloadCsvFile} disabled={!!working}>
					{working === 'csv' ? '생성 중…' : 'CSV'}
				</button>
			</div>
		</section>

		<section class="card live">
			<div class="live-head">
				라이브 링크 <span class="muted">구글시트 <code>=IMPORTDATA()</code> · 엑셀 웹에서 가져오기</span>
			</div>
			{#if isTier2Eligible(entry)}
				<div class="url-box">
					<code>{liveUrl}</code>
					<button class="btn small" onclick={copyLive}>복사</button>
				</div>
				{#if cellCount > CELL_CAP}
					<div class="warn">
						⚠ ≈{cellCount.toLocaleString()} 셀 — 시트 한도(~{CELL_CAP.toLocaleString()}) 초과. <b>컬럼을 줄이거나
						최근 N행</b>으로 좁히세요.
					</div>
				{/if}
				<div class="muted small">Tier2 라이브 워커 배포 후 활성됩니다 (현재 다운로드는 바로 가능).</div>
			{:else}
				<div class="muted">
					이 데이터셋({entry.shardKind})은 대형이라 라이브 시트 연결 대상이 아닙니다 — 위 <b>다운로드</b>를
					쓰거나, 회사 단위 데이터셋을 선택하세요.
				</div>
			{/if}
		</section>
	{/if}
</main>

<style>
	.dc {
		max-width: 880px;
		margin: 0 auto;
		padding: 40px 20px 80px;
		color: #e2e8f0;
		font-family:
			ui-sans-serif,
			system-ui,
			-apple-system,
			'Segoe UI',
			sans-serif;
	}
	.dc-head h1 {
		font-size: 26px;
		font-weight: 700;
		margin: 0 0 8px;
	}
	.dc-head p {
		color: #94a3b8;
		font-size: 14px;
		line-height: 1.6;
		margin: 0;
	}
	.muted {
		color: #64748b;
	}
	.small {
		font-size: 11px;
	}
	.card {
		margin-top: 18px;
		padding: 18px;
		background: #0a0e18;
		border: 1px solid #1e2433;
		border-radius: 10px;
	}
	.row {
		display: flex;
		gap: 12px;
		align-items: flex-end;
		flex-wrap: wrap;
	}
	.field {
		display: flex;
		flex-direction: column;
		gap: 6px;
		font-size: 12px;
		color: #94a3b8;
	}
	.field.id {
		flex: 1;
		min-width: 180px;
	}
	.field em {
		color: #f59e0b;
		font-style: normal;
	}
	select,
	input {
		background: #050811;
		border: 1px solid #263145;
		border-radius: 6px;
		color: #e2e8f0;
		padding: 9px 10px;
		font-size: 13px;
		font-family: inherit;
	}
	select {
		max-width: 420px;
	}
	input:focus,
	select:focus {
		outline: none;
		border-color: #f59e0b;
	}
	.btn {
		background: #1e2433;
		border: 1px solid #2d3748;
		border-radius: 6px;
		color: #e2e8f0;
		padding: 9px 16px;
		font-size: 13px;
		font-weight: 600;
		cursor: pointer;
		white-space: nowrap;
	}
	.btn:hover:not(:disabled) {
		border-color: #f59e0b;
		color: #f59e0b;
	}
	.btn:disabled {
		opacity: 0.5;
		cursor: default;
	}
	.btn.primary {
		background: rgba(245, 158, 11, 0.12);
		border-color: rgba(245, 158, 11, 0.45);
		color: #fbbf24;
	}
	.btn.small {
		padding: 5px 10px;
		font-size: 12px;
	}
	.hint {
		margin-top: 10px;
		font-size: 11px;
		color: #475569;
	}
	code {
		font-family: ui-monospace, 'SF Mono', Menlo, monospace;
		font-size: 12px;
		color: #cbd5e1;
	}
	.err {
		margin-top: 14px;
		padding: 10px 14px;
		background: rgba(239, 68, 68, 0.1);
		border: 1px solid rgba(239, 68, 68, 0.4);
		border-radius: 8px;
		color: #fca5a5;
		font-size: 13px;
	}
	.schema-head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		font-size: 13px;
		flex-wrap: wrap;
		gap: 10px;
	}
	.tail {
		font-size: 12px;
		color: #94a3b8;
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.tail input {
		width: 90px;
		padding: 6px 8px;
	}
	.cols {
		margin-top: 16px;
	}
	.cols-head {
		font-size: 12px;
		color: #94a3b8;
		margin-bottom: 8px;
	}
	.link {
		background: none;
		border: none;
		color: #f59e0b;
		cursor: pointer;
		font-size: 11px;
		margin-left: 6px;
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.chip {
		background: #050811;
		border: 1px solid #263145;
		border-radius: 5px;
		color: #94a3b8;
		padding: 4px 9px;
		font-size: 12px;
		cursor: pointer;
		font-family: ui-monospace, monospace;
	}
	.chip.on {
		background: rgba(245, 158, 11, 0.14);
		border-color: rgba(245, 158, 11, 0.5);
		color: #fbbf24;
	}
	.estimate {
		margin-top: 16px;
		font-size: 12px;
		color: #94a3b8;
	}
	.actions {
		margin-top: 14px;
		display: flex;
		gap: 10px;
	}
	.live-head {
		font-size: 13px;
		margin-bottom: 12px;
	}
	.url-box {
		display: flex;
		gap: 8px;
		align-items: center;
		background: #050811;
		border: 1px solid #263145;
		border-radius: 6px;
		padding: 8px 10px;
	}
	.url-box code {
		flex: 1;
		overflow-x: auto;
		white-space: nowrap;
	}
	.warn {
		margin-top: 10px;
		font-size: 12px;
		color: #fbbf24;
	}
	.live .muted.small {
		margin-top: 8px;
		display: block;
	}
</style>
