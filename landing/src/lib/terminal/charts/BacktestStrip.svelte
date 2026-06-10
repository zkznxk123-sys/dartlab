<script lang="ts">
	// 백테스트 결과 스트립 — 차트 하단 도킹 (전체화면 동행). 헤드라인 = 전략 vs 보유 비교,
	// 전략 열위 시 전체 dim (초록 축포 금지). 상시 고지 푸터 + 출처 — 닫기 불가.
	import type { BtResult, BtWarning } from '../data/backtest';
	import { GOV_ATTRIBUTION } from '../data/govPrice';
	import type { Lang } from '../data/types';

	interface Props {
		result: BtResult;
		presetLabel: string;
		period: string;
		withCosts: boolean;
		adjusted: boolean; // 수정주가 입력 여부 — 각주 정확성
		lang: Lang;
		onClear: () => void;
	}
	let { result, presetLabel, period, withCosts, adjusted, lang, onClear }: Props = $props();

	let showTrades = $state(false);
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	const m = $derived(result.metrics);
	const sgn = (v: number, d = 1) => (v >= 0 ? '+' : '') + v.toFixed(d);
	const cls = (v: number) => (v > 0 ? 'tUp' : v < 0 ? 'tDn' : 'tNeu');
	const beats = $derived(m.retPct >= result.bh.retPct);
	const fmtDate = (t: string) => `${t.slice(2, 4)}.${t.slice(4, 6)}.${t.slice(6, 8)}`;
	// 누적 P&L — 시간순 (1+r) 누적곱 −1 (%). 표시는 역순 테이블이라 원본 인덱스로 매핑.
	const cumPct = $derived.by(() => {
		let acc = 1;
		return result.trades.map((t) => {
			acc *= 1 + t.retPct / 100;
			return (acc - 1) * 100;
		});
	});
	const WARN_LABEL: Record<BtWarning['kind'], { kr: string; en: string }> = {
		fewTrades: { kr: '표본 부족', en: 'few trades' },
		shortRange: { kr: '기간 부족 — 참고용', en: 'short range' },
		splitSuspect: { kr: '분할 의심 — 구간 무효', en: 'split suspect' },
		costsOff: { kr: '비용 미포함', en: 'costs off' }
	};
</script>

<div class="btStrip" class:btLag={!beats}>
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
		<button class="btTradesBtn" onclick={() => (showTrades = !showTrades)}>{T('거래', 'trades')} {m.tradeCount} {showTrades ? '▾' : '▸'}</button>
	</div>
	{#if showTrades && result.trades.length}
		<div class="btTrades">
			<table class="btTable mono">
				<thead><tr><th>{T('진입', 'entry')}</th><th class="r">{T('진입가', 'px')}</th><th>{T('청산', 'exit')}</th><th class="r">{T('청산가', 'px')}</th><th class="r">{T('수익률', 'ret')}</th><th class="r" title={T('해당 거래까지 (1+r) 누적곱 −1', 'cumulative (1+r) product −1')}>{T('누적%', 'cum%')}</th><th class="r">{T('보유일', 'days')}</th></tr></thead>
				<tbody>
					{#each result.trades.slice().reverse() as t, i (t.entryT)}
						{@const cum = cumPct[result.trades.length - 1 - i]}
						<tr>
							<td>{fmtDate(t.entryT)}</td>
							<td class="r">{t.entryPx.toLocaleString('en-US', { maximumFractionDigits: 0 })}</td>
							<td>{t.exitT ? fmtDate(t.exitT) : T('보유중', 'open')}</td>
							<td class="r">{t.exitPx != null ? t.exitPx.toLocaleString('en-US', { maximumFractionDigits: 0 }) : '—'}</td>
							<td class={'r ' + cls(t.retPct)}>{sgn(t.retPct)}%</td>
							<td class={'r ' + cls(cum)}>{sgn(cum)}%</td>
							<td class="r">{t.holdDays}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
	<div class="btFoot">
		⚠ {T('과거 시뮬레이션 — 미래 수익 보장 없음 · 익일 시가 체결', 'historical simulation — no guarantee · next-open fills')}
		· {withCosts ? T('수수료 0.015%+거래세 0.15%+슬리피지 0.1%', 'fees 0.015%+tax 0.15%+slip 0.1%') : T('비용 미포함', 'costs excluded')}
		· {adjusted ? T('배당 미반영 · 수정주가 반영', 'dividends excluded · split-adjusted') : T('배당 미반영 · 무수정주가', 'dividends excluded · unadjusted')} │ {GOV_ATTRIBUTION}
	</div>
</div>
