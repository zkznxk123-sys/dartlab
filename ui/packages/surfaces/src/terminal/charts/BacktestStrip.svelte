<script lang="ts">
	// 백테스트 결과 스트립 — 차트 하단 도킹 (전체화면 동행). 헤드라인 = 전략 vs 보유 비교,
	// 전략 열위 시 전체 dim (초록 축포 금지). 상시 고지 푸터 + 출처 — 닫기 불가.
	import type { BtResult, BtWarning } from '../lib/backtest';
	import { GOV_ATTRIBUTION } from '@dartlab/ui-contracts';
	import type { Lang } from '../lib/types';
	import BacktestReport from './BacktestReport.svelte';

	interface Props {
		result: BtResult;
		presetLabel: string;
		period: string;
		withCosts: boolean;
		adjusted: boolean; // 수정주가 입력 여부 — 각주 정확성
		lang: Lang;
		onClear: () => void;
		onFocusBar?: (t: string) => void; // 리포트 거래/낙폭 행 클릭 → 차트 해당 봉 (PriceChart 가 scrollToTimestamp)
	}
	let { result, presetLabel, period, withCosts, adjusted, lang, onClear, onFocusBar }: Props = $props();

	let showReport = $state(false); // 리포트 도크 4탭 펼침 (요약 strip 위로 확장 드로어)
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	const m = $derived(result.metrics);
	const sgn = (v: number, d = 1) => (v >= 0 ? '+' : '') + v.toFixed(d);
	const cls = (v: number) => (v > 0 ? 'tUp' : v < 0 ? 'tDn' : 'tNeu');
	const beats = $derived(m.retPct >= result.bh.retPct);
	const oos = $derived(result.oos);
	const fmtDate = (t: string) => `${t.slice(2, 4)}.${t.slice(4, 6)}.${t.slice(6, 8)}`;
	const WARN_LABEL: Record<BtWarning['kind'], { kr: string; en: string }> = {
		fewTrades: { kr: '표본 부족', en: 'few trades' },
		shortRange: { kr: '기간 부족 — 참고용', en: 'short range' },
		splitSuspect: { kr: '분할 의심 — 구간 무효', en: 'split suspect' },
		costsOff: { kr: '비용 미포함', en: 'costs off' }
	};
</script>

<div class="btStrip" class:btLag={!beats} class:btOpen={showReport}>
	{#if showReport}
		<BacktestReport {result} {adjusted} {withCosts} {lang} {onFocusBar} />
	{/if}
	<div class="btHead">
		<span class="btPreset">{presetLabel} · {period}</span>
		<b class={'btRet mono ' + cls(m.retPct)}>{T('전략', 'BT')} {sgn(m.retPct)}%</b>
		<span class="btVs">vs</span>
		<b class={'btRet mono ' + cls(result.bh.retPct)}>{T('보유', 'B&H')} {sgn(result.bh.retPct)}%</b>
		<span class="btSpacer"></span>
		{#each result.warnings as w (w.kind)}
			<span class="btWarn" title={w.date ?? ''}>{T(WARN_LABEL[w.kind].kr, WARN_LABEL[w.kind].en)}{w.date ? ' ' + fmtDate(w.date) : ''}</span>
		{/each}
		<button class="btClose" onclick={onClear} title={T('백테스트 해제', 'clear backtest')}>✕</button>
	</div>
	<div class="btKpis mono">
		<span>CAGR <b class={m.cagrPct != null ? cls(m.cagrPct) : 'tNeu'}>{m.cagrPct != null ? sgn(m.cagrPct) + '%' : '—'}</b></span>
		<span title={T('일수익률 연환산 · 무위험 0 가정', 'annualized daily · rf=0')}>Sharpe <b class={m.sharpe != null ? cls(m.sharpe) : 'tNeu'}>{m.sharpe != null ? m.sharpe.toFixed(2) : '—'}</b>{#if result.bh.sharpe != null}<i class="btSub">({T('보유', 'B&H')} {result.bh.sharpe.toFixed(2)})</i>{/if}</span>
		<span title={T('하방 변동성 기준', 'downside deviation')}>Sortino <b class={m.sortino != null ? cls(m.sortino) : 'tNeu'}>{m.sortino != null ? m.sortino.toFixed(2) : '—'}</b></span>
		<span>MDD <b class="tDn">{m.mddPct.toFixed(1)}%</b><i class="btSub">({T('보유', 'B&H')} {result.bh.mddPct.toFixed(1)}%{m.mddDays != null ? ` · ${T('수면', 'uw')} ${m.mddDays}${T('일', 'd')}` : ''})</i></span>
		<span>{T('승률', 'win')} <b>{m.winRatePct != null ? m.winRatePct.toFixed(0) + '%' : '—'}</b><i class="btSub">({result.trades.filter((t) => t.retPct > 0).length}/{m.tradeCount})</i></span>
		<span>{T('손익비', 'PF')} <b>{m.profitFactor != null ? m.profitFactor.toFixed(1) : '—'}</b></span>
		<span title={T('거래당 평균 (최고/최악)', 'avg per trade (best/worst)')}>{T('평균거래', 'avg')} <b class={m.avgTradePct != null ? cls(m.avgTradePct) : 'tNeu'}>{m.avgTradePct != null ? sgn(m.avgTradePct) + '%' : '—'}</b>{#if m.bestTradePct != null && m.worstTradePct != null}<i class="btSub">({sgn(m.bestTradePct, 0)}/{sgn(m.worstTradePct, 0)})</i>{/if}</span>
		<span>{T('노출', 'expo')} <b>{m.exposurePct.toFixed(0)}%</b></span>
		<span>{T('비용', 'cost')} <b class="tDn">{m.costDragPct.toFixed(1)}%p</b></span>
		<button class="btTradesBtn" onclick={() => (showReport = !showReport)} title={T('상세 리포트 — 개요·거래·낙폭·가정', 'detailed report')}>{T('리포트', 'report')} {showReport ? '▾' : '▸'}</button>
	</div>
	{#if oos}
		<!-- OOS 학습/검증 2열 — 고정 파라미터를 안 본 구간에 적용(walk-forward 아님). 검증<학습 = 과최적화 신호. -->
		<div class="btOos mono">
			<span class="btOosLbl" title={fmtDate(result.startIdx >= 0 && result.runSpec ? result.runSpec.range.from : '') + ' ~ ' + fmtDate(oos.splitT)}>{T('학습', 'train')}</span>
			<b class={cls(oos.train.retPct)}>{sgn(oos.train.retPct)}%</b>
			<i class="btSub">Sh {oos.train.sharpe != null ? oos.train.sharpe.toFixed(2) : '—'} · MDD {oos.train.mddPct.toFixed(0)}% · {oos.train.tradeCount}{T('거래', 'tr')}</i>
			<span class="btOosArrow">→</span>
			<span class="btOosLbl test" title={fmtDate(oos.splitT) + ' ~ ' + (result.runSpec ? fmtDate(result.runSpec.range.to) : '')}>{T('검증(OOS)', 'test(OOS)')}</span>
			<b class={cls(oos.test.retPct)}>{sgn(oos.test.retPct)}%</b>
			<i class="btSub">Sh {oos.test.sharpe != null ? oos.test.sharpe.toFixed(2) : '—'} · MDD {oos.test.mddPct.toFixed(0)}% · {oos.test.tradeCount}{T('거래', 'tr')}</i>
			{#if oos.test.retPct < oos.train.retPct}<span class="btWarn">{T('검증 열위 — 과최적화 주의', 'test underperforms — overfit risk')}</span>{/if}
		</div>
	{/if}
	<div class="btFoot">
		⚠ {T('과거 시뮬레이션 — 미래 수익 보장 없음 · 익일 시가 체결', 'historical simulation — no guarantee · next-open fills')}
		· {withCosts ? T('수수료 0.015%+거래세 0.15%+슬리피지 0.1%', 'fees 0.015%+tax 0.15%+slip 0.1%') : T('비용 미포함', 'costs excluded')}
		· {adjusted ? T('배당 미반영 · 수정주가 반영', 'dividends excluded · split-adjusted') : T('배당 미반영 · 무수정주가', 'dividends excluded · unadjusted')}{#if result.runSpec} · {T('기준일', 'as of')} {fmtDate(result.runSpec.dataAsOf)} ({fmtDate(result.runSpec.range.from)}~{fmtDate(result.runSpec.range.to)} · {result.runSpec.range.bars}{T('봉', 'bars')}){/if} │ {GOV_ATTRIBUTION}
	</div>
</div>
