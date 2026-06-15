<script lang="ts">
	// 일반(비전체화면) 모드 차트 크롬 — 기간 칩(좌상) + 드롭다운 4개(지표·그리기·표시·백테스트) + 전체화면.
	// 상태는 ChartCtl 단일 SSOT 공유 — 전체화면 리본(ChartRibbon)과 같은 인스턴스.
	import type { Lang } from '../lib/types';
	import { type ChartCtl, type IndexControl, OVERLAY_ALL, SUB_ALL, PERIODS, TFS, YMODES, CANDLES, DRAW_TOOLS, SUB_HINT, OVERLAY_HINT } from './chartState.svelte';
	import { MACRO_SERIES, KR_INDEX_PRESETS, US_INDEX_PRESETS } from '@dartlab/ui-contracts';
	import { ECON_COLORS } from './econOverlay';
	import { EVENT_CATS } from '../lib/eventRail';
	import { IND_DEFS, paramSummary } from './indicatorParams';
	import IndParamEditor from './IndParamEditor.svelte';
	import BtConfig from './BtConfig.svelte';

	interface Props {
		ctl: ChartCtl;
		lang: Lang;
		hasBand: boolean;
		railCatCounts?: Record<string, number>; // 이벤트 레일 카테고리별 건수 (필터 드롭다운 — 0 카테고리 숨김·카운트 표기)
		onDraw: (name: string) => void;
		onClearDraw: () => void;
		onSnapshot?: () => void; // PNG 저장 — 전체화면 전용 잠금 해제 (발견성)
		subject?: 'price' | 'index'; // 'index' = BT·매물대 비활성(지수는 거래 대상 아님, 01 §4.2-4.3)
		indexLine?: boolean; // US 지수(종가전용) = candleStyle 'area' 고정(세그먼트 disabled, 01 §3.6)
		indexCtl?: IndexControl; // 주가/지수 토글 + 지수 picker (CenterStack 소유 → 컨트롤 바 한 줄에 통합)
	}
	let { ctl, lang, hasBand, railCatCounts = {}, onDraw, onClearDraw, onSnapshot, subject = 'price', indexLine = false, indexCtl }: Props = $props();
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	const styleShown = $derived(indexLine ? 'area' : ctl.candleStyle); // US 지수면 'area'(라인) 강조 — disabled 세그먼트 정합
	let menu = $state<'none' | 'ind' | 'econ' | 'draw' | 'view' | 'bt' | 'rail'>('none');
	let editing = $state<string | null>(null); // IND 메뉴 내 인라인 파라미터 편집 대상
	const hasParams = (k: string) => (IND_DEFS[k]?.params.length ?? 0) > 0;
	$effect(() => {
		if (menu !== 'ind') editing = null;
	});
</script>

<svelte:window onclick={() => (menu !== 'none' ? (menu = 'none') : null)} />

<!-- 차트 컨트롤 바 — 그래프 위 전용 행(absolute 오버레이 폐기, 밀도 배치). 좌=기간·봉주기, 우=지표·표시·BT 도구. -->
<div class="chartTopBar">
{#if indexCtl}
	<!-- 주체 토글 + 지수 picker — CenterStack indexCtl (한 줄 통합). 지수 시 검색 결과 칩 / 비면 큐레이트 9 그룹 칩. -->
	<span class="segGroup idxToggle">
		<button class={indexCtl.subject === 'price' ? 'seg on' : 'seg'} onclick={() => indexCtl.setSubject('price')}>{T('주가', 'Price')}</button>
		<button class={indexCtl.subject === 'index' ? 'seg on' : 'seg'} onclick={() => indexCtl.setSubject('index')}>{T('지수', 'Index')}</button>
	</span>
	{#if indexCtl.subject === 'index'}
		<input class="idxSearch mono" placeholder={T('지수 검색…', 'search…')} value={indexCtl.query} oninput={(e) => indexCtl.search(e.currentTarget.value)} />
		{#if indexCtl.results.length}
			<span class="idxChips">{#each indexCtl.results as r (r.code)}<button class={indexCtl.indexRef?.code === r.code ? 'idxItem on' : 'idxItem'} onclick={() => indexCtl.pick(r)}>{r.name}<span class="idxMkt">{r.market}</span></button>{/each}</span>
		{:else}
			<span class="idxChips"><span class="idxGrpLbl">{T('한국', 'KR')}</span>{#each KR_INDEX_PRESETS as r (r.code)}<button class={indexCtl.indexRef?.code === r.code ? 'idxItem on' : 'idxItem'} onclick={() => indexCtl.pick(r)}>{r.name}</button>{/each}<span class="idxGrpLbl">{T('미국', 'US')}</span>{#each US_INDEX_PRESETS as r (r.code)}<button class={indexCtl.indexRef?.code === r.code ? 'idxItem on' : 'idxItem'} onclick={() => indexCtl.pick(r)}>{r.name}</button>{/each}</span>
		{/if}
		<span class="cbDiv"></span>
	{/if}
{/if}
<!-- 기간 + 봉 주기 (좌) — segGroup 자체 위젯 (리본과 동일 패턴) -->
<div class="chartBar">
	<span class="segGroup" role="radiogroup">{#each PERIODS as p (p)}<button class={ctl.period === p ? 'seg on' : 'seg'} onclick={() => (ctl.period = p)}>{p}</button>{/each}</span>
	<span class="cbDiv"></span>
	<span class="segGroup" role="radiogroup">{#each TFS as t (t.v)}<button class={ctl.tf === t.v ? 'seg on' : 'seg'} title={T('봉 주기', 'timeframe')} onclick={() => (ctl.tf = t.v)}>{T(t.kr, t.en)}</button>{/each}</span>
</div>

<!-- 우상 도구 -->
<div class="chartTools" onclick={(e) => e.stopPropagation()}>
	<div class="ctWrap">
		<button class={ctl.overlays.length || ctl.subs.length ? 'chartTool on' : 'chartTool'} onclick={() => (menu = menu === 'ind' ? 'none' : 'ind')} title={T('보조지표 — 주가 오버레이 + 하단 페인', 'Indicators')}>{T('보조지표', 'IND')}</button>
		{#if menu === 'ind'}
			<div class="ctMenu ctMenuWide">
				<div class="ctMenuLbl">{T('주가 오버레이 (다중)', 'Price overlay (multi)')}</div>
				<div class="ctRow ctRowWrap">
					{#each OVERLAY_ALL as o (o)}
						{@const on = ctl.overlays.includes(o)}
						<button class={on ? 'mItem on' : 'mItem'} title={OVERLAY_HINT[o] ?? ''} onclick={() => ctl.toggleOverlay(o)}>{o}</button>
						{#if on && hasParams(o)}<button class="mItem mGear" title={T('파라미터', 'params')} onclick={() => (editing = editing === o ? null : o)}>⚙</button>{/if}
					{/each}
				</div>
				<div class="ctMenuLbl">{T('보조 지표 (다중)', 'Sub indicators (multi)')}</div>
				<div class="ctRow ctRowWrap">
					{#each SUB_ALL as k (k)}
						{@const on = ctl.subs.includes(k)}
						<button class={on ? 'mItem on' : 'mItem'} title={SUB_HINT[k] ?? ''} onclick={() => ctl.toggleSub(k)}>{k}</button>
						{#if on && hasParams(k)}<button class="mItem mGear" title={T('파라미터', 'params')} onclick={() => (editing = editing === k ? null : k)}>⚙</button>{/if}
					{/each}
				</div>
				{#if editing}
					<IndParamEditor {ctl} {lang} name={editing} />
				{/if}
				{#if ctl.overlays.length || ctl.subs.length || ctl.econ.length}
					<div class="ctRow"><button class="mItem mClear" onclick={() => ctl.clearAllIndicators()}>{T('지표 전체 해제', 'Clear all')}</button></div>
				{/if}
			</div>
		{/if}
	</div>
	<div class="ctWrap">
		<button class={ctl.econ.length ? 'chartTool on' : 'chartTool'} onclick={() => (menu = menu === 'econ' ? 'none' : 'econ')} title={T('경제지표 겹쳐보기', 'Economy overlay')}>{T('경제지표', 'ECON')}</button>
		{#if menu === 'econ'}
			<div class="ctMenu">
				<div class="ctMenuLbl">{T('경제지표 겹쳐보기 (최대 3 · 자기정규화)', 'Economy overlay (max 3 · self-scaled)')}</div>
				<div class="ctRow ctRowWrap">
					{#each MACRO_SERIES as s (s.id)}
						<button class={ctl.econ.includes(s.id) ? 'mItem on' : 'mItem'}
							style={ctl.econ.includes(s.id) ? `background:transparent;color:${ECON_COLORS[s.id]};border-color:${ECON_COLORS[s.id]};font-weight:600` : ''}
							onclick={() => ctl.toggleEcon(s.id)}>{T(s.kr, s.en)}</button>
					{/each}
				</div>
			</div>
		{/if}
	</div>
	<div class="ctWrap">
		<button class={ctl.drawCount ? 'chartTool on' : 'chartTool'} onclick={() => (menu = menu === 'draw' ? 'none' : 'draw')} title={T('그리기', 'Draw')}>{T('그리기', 'DRAW')}</button>
		{#if menu === 'draw'}
			<div class="ctMenu">
				<div class="ctRow ctRowWrap">{#each DRAW_TOOLS as d (d.name)}<button class="mItem" onclick={() => { menu = 'none'; onDraw(d.name); }}>{T(d.kr, d.en)}</button>{/each}</div>
				<div class="ctRow"><button class={ctl.magnet ? 'mItem on' : 'mItem'} onclick={() => (ctl.magnet = !ctl.magnet)} title={T('가까운 봉에 스냅', 'snap to bar')}>{T('자석', 'Magnet')}</button><button class="mItem mClear" onclick={() => { menu = 'none'; onClearDraw(); }}>{T('전체 지우기', 'Clear')}</button></div>
			</div>
		{/if}
	</div>
	<div class="ctWrap">
		<button class={ctl.candleStyle !== 'candle_solid' || ctl.yMode !== 'normal' || ctl.showEvents || ctl.showBand || ctl.showRefs || ctl.showVP || !ctl.adj ? 'chartTool on' : 'chartTool'} onclick={() => (menu = menu === 'view' ? 'none' : 'view')} title={T('표시 설정', 'View')}>{T('표시', 'VIEW')}</button>
		{#if menu === 'view'}
			<div class="ctMenu">
				<div class="ctMenuLbl">{T('캔들', 'Candle')}</div>
				<div class="ctRow">{#each CANDLES as cs (cs.v)}<button class={styleShown === cs.v ? 'mItem on' : 'mItem'} disabled={indexLine} title={indexLine ? T('종가 전용 — 라인 고정', 'close-only — line') : ''} onclick={() => !indexLine && (ctl.candleStyle = cs.v)}>{T(cs.kr, cs.en)}</button>{/each}</div>
				<div class="ctMenuLbl">{T('Y축', 'Y axis')}</div>
				<div class="ctRow">{#each YMODES as y (y.v)}<button class={ctl.yMode === y.v ? 'mItem on' : 'mItem'} onclick={() => (ctl.yMode = y.v)}>{T(y.kr, y.en)}</button>{/each}</div>
				<div class="ctMenuLbl">{T('가격', 'Price')}</div>
				<div class="ctRow"><button class={ctl.adj ? 'mItem on' : 'mItem'} onclick={() => (ctl.adj = !ctl.adj)}>{T('수정주가', 'Adjusted')}</button><button class={ctl.showRefs ? 'mItem on' : 'mItem'} onclick={() => (ctl.showRefs = !ctl.showRefs)}>{T('52주·전일 기준선', '52w/prev refs')}</button><button class={ctl.showVP && subject !== 'index' ? 'mItem on' : 'mItem'} disabled={subject === 'index'} title={subject === 'index' ? T('지수는 매물대 없음', 'no volume profile for indices') : ''} onclick={() => subject !== 'index' && (ctl.showVP = !ctl.showVP)}>{T('매물대', 'Vol Profile')}</button></div>
				<div class="ctMenuLbl">{T('마커', 'Markers')}</div>
				<div class="ctRow"><button class={ctl.showEvents ? 'mItem on' : 'mItem'} onclick={() => (ctl.showEvents = !ctl.showEvents)}>{T('실적 발표', 'Earnings')}</button><button class={ctl.showBand ? 'mItem on' : 'mItem'} disabled={!hasBand} onclick={() => hasBand && (ctl.showBand = !ctl.showBand)}>{T('적정주가 밴드', 'Fair band')}</button></div>
			</div>
		{/if}
	</div>
	<div class="ctWrap">
		<button class={!ctl.railAllOn ? 'chartTool on' : 'chartTool'} onclick={() => (menu = menu === 'rail' ? 'none' : 'rail')} title={T('이벤트 레일 — 차트 하단 공시 종류 필터', 'Event rail — filter disclosures shown under the chart')}>{T('이벤트레일', 'RAIL')}</button>
		{#if menu === 'rail'}
			<div class="ctMenu">
				<div class="ctMenuLbl">{T('이벤트 레일 — 표시할 공시 종류', 'Event rail — types to show')}</div>
				<div class="ctRow ctRowWrap">
					<button class={ctl.railAllOn ? 'mItem on' : 'mItem'} onclick={() => ctl.showAllRailCats()}>{T('전체', 'All')}</button>
					{#each EVENT_CATS as c (c.key)}
						{#if (railCatCounts[c.key] ?? 0) > 0}
							<button class={ctl.railCatOn(c.key) ? 'mItem on' : 'mItem'} onclick={() => ctl.toggleRailCat(c.key)}>{T(c.kr, c.en)} <span class="dim">{railCatCounts[c.key]}</span></button>
						{/if}
					{/each}
				</div>
				<div class="ctMenuLbl">{T('· DART 공시그룹 근사 분류. 뉴스·다른 이벤트는 추후 추가', '· approx DART groups · news & more later')}</div>
			</div>
		{/if}
	</div>
	<div class="ctWrap">
		<button class={ctl.btKey && subject !== 'index' ? 'chartTool on' : 'chartTool'} disabled={subject === 'index'} onclick={() => { if (subject === 'index') return; if (ctl.tf !== 'D') { if (ctl.period === 'MAX') ctl.period = '3Y'; ctl.tf = 'D'; } menu = menu === 'bt' ? 'none' : 'bt'; }} title={subject === 'index' ? T('지수는 거래 대상 아님', 'index not tradable') : ctl.tf !== 'D' ? T('일봉 기준 — 클릭 시 일봉 전환', 'daily-based — switches to D') : T('전략 백테스트', 'Backtest')}>{T('백테스트', 'BT')}</button>
		{#if menu === 'bt'}
			<div class="ctMenu"><BtConfig {ctl} {lang} /></div>
		{/if}
	</div>
	<button class="chartTool" onclick={() => onSnapshot?.()} title={T('차트 PNG 저장 (출처 띠 포함)', 'save PNG')} aria-label="snapshot">
		<svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round" aria-hidden="true"><path d="M2 5h2.4L6 3.2h4L11.6 5H14v8H2z"/><circle cx="8" cy="8.6" r="2.5"/></svg>
	</button>
	<button class="chartTool" onclick={() => (ctl.full = true)} title={T('전체화면 (Shift+F)', 'Fullscreen (Shift+F)')} aria-label="fullscreen">⤢</button>
</div>
</div>
