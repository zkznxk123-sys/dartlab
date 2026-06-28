<script lang="ts">
	// 터미널 상단 「데이터」 버튼 — 이 회사 데이터 공개 다운로드. viewer DataDownloadMenu 와 동형(친화 Excel +
	// 원본 parquet + 전체 데이터셋 + 데이터 정책). 터미널 자체 finance 포트로 만들어 viewer 의존 0.
	import type { DartLabRuntime, StmtKind } from '@dartlab/ui-contracts';
	import { hfUrl } from '@dartlab/ui-runtime/data/parquet/hfRange';
	import { buildWorkbook, downloadBlob, type GridCell } from '../../downloadExport';
	import type { Lang } from '../lib/types';

	interface Props {
		runtime: DartLabRuntime;
		code: string;
		corpName: string;
		lang: Lang;
	}
	let { runtime, code, corpName, lang }: Props = $props();

	const XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
	const DATASET_URL = 'https://huggingface.co/datasets/eddmpython/dartlab-data';
	const en = $derived(lang === 'en');
	// 6자리 숫자 = KR(DART), 그 외 = US(EDGAR). 원본 parquet 경로·정책 문구 분기.
	const isUs = $derived(!/^\d{6}$/.test(code));
	const panelUrl = $derived(hfUrl(`${isUs ? 'edgar' : 'dart'}/panel/${code}.parquet`));
	const financeUrl = $derived(hfUrl(`${isUs ? 'edgar/financeStmt' : 'dart/finance'}/${code}.parquet`));
	const termsUrl = $derived(
		isUs ? 'https://www.sec.gov/os/accessing-edgar-data' : 'https://opendart.fss.or.kr/intro/terms.do'
	);

	let open = $state(false);
	let busy = $state(false);

	const hc = (t: string): GridCell => ({ text: t, colspan: 1, rowspan: 1, align: '', isHeader: true });
	const tc = (t: string): GridCell => ({ text: t, colspan: 1, rowspan: 1, align: '', isHeader: false });

	async function downloadFinance() {
		if (busy) return;
		busy = true;
		try {
			const bundle = await runtime.finance.bundle(code);
			const view = bundle?.views[bundle.defaultMode] ?? bundle?.views.annual ?? bundle?.views.quarter ?? null;
			if (!view) return;
			const periods = view.periods;
			const unit = bundle?.currency === 'USD' ? '$B' : '조원';
			const kinds: { k: StmtKind; label: string }[] = [
				{ k: 'IS', label: en ? 'Income' : '손익계산서' },
				{ k: 'BS', label: en ? 'Balance' : '재무상태표' },
				{ k: 'CF', label: en ? 'Cashflow' : '현금흐름표' }
			];
			const sheets = kinds
				.map(({ k, label }) => {
					const rows = view.statements[k] ?? [];
					const grid: GridCell[][] = [
						[hc(en ? 'Account' : '계정'), ...periods.map(hc)],
						...rows.map((r) => [tc(en ? r.en : r.kr), ...r.values.map((v) => tc(v == null ? '' : String(v)))])
					];
					return { label, grid, unit };
				})
				.filter((s) => s.grid.length > 1);
			if (view.ratios?.length) {
				sheets.push({
					label: en ? 'Ratios' : '주요비율',
					grid: [
						[hc(en ? 'Metric' : '지표'), ...periods.map(hc)],
						...view.ratios.map((r) => [tc(en ? r.en : r.kr), ...r.values.map((v) => tc(v == null ? '' : String(v)))])
					],
					unit: ''
				});
			}
			if (!sheets.length) return;
			downloadBlob(buildWorkbook(sheets), `${corpName || code}_${en ? 'financials' : '재무제표'}.xlsx`, XLSX_MIME);
		} finally {
			busy = false;
		}
	}
</script>

<div class="dataDl">
	<button class={'hdrLink' + (open ? ' on' : '')} onclick={() => (open = !open)} title={en ? 'Download this company data (public)' : '이 회사 데이터 공개 다운로드'}>
		{en ? 'Data' : '데이터'}
	</button>
	{#if open}
		<button class="dlBackdrop" aria-label="close" onclick={() => (open = false)}></button>
		<div class="dlPop">
			<div class="dpH">{corpName || code} · {en ? 'open data' : '공개 데이터'}</div>
			<div class="dpSub">{en ? 'easy formats — Excel · Sheets' : '보기 쉬운 형식 — Excel · Sheets · 메모장'}</div>
			<button class="dpLink dpBtn" onclick={downloadFinance} disabled={busy}>
				{en ? 'Financials (IS·BS·CF)' : '재무제표 (손익·재무상태·현금흐름)'}
				<span class="dpExt">{busy ? (en ? 'building…' : '생성 중…') : 'Excel'}</span>
			</button>
			<div class="dpSub">{en ? 'raw — for developers (parquet)' : '원본 — 개발자용 (parquet)'}</div>
			<a class="dpLink" href={panelUrl} download>{en ? 'Disclosure panel' : '공시 panel'} <span class="dpExt">.parquet</span></a>
			<a class="dpLink" href={financeUrl} download>{en ? 'Financials' : '재무제표'} <span class="dpExt">.parquet</span></a>
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
		width: 318px;
		display: flex;
		flex-direction: column;
		gap: 4px;
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
		margin-top: 4px;
		font-size: 9px;
		color: #475569;
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}
	.dpLink {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 6px 9px;
		border: 1px solid #1e2433;
		border-radius: 5px;
		color: #e2e8f0;
		font-size: 12px;
		text-decoration: none;
		background: none;
		font: inherit;
		cursor: pointer;
		text-align: left;
		width: 100%;
	}
	.dpLink:hover {
		border-color: var(--amber, #f59e0b);
		color: var(--amber, #f59e0b);
		background: rgba(245, 158, 11, 0.06);
	}
	.dpBtn {
		background: rgba(245, 158, 11, 0.1);
		border-color: rgba(245, 158, 11, 0.4);
		color: #f1f5f9;
	}
	.dpBtn:disabled {
		opacity: 0.5;
		cursor: default;
	}
	.dpExt {
		font-size: 10px;
		color: #64748b;
	}
	.dpDs {
		color: #cbd5e1;
	}
	.dpPolicy {
		display: flex;
		flex-direction: column;
		gap: 4px;
		margin-top: 5px;
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
