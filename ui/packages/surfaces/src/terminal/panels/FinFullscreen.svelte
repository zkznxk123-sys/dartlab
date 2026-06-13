<script lang="ts">
	// 재무제표 분석 전체화면 — 버틀러식 상단 탭 + 탭별 밀집 그래프 (구역 규칙: 그래프는 중앙).
	// 종합 탭 = 기존 16 재무카드 전부(기본적으로 다 보이게). 나머지 탭 = finance 심화 카드
	// (terminalFinance.tabCards, 모드 토글 동작) + report·교차 카드(finTabs.ts, 연 축 고정, lazy).
	import { untrack } from 'svelte';
	import type { AuditYear, FinMode, TerminalFinanceBundle, TopExecPay } from '@dartlab/ui-contracts';
	import { useDartLabRuntime } from '@dartlab/ui-runtime';
	import type { Company, Lang } from '../data/types';
	import MiniFinChart from '../charts/MiniFinChart.svelte';
	import AuditStrip from '../charts/AuditStrip.svelte';
	import { FS_TABS, type TabCard } from '../data/finTabs';

	interface Props {
		co: Company;
		lang: Lang;
		bundle: TerminalFinanceBundle | null;
		mode: FinMode;
		onMode: (m: FinMode) => void;
		onClose: () => void;
	}
	let { co, lang, bundle, mode, onMode, onClose }: Props = $props();
	const rt = useDartLabRuntime();
	const finModeLabel: Record<FinMode, string> = { ttm: 'TTM', quarter: '분기', annual: '연간' };

	let tab = $state('all');
	// report 카드 lazy 캐시. ⛔ self-dep 가드: 로드 effect 는 reportCards 를 untrack 으로만 읽는다
	// (tracked read+write = effect 재실행 → 진행 중 로드 취소 버그). 회사 전환은 epoch 로 식별.
	let reportCards = $state<Record<string, TabCard[] | 'loading'>>({});
	// 부가 패널 (감사 스트립 · 임원 보수 표) — reportCards 와 동일한 epoch 가드·lazy 패턴
	let auditTrail = $state<AuditYear[] | 'loading' | 'empty' | null>(null);
	let execTop = $state<TopExecPay | 'loading' | 'empty' | null>(null);
	let epoch = 0; // 비반응 — 회사 전환 세대
	$effect(() => {
		void co.code;
		epoch++;
		tab = 'all';
		reportCards = {};
		auditTrail = null;
		execTop = null;
	});
	$effect(() => {
		const t = tab;
		const code = co.code;
		const b = bundle; // null → 재무 도착 시 재실행 (교차 카드가 annual statements 필요)
		const def = FS_TABS.find((d) => d.key === t);
		if (!def?.load || b == null) return;
		if (untrack(() => reportCards[t])) return;
		const myEpoch = untrack(() => epoch);
		reportCards[t] = 'loading';
		def.load(code, b, rt.report).then((cards) => {
			if (epoch !== myEpoch) return; // 회사가 바뀜 — 옛 결과 폐기
			reportCards[t] = cards;
		});
	});
	$effect(() => {
		const code = co.code;
		if (tab !== 'debt' || untrack(() => auditTrail) != null) return;
		const myEpoch = untrack(() => epoch);
		auditTrail = 'loading';
		rt.report.auditTrail(code).then((tr) => {
			if (epoch !== myEpoch) return;
			auditTrail = tr && tr.length ? tr : 'empty';
		});
	});
	$effect(() => {
		const code = co.code;
		if (tab !== 'people' || untrack(() => execTop) != null) return;
		const myEpoch = untrack(() => epoch);
		execTop = 'loading';
		rt.report.topExecPay(code).then((tp) => {
			if (epoch !== myEpoch) return;
			execTop = tp && tp.rows.length ? tp : 'empty';
		});
	});
	const auditList = $derived(Array.isArray(auditTrail) ? auditTrail : null);
	const execTopData = $derived(execTop !== null && execTop !== 'loading' && execTop !== 'empty' ? execTop : null);

	const finData = $derived(bundle ? (bundle.views[mode] ?? null) : null);
	const activeDef = $derived(FS_TABS.find((d) => d.key === tab) ?? null);

	// 원표(전 기간 와이드 테이블)는 우측 재무 패널 ⤢ → FinTablesModal 로 이동 (운영자 결정 — 전체화면 탭 아님)
	// finance 심화 카드 (동기·모드 반응) — 전 시리즈 null 카드는 숨김 (waterfall 은 steps, heatmap 은 heat 기준)
	const finCards = $derived.by(() => {
		if (tab === 'all' || !finData || !activeDef?.finKey) return [];
		return finData.tabCards[activeDef.finKey].filter((c) =>
			c.kind === 'waterfall' ? (c.steps?.some((s) => s.value != null) ?? false)
			: c.kind === 'heatmap' ? (c.heat?.vals.some((r) => r.some((v) => v != null)) ?? false)
			: c.series.some((s) => s.data.some((v) => v != null))
		);
	});
	const reportPart = $derived(tab === 'all' ? null : reportCards[tab]);
	const reportLoading = $derived(activeDef?.load != null && (reportPart === 'loading' || reportPart === undefined));
	const reportList = $derived(Array.isArray(reportPart) ? reportPart : []);
	const tabEmpty = $derived(
		tab !== 'all' && !finCards.length && !reportLoading && !reportList.length &&
		!(tab === 'debt' && (auditList || auditTrail === 'loading')) &&
		!(tab === 'people' && (execTopData || execTop === 'loading'))
	);

	$effect(() => {
		const onKey = (ev: KeyboardEvent) => {
			if (ev.key === 'Escape') onClose();
		};
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});
</script>

<div class="finFs" role="dialog" aria-label={lang === 'en' ? 'Financial analysis fullscreen' : '재무제표 분석 전체화면'}>
	<div class="finFsBar">
		<span class="finFsTitle">{co.name.kr} <i>{co.code}</i> · {lang === 'en' ? 'FINANCIAL ANALYSIS' : '재무제표 분석'}</span>
		<nav class="finFsTabs">
			<button class={'finFsTab ' + (tab === 'all' ? 'on' : '')} onclick={() => (tab = 'all')}>{lang === 'en' ? 'OVERVIEW' : '종합'}</button>
			{#each FS_TABS as t (t.key)}
				<button class={'finFsTab ' + (tab === t.key ? 'on' : '')} onclick={() => (tab = t.key)}>{lang === 'en' ? t.label.en : t.label.kr}</button>
			{/each}
		</nav>
		{#if (tab === 'all' || activeDef?.finKey) && bundle && bundle.modes.length > 1}
			<span class="segGroup mini">{#each bundle.modes as m (m)}<button class={mode === m ? 'seg on' : 'seg'} onclick={() => onMode(m)}>{lang === 'en' ? m.toUpperCase() : finModeLabel[m]}</button>{/each}</span>
		{/if}
		<button class="finFsClose" onclick={onClose} title={lang === 'en' ? 'close (ESC)' : '닫기 (ESC)'}>✕</button>
	</div>
	<div class="finFsBody">
		{#if activeDef?.q}
			<div class="finFsQ">{activeDef.q}</div>
		{/if}
		{#if tab === 'all'}
			{#if finData}
				<div class="finFsGrid">
					{#each finData.cards as card (card.key)}
						<div class="finMini"><MiniFinChart {card} periods={finData.periods} /></div>
					{/each}
				</div>
			{:else}
				<div class="chartLoad" style="height:140px">{lang === 'en' ? 'loading financials …' : '재무제표 불러오는 중 …'}</div>
			{/if}
		{:else if tabEmpty}
			<div class="storyEmpty">{lang === 'en' ? 'No data for this tab.' : '이 회사는 해당 탭 데이터가 없습니다.'}</div>
		{:else}
			{#if tab === 'debt' && auditList}
				<AuditStrip trail={auditList} />
			{/if}
			<div class="finFsGrid">
				{#each finCards as card (card.key)}
					<div class="finMini"><MiniFinChart {card} periods={finData!.periods} /></div>
				{/each}
				{#each reportList as tc (tc.card.key)}
					<div class="finMini"><MiniFinChart card={tc.card} periods={tc.periods} /></div>
				{/each}
				{#if tab === 'people' && execTopData}
					<div class="finMini execTopCell">
						<div class="mfcHead">
							<span class="mfcTitle">개별 임원 보수 Top {execTopData.rows.length} · FY{execTopData.year.slice(2)}</span>
						</div>
						<table class="execTopTbl">
							<thead>
								<tr><th>{lang === 'en' ? 'Name' : '이름'}</th><th>{lang === 'en' ? 'Title' : '직위'}</th><th class="num">{lang === 'en' ? 'Pay (100M)' : '보수(억)'}</th><th class="num">{lang === 'en' ? 'vs avg' : '평균 대비'}</th></tr>
							</thead>
							<tbody>
								{#each execTopData.rows as r (r.name + r.title)}
									<tr>
										<td>{r.name}</td>
										<td class="execTopTitle">{r.title}</td>
										<td class="num mono">{(r.pay / 1e8).toFixed(1)}</td>
										<td class="num mono">{execTopData.avgPay != null && execTopData.avgPay > 0 ? '×' + (r.pay / execTopData.avgPay).toFixed(1) : '—'}</td>
									</tr>
								{/each}
							</tbody>
						</table>
						<div class="execTopNote">5억원 이상 공시 대상 · 평균 = 이사·감사 1인평균 보수</div>
					</div>
				{/if}
			</div>
			{#if reportLoading}
				<div class="chartLoad" style="height:60px">{lang === 'en' ? 'loading report series …' : '정기보고서 시계열 불러오는 중 …'}</div>
			{/if}
			{#if activeDef?.note && !reportLoading}
				<div class="finFsNote">{activeDef.note}</div>
			{/if}
		{/if}
	</div>
</div>
