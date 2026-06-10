<script lang="ts">
	import Header from '$lib/components/sections/Header.svelte';
	import {
		readParquetMetadata,
		readParquetRows,
		type RangeRequestStat
	} from '$lib/data/hfRange';

	type Stage = 'idle' | 'running' | 'done' | 'error';

	interface KrxPriceRow extends Record<string, unknown> {
		BAS_DD?: string | number | null;
		ISU_CD?: string | null;
		TDD_CLSPRC?: string | number | null;
		MKTCAP?: string | number | null;
	}

	interface ProbeResult {
		path: string;
		rowStart: number;
		rowEnd: number;
		rowsRead: number;
		latestDate: string;
		latestRows: number;
		codes: number;
		spark60Codes: number;
		transferredBytes: number;
		requests: number;
		durationMs: number;
	}

	const PRICE_COLUMNS = ['BAS_DD', 'ISU_CD', 'TDD_CLSPRC', 'MKTCAP'];

	let stage = $state<Stage>('idle');
	let errorMessage = $state('');
	let tailRows = $state(180_000);
	let targetYear = $state(new Date().getFullYear());
	let result = $state<ProbeResult | null>(null);
	let requests = $state<RangeRequestStat[]>([]);

	function num(value: unknown): number | null {
		if (value == null) return null;
		const n = Number(value);
		return Number.isFinite(n) ? n : null;
	}

	function normalizeDate(value: unknown): string {
		if (value == null) return '';
		return String(value);
	}

	function stockCode(isuCd: string | null | undefined): string {
		if (!isuCd) return '';
		return isuCd.startsWith('A') ? isuCd.slice(1) : isuCd;
	}

	async function runTailProbe() {
		stage = 'running';
		errorMessage = '';
		result = null;
		requests = [];
		const t0 = performance.now();
		try {
			const path = `gov/prices/date/${targetYear}.parquet`;
			const meta = await readParquetMetadata(path);
			const rowEnd = meta.rows;
			const rowStart = Math.max(0, rowEnd - tailRows);
			requests = [...meta.requests];

			const data = await readParquetRows<KrxPriceRow>(path, {
				columns: PRICE_COLUMNS,
				rowStart,
				rowEnd
			});
			requests = [...requests, ...data.requests];

			let latestDate = '';
			const byCode = new Map<string, number[]>();
			const latest = new Set<string>();

			for (const row of data.rows) {
				const date = normalizeDate(row.BAS_DD);
				if (date > latestDate) latestDate = date;
				const code = stockCode(row.ISU_CD);
				const close = num(row.TDD_CLSPRC);
				if (!code || close == null) continue;
				let values = byCode.get(code);
				if (!values) {
					values = [];
					byCode.set(code, values);
				}
				values.push(close);
			}

			for (const row of data.rows) {
				if (normalizeDate(row.BAS_DD) !== latestDate) continue;
				const code = stockCode(row.ISU_CD);
				if (code) latest.add(code);
			}

			const transferredBytes = requests.reduce((sum, req) => sum + req.bytes, 0);
			result = {
				path,
				rowStart,
				rowEnd,
				rowsRead: data.rows.length,
				latestDate,
				latestRows: latest.size,
				codes: byCode.size,
				spark60Codes: [...byCode.values()].filter((values) => values.length >= 60).length,
				transferredBytes,
				requests: requests.length,
				durationMs: performance.now() - t0
			};
			stage = 'done';
		} catch (err) {
			errorMessage = err instanceof Error ? err.message : String(err);
			stage = 'error';
		}
	}

	let totalBytes = $derived(requests.reduce((sum, req) => sum + req.bytes, 0));
</script>

<svelte:head>
	<title>Price Tail Probe · dartlab</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<Header context="landing" />

<main class="page">
	<section class="head">
		<div>
			<span class="eyebrow">lab · price runtime</span>
			<h1>KRX Tail Range Probe</h1>
		</div>
		<div class="actions">
			<label>
				<span>year</span>
				<input type="number" min="2020" max="2030" step="1" bind:value={targetYear} />
			</label>
			<label>
				<span>tail rows</span>
				<input type="number" min="3000" max="700000" step="1000" bind:value={tailRows} />
			</label>
			<button type="button" onclick={runTailProbe} disabled={stage === 'running'}>
				{stage === 'running' ? '측정 중' : 'Tail 측정'}
			</button>
		</div>
	</section>

	{#if errorMessage}
		<section class="panel error">{errorMessage}</section>
	{/if}

	<section class="summary">
		<div><span>stage</span><strong>{stage}</strong></div>
		<div><span>duration</span><strong>{result ? `${result.durationMs.toFixed(0)}ms` : '-'}</strong></div>
		<div><span>transferred</span><strong>{totalBytes.toLocaleString('ko-KR')} bytes</strong></div>
		<div><span>requests</span><strong>{requests.length}</strong></div>
	</section>

	<section class="panel">
		<h2>Result</h2>
		{#if result}
			<pre>{JSON.stringify(result, null, 2)}</pre>
		{:else}
			<p class="muted">현재 HF KRX parquet을 그대로 두고 tail row만 읽는 실험입니다.</p>
		{/if}
	</section>

	<section class="panel">
		<h2>Range Requests</h2>
		{#if requests.length === 0}
			<p class="muted">아직 요청이 없습니다.</p>
		{:else}
			<table>
				<thead><tr><th>status</th><th>range</th><th>bytes</th><th>ms</th></tr></thead>
				<tbody>
					{#each requests as req}
						<tr>
							<td>{req.status}</td>
							<td>{req.range ?? '-'}</td>
							<td>{req.bytes.toLocaleString('ko-KR')}</td>
							<td>{req.durationMs.toFixed(0)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</section>
</main>

<style>
	.page {
		min-height: 100vh;
		padding: 76px 20px 40px;
		background: #050811;
		color: #e5e7eb;
	}
	.head,
	.summary,
	.panel {
		max-width: 1180px;
		margin: 0 auto;
	}
	.head {
		display: flex;
		justify-content: space-between;
		align-items: flex-end;
		gap: 16px;
		padding-bottom: 18px;
		border-bottom: 1px solid #1e2433;
	}
	.eyebrow {
		color: #38bdf8;
		font-size: 11px;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
	}
	h1 {
		margin: 6px 0 0;
		font-size: 34px;
		letter-spacing: 0;
	}
	.actions {
		display: flex;
		align-items: end;
		gap: 8px;
	}
	label span {
		display: block;
		margin-bottom: 4px;
		color: #64748b;
		font-size: 11px;
		text-transform: uppercase;
	}
	input,
	button {
		height: 34px;
		border: 1px solid #263145;
		border-radius: 5px;
		background: #080d17;
		color: #e5e7eb;
		font: inherit;
	}
	input {
		width: 120px;
		padding: 0 8px;
	}
	button {
		border-color: #38bdf8;
		color: #38bdf8;
		padding: 0 12px;
		cursor: pointer;
	}
	button:disabled {
		opacity: 0.55;
		cursor: wait;
	}
	.summary {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: 8px;
		margin-top: 14px;
		margin-bottom: 12px;
	}
	.summary div,
	.panel {
		border: 1px solid #1e2433;
		border-radius: 7px;
		background: #080d17;
	}
	.summary div {
		padding: 12px;
	}
	.summary span {
		display: block;
		color: #64748b;
		font-size: 11px;
		text-transform: uppercase;
	}
	.summary strong {
		display: block;
		margin-top: 6px;
	}
	.panel {
		margin-bottom: 12px;
		padding: 14px;
	}
	.panel h2 {
		margin: 0 0 10px;
		font-size: 15px;
		letter-spacing: 0;
	}
	.muted {
		color: #64748b;
	}
	.error {
		margin-top: 12px;
		border-color: #ef4444;
		color: #fecaca;
	}
	pre {
		max-height: 320px;
		overflow: auto;
		margin: 0;
		color: #cbd5e1;
		font-size: 12px;
	}
	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 12px;
	}
	th,
	td {
		border-bottom: 1px solid #1e2433;
		padding: 6px;
		text-align: left;
	}
	td:nth-child(2) {
		max-width: 620px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-family: monospace;
		color: #94a3b8;
	}
</style>
