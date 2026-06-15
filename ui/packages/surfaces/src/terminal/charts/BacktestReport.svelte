<script lang="ts">
	// 백테스트 리포트 도크 — 차트 하단 확장 스크롤 드로어 4탭(Overview/Trades/Drawdown/Assumptions, 03 §0.5.6 P3·§0.5.9-E).
	// strip(요약) 위로 펼쳐지는 오버레이 — 전체화면 레이아웃 수술 없이 일반/전체화면 양쪽 동작(차트 resize 회귀 0).
	// 거래/낙폭 행 클릭 → onFocusBar(날짜) → PriceChart 가 chart.scrollToTimestamp. 카드더미 금지·full-width band·정직 라벨.
	import type { BtResult } from '../lib/backtest';
	import { GOV_ATTRIBUTION } from '@dartlab/ui-contracts';
	import type { Lang } from '../lib/types';

	interface Props {
		result: BtResult;
		adjusted: boolean;
		withCosts: boolean;
		lang: Lang;
		onFocusBar?: (t: string) => void; // 거래 행 클릭 → 차트 해당 봉 센터링
	}
	let { result, adjusted, withCosts, lang, onFocusBar }: Props = $props();
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	let tab = $state<'overview' | 'trades' | 'drawdown' | 'assumptions'>('overview');
	const m = $derived(result.metrics);
	const rs = $derived(result.runSpec);
	const sgn = (v: number, d = 1) => (v >= 0 ? '+' : '') + v.toFixed(d);
	const cls = (v: number) => (v > 0 ? 'tUp' : v < 0 ? 'tDn' : 'tNeu');
	const fmtD = (t: string) => (t && t.length >= 8 ? `${t.slice(0, 4)}.${t.slice(4, 6)}.${t.slice(6, 8)}` : '—');
	const num = (v: number, d = 0) => v.toLocaleString('en-US', { maximumFractionDigits: d });
	// 누적 P&L (시간순)
	const cumPct = $derived.by(() => {
		let acc = 1;
		return result.trades.map((t) => { acc *= 1 + t.retPct / 100; return (acc - 1) * 100; });
	});
	// 낙폭 탭 — 최악 거래 상위 (낙폭 분해 대용, mddWindow 단일 + 거래 분포)
	const worstTrades = $derived([...result.trades].sort((a, b) => a.retPct - b.retPct).slice(0, 6));
	const recovered = $derived(result.mddWindow?.recoverIdx != null);

	// Trades CSV — 브라우저 zero-dep Blob 다운로드 (egress 는 table-export PRD 영역이라 여기선 최소 거래내역만).
	function exportCsv() {
		const head = ['entry', 'entryPx', 'exit', 'exitPx', 'retPct', 'cumPct', 'holdDays', 'exitReason'];
		const rows = result.trades.map((t, i) => [t.entryT, t.entryPx.toFixed(2), t.exitT ?? '', t.exitPx != null ? t.exitPx.toFixed(2) : '', t.retPct.toFixed(2), cumPct[i].toFixed(2), t.holdDays, t.exitReason]);
		const csv = [head, ...rows].map((r) => r.join(',')).join('\n');
		const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `backtest_${rs?.symbol.code ?? 'trades'}_${rs?.dataAsOf ?? ''}.csv`;
		a.click();
		URL.revokeObjectURL(url);
	}
	const TABS: { k: typeof tab; kr: string; en: string }[] = [
		{ k: 'overview', kr: '개요', en: 'Overview' },
		{ k: 'trades', kr: '거래', en: 'Trades' },
		{ k: 'drawdown', kr: '낙폭', en: 'Drawdown' },
		{ k: 'assumptions', kr: '가정', en: 'Assumptions' }
	];
</script>

<div class="btReport mono">
	<div class="btTabs">
		{#each TABS as t (t.k)}
			<button class={tab === t.k ? 'btTab on' : 'btTab'} onclick={() => (tab = t.k)}>{T(t.kr, t.en)}{#if t.k === 'trades'}<span class="btTabN"> {m.tradeCount}</span>{/if}</button>
		{/each}
	</div>

	{#if tab === 'overview'}
		<div class="btPane">
			<!-- 정직 배너 — 단일 구간 in-sample. 다구간 교차검증(walk-forward·DSR)은 로컬 정밀 모드(§0.5.9-E·§0.6.1) -->
			<div class="btBanner">{T('단일 구간 결과입니다. 다구간 교차검증(walk-forward·DSR·PBO)은 로컬 정밀 모드에서 제공됩니다 — 표본 한계로 단일종목 통계는 floor 미노출.', 'Single-window result. Multi-window cross-validation (walk-forward · DSR · PBO) is available in local precision mode.')}</div>
			<div class="btGrid">
				<div class="btCell"><span>{T('전략 수익률', 'strategy ret')}</span><b class={cls(m.retPct)}>{sgn(m.retPct)}%</b></div>
				<div class="btCell"><span>{T('보유(B&H)', 'buy & hold')}</span><b class={cls(result.bh.retPct)}>{sgn(result.bh.retPct)}%</b></div>
				<div class="btCell"><span>{T('초과', 'excess')}</span><b class={cls(m.retPct - result.bh.retPct)}>{sgn(m.retPct - result.bh.retPct)}%p</b></div>
				<div class="btCell"><span>CAGR</span><b class={m.cagrPct != null ? cls(m.cagrPct) : 'tNeu'}>{m.cagrPct != null ? sgn(m.cagrPct) + '%' : '—'}</b></div>
				<div class="btCell"><span>Sharpe</span><b>{m.sharpe != null ? m.sharpe.toFixed(2) : '—'}</b></div>
				<div class="btCell"><span>Sortino</span><b>{m.sortino != null ? m.sortino.toFixed(2) : '—'}</b></div>
				<div class="btCell"><span>MDD</span><b class="tDn">{m.mddPct.toFixed(1)}%</b></div>
				<div class="btCell"><span>{T('승률', 'win rate')}</span><b>{m.winRatePct != null ? m.winRatePct.toFixed(0) + '%' : '—'}</b></div>
				<div class="btCell"><span>{T('손익비', 'profit factor')}</span><b>{m.profitFactor != null ? m.profitFactor.toFixed(2) : '—'}</b></div>
				<div class="btCell"><span>{T('평균 거래', 'avg trade')}</span><b class={m.avgTradePct != null ? cls(m.avgTradePct) : 'tNeu'}>{m.avgTradePct != null ? sgn(m.avgTradePct) + '%' : '—'}</b></div>
				<div class="btCell"><span>{T('노출', 'exposure')}</span><b>{m.exposurePct.toFixed(0)}%</b></div>
				<div class="btCell"><span>{T('비용 드래그', 'cost drag')}</span><b class="tDn">{m.costDragPct.toFixed(1)}%p</b></div>
			</div>
			{#if result.oos}
				<div class="btSubHead">{T('학습 / 검증 (OOS) — 고정 파라미터, walk-forward 아님', 'train / test (OOS) — fixed params, not walk-forward')}</div>
				<div class="btGrid">
					<div class="btCell"><span>{T('학습 수익률', 'train ret')}</span><b class={cls(result.oos.train.retPct)}>{sgn(result.oos.train.retPct)}%</b></div>
					<div class="btCell"><span>{T('학습 Sharpe', 'train Sh')}</span><b>{result.oos.train.sharpe != null ? result.oos.train.sharpe.toFixed(2) : '—'}</b></div>
					<div class="btCell test"><span>{T('검증 수익률', 'test ret')}</span><b class={cls(result.oos.test.retPct)}>{sgn(result.oos.test.retPct)}%</b></div>
					<div class="btCell test"><span>{T('검증 Sharpe', 'test Sh')}</span><b>{result.oos.test.sharpe != null ? result.oos.test.sharpe.toFixed(2) : '—'}</b></div>
				</div>
			{/if}
		</div>
	{:else if tab === 'trades'}
		<div class="btPane">
			<div class="btPaneBar"><span class="btHint">{T('행 클릭 → 차트 해당 진입봉으로 이동', 'click row → jump to entry bar')}</span><button class="mItem" onclick={exportCsv}>{T('CSV 내보내기', 'export CSV')}</button></div>
			<table class="btTable">
				<thead><tr><th>{T('진입', 'entry')}</th><th class="r">{T('진입가', 'in')}</th><th>{T('청산', 'exit')}</th><th class="r">{T('청산가', 'out')}</th><th class="r">{T('수익률', 'ret')}</th><th class="r">{T('누적', 'cum')}</th><th class="r">{T('보유일', 'days')}</th><th>{T('사유', 'reason')}</th></tr></thead>
				<tbody>
					{#each result.trades.slice().reverse() as t, i (t.entryT)}
						{@const cum = cumPct[result.trades.length - 1 - i]}
						<tr class="btRow" onclick={() => onFocusBar?.(t.entryT)} title={T('차트로 이동', 'jump to chart')}>
							<td>{fmtD(t.entryT)}</td>
							<td class="r">{num(t.entryPx)}</td>
							<td>{t.exitT ? fmtD(t.exitT) : T('보유중', 'open')}</td>
							<td class="r">{t.exitPx != null ? num(t.exitPx) : '—'}</td>
							<td class={'r ' + cls(t.retPct)}>{sgn(t.retPct)}%</td>
							<td class={'r ' + cls(cum)}>{sgn(cum)}%</td>
							<td class="r">{t.holdDays}</td>
							<td class="dim">{t.exitReason === 'finalMark' ? T('미청산', 'open') : T('신호', 'signal')}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{:else if tab === 'drawdown'}
		<div class="btPane">
			<div class="btGrid">
				<div class="btCell"><span>{T('최대 낙폭', 'max drawdown')}</span><b class="tDn">{m.mddPct.toFixed(1)}%</b></div>
				<div class="btCell"><span>{T('최장 수면', 'longest underwater')}</span><b>{m.mddDays != null ? m.mddDays + T('거래일', 'd') : '—'}</b></div>
				<div class="btCell"><span>{T('회복', 'recovered')}</span><b class={recovered ? 'tUp' : 'tDn'}>{recovered ? T('회복함', 'yes') : T('미회복', 'no')}</b></div>
				<div class="btCell"><span>{T('보유(B&H) MDD', 'B&H MDD')}</span><b class="tDn">{result.bh.mddPct.toFixed(1)}%</b></div>
			</div>
			<div class="btSubHead">{T('최악 거래 (낙폭 기여 상위)', 'worst trades')}</div>
			<table class="btTable">
				<thead><tr><th>{T('진입', 'entry')}</th><th>{T('청산', 'exit')}</th><th class="r">{T('수익률', 'ret')}</th><th class="r">{T('보유일', 'days')}</th></tr></thead>
				<tbody>
					{#each worstTrades as t (t.entryT)}
						<tr class="btRow" onclick={() => onFocusBar?.(t.entryT)}>
							<td>{fmtD(t.entryT)}</td><td>{t.exitT ? fmtD(t.exitT) : T('보유중', 'open')}</td>
							<td class={'r ' + cls(t.retPct)}>{sgn(t.retPct)}%</td><td class="r">{t.holdDays}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{:else}
		<div class="btPane btAssume">
			<div class="btSubHead">{T('체결·데이터 가정', 'execution & data assumptions')}</div>
			<ul>
				<li>{T('신호 t일 종가 확정 → t+1일 시가 체결 (미래참조 구조적 차단)', 'signal close(t) → fill open(t+1) · look-ahead structurally blocked')}</li>
				<li>{T('거래정지(거래량 0) 봉 = 체결 자동 이연', 'halted bars (zero volume) defer fills')}{result.deferredBars > 0 ? ` · ${result.deferredBars}${T('봉 이연', ' bars deferred')}` : ''}</li>
				<li>{withCosts ? T('비용 반영 — 수수료 0.015% + 거래세 0.15% + 슬리피지 0.1% (편집 가능)', 'costs on — fee 0.015% + tax 0.15% + slippage 0.1%') : T('⚠ 비용 미포함 — 실거래 대비 낙관', '⚠ costs excluded — optimistic vs live')}</li>
				<li>{T('벤치마크 = 보유(B&H), 전략과 동일 비용 적용 (공정 비교)', 'benchmark = buy & hold, same costs')}</li>
				<li class="warn">{T('⚠ 배당 미반영', '⚠ dividends excluded')} · {adjusted ? T('수정주가 반영', 'split-adjusted') : T('⚠ 무수정주가 — 분할 시 B&H 왜곡', '⚠ unadjusted — splits distort B&H')} — {T('B&H를 체계적으로 깎아 전략이 상대적으로 좋아 보일 수 있음', 'depresses B&H; strategy may look relatively better')}</li>
			</ul>
			{#if rs}
				<div class="btSubHead">{T('실행 명세 (RunSpec)', 'run spec')}</div>
				<div class="btSpec">
					<span>{T('종목', 'symbol')}: {rs.symbol.name ?? ''} {rs.symbol.code}</span>
					<span>{T('전략', 'strategy')}: {rs.strategy.id} ({Object.entries(rs.strategy.params).map(([k, v]) => `${k}=${v}`).join(' ')})</span>
					<span>{T('구간', 'range')}: {fmtD(rs.range.from)} ~ {fmtD(rs.range.to)} · {rs.range.bars}{T('봉', ' bars')}</span>
					<span>{T('기준일', 'as of')}: {fmtD(rs.dataAsOf)} · {T('데이터', 'source')}: {rs.dataSource} · {T('엔진', 'engine')} {rs.engineVersion}</span>
				</div>
			{/if}
			<div class="btFootNote">⚠ {T('과거 가정 노출형 시뮬레이션 — 미래 수익 보장 없음 · 추천 아님', 'assumption-exposed historical simulation — no guarantee · not advice')} │ {GOV_ATTRIBUTION}</div>
		</div>
	{/if}
</div>
