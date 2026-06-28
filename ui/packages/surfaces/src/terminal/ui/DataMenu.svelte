<script lang="ts">
	// 터미널 상단 「데이터」 — 이 회사의 *모든 공개 데이터셋*(DOWNLOAD_CATALOG, 이번에 배선한 노출 카탈로그)을
	// Excel·CSV 로 내려받는다. 브라우저가 parquet 직독→변환(서버 0). viewer 의 2~3종 복제가 아니라 카탈로그 전체.
	import type { DartLabRuntime } from '@dartlab/ui-contracts';
	import { DOWNLOAD_CATALOG } from '@dartlab/ui-runtime/data/catalog/downloadCatalog';
	import { hfUrl, readParquetRows } from '@dartlab/ui-runtime/data/parquet/hfRange';
	import { buildWorkbook, downloadBlob, downloadCsv, type GridCell } from '../../downloadExport';
	import type { Lang } from '../lib/types';

	interface Props {
		runtime: DartLabRuntime;
		code: string;
		corpName: string;
		lang: Lang;
	}
	let { code, corpName, lang }: Props = $props();

	const XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
	const DATASET_URL = 'https://huggingface.co/datasets/eddmpython/dartlab-data';
	const en = $derived(lang === 'en');
	// 6자리 숫자 = KR(DART/gov/krx), 그 외 = US(EDGAR).
	const isUs = $derived(!/^\d{6}$/.test(code));
	const termsUrl = $derived(
		isUs ? 'https://www.sec.gov/os/accessing-edgar-data' : 'https://opendart.fss.or.kr/intro/terms.do'
	);

	// 회사 단위(shardKind='company') 데이터셋만 — 시장(KR/US)에 맞는 dir. 짧은 라벨 + 파일경로.
	const LABELS: Record<string, string> = $derived.by(() => ({
		'dart/finance': en ? 'Financials' : '재무 데이터',
		'dart/panel': en ? 'Disclosure (wide)' : '공시 수평화',
		'dart/report': en ? 'Periodic reports' : '정기보고서',
		'gov/prices/company': en ? 'Daily prices + cap' : '일별 시세·시총',
		'krx/prices/company': en ? 'Daily prices (KRX)' : '일별 시세 (KRX)',
		'edgar/financeStmt': en ? 'Financials' : '재무 데이터',
		'edgar/panel': en ? 'Disclosure (wide)' : '공시 수평화',
		'edgar/prices/company': en ? 'Daily prices (OHLCV)' : '일별 시세 (OHLCV)',
		'edgar/tickers': en ? 'Ticker↔CIK map' : '식별자 맵'
	}));
	const datasets = $derived(
		DOWNLOAD_CATALOG.filter(
			(e) =>
				e.shardKind === 'company' &&
				// krx/prices/company 제외 — gov/prices/company(라이브·전종목)와 중복이고 회사별 미완(404 다수).
				e.dir !== 'krx/prices/company' &&
				(isUs ? e.dir.startsWith('edgar/') : e.dir.startsWith('dart/') || e.dir.startsWith('gov/'))
		)
	);

	let open = $state(false);
	let busy = $state(''); // `${dir}:${fmt}` 진행 중
	let err = $state('');

	const hc = (t: string): GridCell => ({ text: t, colspan: 1, rowspan: 1, align: '', isHeader: true });
	const tc = (t: string): GridCell => ({ text: t, colspan: 1, rowspan: 1, align: '', isHeader: false });
	function rowsToGrid(cols: string[], rows: Record<string, unknown>[]): GridCell[][] {
		return [
			cols.map(hc),
			...rows.map((r) => cols.map((c) => tc(r[c] == null ? '' : String(r[c]))))
		];
	}

	async function dl(dir: string, fmt: 'xlsx' | 'csv') {
		const key = `${dir}:${fmt}`;
		if (busy) return;
		busy = key;
		err = '';
		try {
			const { rows } = await readParquetRows(`${dir}/${code}.parquet`);
			if (!rows.length) {
				err = en ? 'no data for this company' : '이 회사 데이터 없음';
				return;
			}
			const cols = Object.keys(rows[0]);
			const label = LABELS[dir] ?? dir;
			const stem = `${corpName || code}_${label.replace(/[/ ()]/g, '')}`;
			if (fmt === 'csv') {
				downloadCsv(stem, cols, rows);
			} else {
				downloadBlob(buildWorkbook([{ label, grid: rowsToGrid(cols, rows) }]), `${stem}.xlsx`, XLSX_MIME);
			}
		} catch (e) {
			err = e instanceof Error ? e.message : String(e);
		} finally {
			busy = '';
		}
	}
</script>

<div class="dataDl">
	<button class={'hdrLink' + (open ? ' on' : '')} onclick={() => (open = !open)} title={en ? 'Download all data for this company' : '이 회사 전체 데이터 다운로드'}>
		{en ? 'Data' : '데이터'}
	</button>
	{#if open}
		<button class="dlBackdrop" aria-label="close" onclick={() => (open = false)}></button>
		<div class="dlPop">
			<div class="dpH">{corpName || code} · {en ? 'all open data' : '전체 공개 데이터'}</div>
			<div class="dpSub">{en ? 'easy formats — Excel · Sheets · Notepad' : '보기 쉬운 형식 — Excel · Sheets · 메모장'}</div>
			{#each datasets as d (d.dir)}
				<div class="dsRow">
					<span class="dsLabel">{LABELS[d.dir] ?? d.dir}<span class="dsDir">{d.dir}</span></span>
					<span class="dsBtns">
						<button class="dsBtn" onclick={() => dl(d.dir, 'xlsx')} disabled={!!busy}>{busy === `${d.dir}:xlsx` ? '…' : 'Excel'}</button>
						<button class="dsBtn" onclick={() => dl(d.dir, 'csv')} disabled={!!busy}>{busy === `${d.dir}:csv` ? '…' : 'CSV'}</button>
					</span>
				</div>
			{/each}
			{#if err}<div class="dsErr">⚠ {err}</div>{/if}
			<div class="dpSub">{en ? 'raw — for developers (parquet)' : '원본 — 개발자용 (parquet)'}</div>
			{#each datasets as d (d.dir)}
				<a class="dpRaw" href={hfUrl(`${d.dir}/${code}.parquet`)} download>{LABELS[d.dir] ?? d.dir} <span class="dpExt">.parquet</span></a>
			{/each}
			<a class="dpLink dpDs" href={DATASET_URL} target="_blank" rel="noreferrer">{en ? 'Full dataset (all companies) ↗' : '전체 데이터셋 (모든 회사) ↗'}</a>
			<div class="dpPolicy">
				<div>
					{en ? 'Source' : '원자료'} <b>{isUs ? 'SEC EDGAR' : 'DART 전자공시'}</b> · {en ? 'processed by' : '가공·수평화'}
					<b>dartlab</b> · {en ? 'served via HuggingFace public dataset' : '배포 HuggingFace 공개 데이터셋'}.
				</div>
				<div>
					{isUs ? (en ? 'U.S. government work (public domain)' : '미국 정부 저작물(퍼블릭 도메인)') : (en ? 'Public data (Korea Public Data Act)' : '공공데이터(공공데이터법)')}
					— {en ? 'free to use & redistribute, commercial or not' : '영리·비영리 자유 이용·재배포 가능'} ·
					<b>{en ? 'attribution appreciated' : '출처 표기 권장'}</b>.
				</div>
				<div class="dpWarn">⚠ {en ? 'Accuracy/completeness not guaranteed — not investment advice.' : '데이터 정확성·완전성 미보증(원자료는 공시제출인 책임) · 투자 판단·자문이 아닙니다'}.</div>
				<a class="dpTerms" href={termsUrl} target="_blank" rel="noreferrer">{isUs ? 'SEC EDGAR' : 'DART'} {en ? 'terms' : '이용약관'} ↗</a>
			</div>
		</div>
	{/if}
</div>

<style>
	.dataDl {
		position: relative;
		display: inline-flex;
	}
	.dlBackdrop {
		position: fixed;
		inset: 0;
		z-index: 60;
		background: transparent;
		border: 0;
		cursor: default;
	}
	.dlPop {
		position: absolute;
		top: calc(100% + 8px);
		right: 0;
		z-index: 61;
		width: 340px;
		max-height: 78vh;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		gap: 3px;
		padding: 11px;
		background: #0a0e18;
		border: 1px solid #263145;
		border-radius: 8px;
		box-shadow: 0 14px 36px rgba(0, 0, 0, 0.55);
	}
	.dpH {
		font-size: 11px;
		color: #cbd5e1;
		font-weight: 600;
	}
	.dpSub {
		margin-top: 5px;
		font-size: 9px;
		color: #475569;
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}
	.dsRow {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		padding: 4px 0 4px 2px;
	}
	.dsLabel {
		display: flex;
		flex-direction: column;
		font-size: 12px;
		color: #e2e8f0;
		line-height: 1.25;
	}
	.dsDir {
		font-size: 9px;
		color: #475569;
		font-family: ui-monospace, monospace;
	}
	.dsBtns {
		display: flex;
		gap: 5px;
		flex-shrink: 0;
	}
	.dsBtn {
		min-width: 46px;
		padding: 5px 9px;
		border: 1px solid rgba(245, 158, 11, 0.4);
		border-radius: 5px;
		background: rgba(245, 158, 11, 0.1);
		color: #fbbf24;
		font: inherit;
		font-size: 11px;
		font-weight: 600;
		cursor: pointer;
	}
	.dsBtn:hover:not(:disabled) {
		background: rgba(245, 158, 11, 0.2);
	}
	.dsBtn:disabled {
		opacity: 0.5;
		cursor: default;
	}
	.dsErr {
		font-size: 11px;
		color: #fca5a5;
		padding: 2px;
	}
	.dpRaw {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 4px 6px;
		border-radius: 4px;
		color: #94a3b8;
		font-size: 11px;
		text-decoration: none;
	}
	.dpRaw:hover {
		color: var(--amber, #f59e0b);
		background: rgba(245, 158, 11, 0.05);
	}
	.dpExt {
		font-size: 10px;
		color: #64748b;
		font-family: ui-monospace, monospace;
	}
	.dpLink {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 6px 9px;
		margin-top: 3px;
		border: 1px solid #1e2433;
		border-radius: 5px;
		color: #cbd5e1;
		font-size: 12px;
		text-decoration: none;
	}
	.dpLink:hover {
		border-color: var(--amber, #f59e0b);
		color: var(--amber, #f59e0b);
	}
	.dpPolicy {
		display: flex;
		flex-direction: column;
		gap: 4px;
		margin-top: 6px;
		padding-top: 7px;
		border-top: 1px solid #1e2433;
		font-size: 10px;
		line-height: 1.5;
		color: #94a3b8;
	}
	.dpPolicy b {
		color: #cbd5e1;
		font-weight: 600;
	}
	.dpWarn {
		color: #fbbf24;
	}
	.dpTerms {
		align-self: flex-start;
		color: var(--amber, #f59e0b);
		text-decoration: none;
	}
	.dpTerms:hover {
		text-decoration: underline;
	}
</style>
