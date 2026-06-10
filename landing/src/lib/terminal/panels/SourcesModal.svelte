<script lang="ts">
	// 데이터 출처 모달 — 터미널 전 패널의 원천·갱신주기·라이선스를 한 표로 명시 (공공누리 출처표시 의무 포함).
	import type { Lang } from '../data/types';
	import { GOV_ATTRIBUTION } from '../data/govPrice';
	import { MACRO_ATTRIBUTION } from '../data/macroSeries';

	interface Props {
		lang: Lang;
		open: boolean;
		onClose: () => void;
	}
	let { lang, open, onClose }: Props = $props();

	interface SourceRow {
		data: { kr: string; en: string };
		org: { kr: string; en: string };
		path: string; // HF 산출물 경로 (mono)
		cadence: { kr: string; en: string };
		license: { kr: string; en: string };
	}
	const ROWS: SourceRow[] = [
		{
			data: { kr: '주가·지수 일별시세 (OHLCV)', en: 'Daily prices & indices (OHLCV)' },
			org: { kr: '금융위원회·한국거래소 — 공공데이터포털', en: 'FSC · KRX — data.go.kr' },
			path: 'gov/prices · gov/indices',
			cadence: { kr: '매 영업일 EOD', en: 'EOD each trading day' },
			license: { kr: '공공누리 — 출처표시', en: 'KOGL — attribution' }
		},
		{
			data: { kr: '공시 원문·목록 (정기·수시)', en: 'Filings (regular · non-regular)' },
			org: { kr: '금융감독원 DART (OpenDART)', en: 'FSS DART (OpenDART)' },
			path: 'panel · allFilings',
			cadence: { kr: '매일 동기화', en: 'daily sync' },
			license: { kr: 'DART 이용약관', en: 'DART terms' }
		},
		{
			data: { kr: '재무제표 (분기·연간·TTM)', en: 'Financial statements (Q · FY · TTM)' },
			org: { kr: 'DART 정기보고서 XBRL', en: 'DART XBRL filings' },
			path: 'dart/finance/{code}',
			cadence: { kr: '분기 (공시 후)', en: 'quarterly (post-filing)' },
			license: { kr: 'DART 이용약관', en: 'DART terms' }
		},
		{
			data: { kr: '정기보고서 팩트 (배당·자사주·임원·대주주·회사채)', en: 'Report facts (dividends · buyback · officers · owners · bonds)' },
			org: { kr: 'DART OpenAPI 정기보고서', en: 'DART OpenAPI report' },
			path: 'report',
			cadence: { kr: '분기', en: 'quarterly' },
			license: { kr: 'DART 이용약관', en: 'DART terms' }
		},
		{
			data: { kr: '한국 매크로 (환율·기준금리·CPI·수출·경기지수)', en: 'KR macro (FX · base rate · CPI · exports · CLI)' },
			org: { kr: '한국은행 ECOS', en: 'Bank of Korea ECOS' },
			path: 'macro/ecos',
			cadence: { kr: '일·월 (지표별)', en: 'daily · monthly' },
			license: { kr: 'ECOS 오픈API', en: 'ECOS open API' }
		},
		{
			data: { kr: '미국 매크로 (국채금리·연방금리·CPI·고용)', en: 'US macro (UST · Fed funds · CPI · labor)' },
			org: { kr: 'FRED (세인트루이스 연준)', en: 'FRED (St. Louis Fed)' },
			path: 'macro/fred',
			cadence: { kr: '일·주·월 (지표별)', en: 'daily · weekly · monthly' },
			license: { kr: 'FRED API 약관', en: 'FRED API terms' }
		},
		{
			data: { kr: '생태계·등급·산업분류·공급망', en: 'Ecosystem · grades · industry map · supply chain' },
			org: { kr: 'dartlab 자체 구축 (공시 파싱)', en: 'dartlab-built (parsed filings)' },
			path: 'ecosystem · map',
			cadence: { kr: '분기', en: 'quarterly' },
			license: { kr: '파생 산출물', en: 'derived artifact' }
		},
		{
			data: { kr: '신용 dCR·적정주가·종합판정·백테스트', en: 'dCR credit · fair value · verdict · backtest' },
			org: { kr: 'dartlab 엔진 — 브라우저 계산', en: 'dartlab engine — in-browser' },
			path: '—',
			cadence: { kr: '즉시 (실데이터 입력)', en: 'instant (from real data)' },
			license: { kr: '비공식 · 투자조언 아님', en: 'unofficial · not advice' }
		}
	];
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	function onKey(e: KeyboardEvent) {
		if (e.key === 'Escape') onClose();
	}
</script>

<svelte:window onkeydown={open ? onKey : undefined} />

{#if open}
	<div class="scrimWrap" role="presentation" onclick={onClose}>
		<div class="scrModal srcModal" role="dialog" aria-modal="true" aria-label={T('데이터 출처', 'Data sources')} onclick={(e) => e.stopPropagation()}>
			<div class="scrHead">
				<span class="scrTitle">{T('데이터 출처', 'DATA SOURCES')}</span>
				<span class="scrCount">{ROWS.length} {T('원천 · 전 데이터 EOD/배치 (실시간 아님)', 'sources · all EOD/batch (not realtime)')}</span>
				<button class="scrClose" onclick={onClose} aria-label="close">✕</button>
			</div>
			<div class="srcBody">
				<table class="scrTable srcTable">
					<thead><tr>
						<th class="l">{T('데이터', 'DATA')}</th>
						<th class="l">{T('원천 기관', 'SOURCE')}</th>
						<th class="l">{T('산출물', 'ARTIFACT')}</th>
						<th class="l">{T('갱신', 'CADENCE')}</th>
						<th class="l">{T('라이선스·조건', 'LICENSE')}</th>
					</tr></thead>
					<tbody>
						{#each ROWS as r (r.path + r.data.en)}
							<tr class="srcRow">
								<td class="l"><b>{T(r.data.kr, r.data.en)}</b></td>
								<td class="l">{T(r.org.kr, r.org.en)}</td>
								<td class="l mono srcPath">{r.path}</td>
								<td class="l">{T(r.cadence.kr, r.cadence.en)}</td>
								<td class="l srcLic">{T(r.license.kr, r.license.en)}</td>
							</tr>
						{/each}
					</tbody>
				</table>
				<div class="srcNotes">
					<div class="srcNote">{GOV_ATTRIBUTION} · {MACRO_ATTRIBUTION}</div>
					<div class="srcNote">{T('호스팅: HuggingFace dataset', 'Hosting: HuggingFace dataset')} <span class="mono">eddmpython/dartlab-data</span> ({T('공개', 'public')})</div>
					<div class="srcNote dim">{T('본 화면의 모든 수치는 공시·공공 데이터 기반 정보 제공 목적이며 투자 권유가 아닙니다. 투자 판단의 책임은 이용자에게 있습니다.', 'All figures are for information only, built from public filings and open data — not investment advice.')}</div>
				</div>
			</div>
		</div>
	</div>
{/if}
