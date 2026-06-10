<script lang="ts">
	// 재무제표 분석 전체화면 — 버틀러식 상단 탭 + 탭별 밀집 그래프 (구역 규칙: 그래프는 중앙).
	// 종합 탭 = 기존 16 재무카드 전부(기본적으로 다 보이게). 나머지 탭 = finance 심화 카드
	// (terminalFinance.tabCards, 모드 토글 동작) + report·교차 카드(finTabs.ts, 연 축 고정, lazy).
	import { untrack } from 'svelte';
	import type { Company, Lang } from '../data/types';
	import type { TerminalFinanceBundle, FinMode } from '../data/terminalFinance';
	import MiniFinChart from '../charts/MiniFinChart.svelte';
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
	const finModeLabel: Record<FinMode, string> = { ttm: '분기 TTM', quarter: '분기', annual: '연간' };

	let tab = $state('all');
	// report 카드 lazy 캐시. ⛔ self-dep 가드: 로드 effect 는 reportCards 를 untrack 으로만 읽는다
	// (tracked read+write = effect 재실행 → 진행 중 로드 취소 버그). 회사 전환은 epoch 로 식별.
	let reportCards = $state<Record<string, TabCard[] | 'loading'>>({});
	let epoch = 0; // 비반응 — 회사 전환 세대
	$effect(() => {
		void co.code;
		epoch++;
		tab = 'all';
		reportCards = {};
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
		def.load(code, b).then((cards) => {
			if (epoch !== myEpoch) return; // 회사가 바뀜 — 옛 결과 폐기
			reportCards[t] = cards;
		});
	});

	const finData = $derived(bundle ? (bundle.views[mode] ?? null) : null);
	const activeDef = $derived(FS_TABS.find((d) => d.key === tab) ?? null);
	// finance 심화 카드 (동기·모드 반응) — 전 시리즈 null 카드는 숨김
	const finCards = $derived.by(() => {
		if (tab === 'all' || !finData || !activeDef?.finKey) return [];
		return finData.tabCards[activeDef.finKey].filter((c) => c.series.some((s) => s.data.some((v) => v != null)));
	});
	const reportPart = $derived(tab === 'all' ? null : reportCards[tab]);
	const reportLoading = $derived(activeDef?.load != null && (reportPart === 'loading' || reportPart === undefined));
	const reportList = $derived(Array.isArray(reportPart) ? reportPart : []);
	const tabEmpty = $derived(tab !== 'all' && !finCards.length && !reportLoading && !reportList.length);

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
			<div class="finFsGrid">
				{#each finCards as card (card.key)}
					<div class="finMini"><MiniFinChart {card} periods={finData!.periods} /></div>
				{/each}
				{#each reportList as tc (tc.card.key)}
					<div class="finMini"><MiniFinChart card={tc.card} periods={tc.periods} /></div>
				{/each}
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
