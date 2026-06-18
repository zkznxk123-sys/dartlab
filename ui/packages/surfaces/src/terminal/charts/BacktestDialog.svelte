<script lang="ts">
	// 백테스트 전문 화면 — 차트 위 [백테스팅 상세] → 모달. 4탭(개요·성과·거래·속성)으로 위계 분리.
	// 개요: 히어로5 지표(큰 활자) + 보조지표 표 + 자산곡선(EquityChart, 실측px·축·크로스헤어) + OOS.
	// 성과: 월별 수익률 히트맵 + 낙폭 분석 + 최악 거래.  거래: 전체 내역 + CSV.  속성: 가정·RunSpec·정직 푸터(정본).
	// 거래/낙폭 행 클릭 → onFocusBar(날짜) + onClose → 메인차트 해당 봉 센터링. 정직 라벨·동일비용 B&H·추천 아님.
	import type { PortfolioBtResult, StrategySlot } from '../lib/backtest';
	import { GOV_ATTRIBUTION } from '@dartlab/ui-contracts';
	import type { Lang } from '../lib/types';
	import EquityChart from './EquityChart.svelte';
	import MonthlyReturnsHeatmap from './MonthlyReturnsHeatmap.svelte';
	import TradeScatter from './TradeScatter.svelte';
	import YearlyReturnsBars from './YearlyReturnsBars.svelte';
	import ReturnHistogram from './ReturnHistogram.svelte';

	interface Props {
		pf: PortfolioBtResult;
		slots: StrategySlot[]; // 전체 슬롯(메타) — pf.slots 는 워밍업 통과분만이라 id 매칭
		focus: number;
		period: string;
		withCosts: boolean;
		adjusted: boolean;
		candleTs: string[]; // displaySeries 캔들 t(YYYYMMDD) — equity 인덱스 정렬(startIdx 오프셋으로 슬라이스)
		lang: Lang;
		onFocus: (i: number) => void;
		onClose: () => void;
		onFocusBar?: (t: string) => void; // 거래/낙폭 행 클릭 → 차트 해당 봉
	}
	let { pf, slots, focus, period, withCosts, adjusted, candleTs, lang, onFocus, onClose, onFocusBar }: Props = $props();
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	type ViewTab = 'overview' | 'performance' | 'trades' | 'properties';
	let viewTab = $state<ViewTab>('overview');

	// 본문은 포커스 1전략 단수 유지 — result 를 포커스 슬롯 파생으로.
	const focusId = $derived(slots[focus]?.id ?? slots[0]?.id);
	const result = $derived(pf.slots.find((s) => s.id === focusId)?.result ?? pf.slots[0].result);
	const presetLabel = $derived(slots.find((s) => s.id === focusId)?.label ?? '');
	const stratColor = $derived(slots.find((s) => s.id === focusId)?.color ?? '#fb923c'); // 포커스 전략 색 — EquityChart 색 일치
	const combo = $derived(pf.combo);
	const multi = $derived(pf.slots.length >= 2);
	const metaOf = (id: string) => slots.find((s) => s.id === id);
	const idxOf = (id: string) => slots.findIndex((s) => s.id === id);
	const m = $derived(result.metrics);
	const rs = $derived(result.runSpec);
	const oos = $derived(result.oos);
	// OOS Sharpe 감쇠 — 검증/학습 비율(−면 열화, 과최적화의 정량 신호). train.sharpe>0 & 둘 다 산출 시만(분모 음/0 무의미).
	const oosDecay = $derived.by<number | null>(() => {
		if (!oos || oos.train.sharpe == null || oos.test.sharpe == null || oos.train.sharpe <= 0) return null;
		return (oos.test.sharpe / oos.train.sharpe - 1) * 100;
	});
	const sgn = (v: number, d = 1) => (v >= 0 ? '+' : '') + v.toFixed(d);
	const cls = (v: number) => (v > 0 ? 'tUp' : v < 0 ? 'tDn' : 'tNeu');
	const fmtD = (t: string) => (t && t.length >= 8 ? `${t.slice(0, 4)}.${t.slice(4, 6)}.${t.slice(6, 8)}` : '—');
	const num = (v: number, d = 0) => v.toLocaleString('en-US', { maximumFractionDigits: d });
	const beats = $derived(m.retPct >= result.bh.retPct);

	// ── 자산곡선 데이터(EquityChart props) — 평가창 내 non-null 슬라이스. ──
	const eq = $derived(result.equity.filter((v): v is number => v != null));
	const bhq = $derived(result.bhEquity.filter((v): v is number => v != null));
	const nBars = $derived(eq.length);
	// 캔들 t 를 equity 와 동일 슬라이스(startIdx 오프셋)로 — 월별 히트맵·x축 날짜 정렬.
	const tsWin = $derived(candleTs.slice(result.startIdx, result.startIdx + nBars));
	// 낙폭(언더워터) — 전략 누적 최고점 대비 하락률(≤0).
	const dd = $derived.by(() => {
		let peak = -Infinity;
		return eq.map((v) => {
			if (v > peak) peak = v;
			return peak > 0 ? (v / peak - 1) * 100 : 0;
		});
	});
	const splitFrac = $derived.by<number | null>(() => {
		if (!oos || nBars < 2) return null;
		const rel = oos.splitIdx - result.startIdx;
		if (rel <= 0 || rel >= nBars) return null;
		return rel / (nBars - 1);
	});
	const eqRange = $derived.by(() => {
		const all = [...eq, ...bhq];
		if (!all.length) return { lo: 90, hi: 110 };
		let lo = Math.min(...all);
		let hi = Math.max(...all);
		if (hi - lo < 1) {
			lo -= 1;
			hi += 1;
		}
		return { lo, hi };
	});
	const ddMin = $derived(dd.length ? Math.min(...dd, -1) : -1);

	// 누적 P&L (시간순) — 거래표 누적 칸.
	const cumPct = $derived.by(() => {
		let acc = 1;
		return result.trades.map((t) => {
			acc *= 1 + t.retPct / 100;
			return (acc - 1) * 100;
		});
	});
	const worstTrades = $derived([...result.trades].sort((a, b) => a.retPct - b.retPct).slice(0, 6));
	// 거래 분석 — 기대값(거래당 평균수익)·평균 MAE/MFE(역행/순행).
	const tradeStats = $derived.by(() => {
		const ts = result.trades.filter((t) => t.maePct != null);
		if (!result.trades.length) return null;
		const exp = result.trades.reduce((s, t) => s + t.retPct, 0) / result.trades.length;
		const mae = ts.length ? ts.reduce((s, t) => s + (t.maePct ?? 0), 0) / ts.length : null;
		const mfe = ts.length ? ts.reduce((s, t) => s + (t.mfePct ?? 0), 0) / ts.length : null;
		return { exp, mae, mfe };
	});
	const recovered = $derived(result.mddWindow?.recoverIdx != null);

	function jumpToBar(t: string) {
		onFocusBar?.(t);
		onClose();
	}

	// Trades CSV — 브라우저 zero-dep Blob.
	function exportCsv() {
		const head = ['entry', 'entryPx', 'exit', 'exitPx', 'retPct', 'maePct', 'mfePct', 'cumPct', 'holdDays', 'exitReason'];
		const rows = result.trades.map((t, i) => [t.entryT, t.entryPx.toFixed(2), t.exitT ?? '', t.exitPx != null ? t.exitPx.toFixed(2) : '', t.retPct.toFixed(2), t.maePct != null ? t.maePct.toFixed(2) : '', t.mfePct != null ? t.mfePct.toFixed(2) : '', cumPct[i].toFixed(2), t.holdDays, t.exitReason]);
		const csv = [head, ...rows].map((r) => r.join(',')).join('\n');
		const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `backtest_${rs?.symbol.code ?? 'trades'}_${rs?.dataAsOf ?? ''}.csv`;
		a.click();
		URL.revokeObjectURL(url);
	}

	$effect(() => {
		const onKey = (e: KeyboardEvent) => {
			if (e.key === 'Escape') onClose();
		};
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});

	const VIEW_TABS: { k: ViewTab; kr: string; en: string }[] = [
		{ k: 'overview', kr: '개요', en: 'Overview' },
		{ k: 'performance', kr: '성과', en: 'Performance' },
		{ k: 'trades', kr: '거래', en: 'Trades' },
		{ k: 'properties', kr: '속성', en: 'Properties' }
	];
</script>

<div class="scrimWrap" role="presentation" onclick={onClose}>
	<div class="scrModal bdModal" role="dialog" aria-modal="true" aria-label={T('전략 백테스팅', 'strategy backtest')} onclick={(e) => e.stopPropagation()}>
		<div class="scrHead">
			<span class="scrTitle">{T('전략 백테스팅', 'STRATEGY BACKTEST')}</span>
			<span class="bdStrat">{presetLabel}<i>{period} · {rs ? `${fmtD(rs.range.from)}~${fmtD(rs.range.to)} · ${rs.range.bars}${T('봉', ' bars')}` : ''}</i></span>
			<span class="bdHeadline mono">
				<b class={cls(m.retPct)}>{T('전략', 'strategy')} {sgn(m.retPct)}%</b>
				<i>vs</i>
				<b class={cls(result.bh.retPct)}>{T('보유', 'B&H')} {sgn(result.bh.retPct)}%</b>
				<em class={'bdExcess ' + cls(m.retPct - result.bh.retPct)}>{sgn(m.retPct - result.bh.retPct)}%p</em>
			</span>
			<button class="scrClose" onclick={onClose} aria-label="close">✕</button>
		</div>

		{#if multi}
			<!-- 전략 탭 — 포커스 전환(본문은 포커스 1전략). -->
			<div class="bdTabs">
				{#each pf.slots as s (s.id)}
					{@const meta = metaOf(s.id)}
					<button class="bdTab" class:on={s.id === focusId} onclick={() => onFocus(idxOf(s.id))}>
						<i class="bdSw" style={`background:${meta?.color ?? '#8b919e'}`}></i>{meta?.label ?? s.id}
						<em class={cls(s.result.metrics.retPct)}>{sgn(s.result.metrics.retPct)}%</em>
					</button>
				{/each}
			</div>
		{/if}

		<!-- 뷰 탭 — 개요·성과·거래·속성 -->
		<div class="bdViewTabs">
			{#each VIEW_TABS as v (v.k)}
				<button class="bdVtab" class:on={viewTab === v.k} onclick={() => (viewTab = v.k)}>{T(v.kr, v.en)}</button>
			{/each}
		</div>

		<div class="bdBody">
			{#if viewTab === 'overview'}
				{#if combo}
					<div class="bdCombo">
						{T('동일가중 조합 (리밸런싱 없음)', 'equal-weight combo (no rebalancing)')}
						· {T('수익률', 'return')} <b class={'mono ' + cls(combo.metrics.retPct)}>{sgn(combo.metrics.retPct)}%</b>
						· MDD <b class="mono tDn">{combo.metrics.mddPct.toFixed(1)}%</b>
						· Sharpe <b class="mono">{combo.metrics.sharpe != null ? combo.metrics.sharpe.toFixed(2) : '—'}</b>
						· Calmar <b class="mono">{combo.metrics.calmar != null ? combo.metrics.calmar.toFixed(2) : '—'}</b>
						· {T('vs 보유', 'vs B&H')} <b class={'mono ' + cls(combo.metrics.retPct - result.bh.retPct)}>{sgn(combo.metrics.retPct - result.bh.retPct)}%p</b>
						<i>{T('조합은 거래 단위 없음 — 승률·손익비 등 거래 KPI 미산출(equity 지표만). 단일종목 = 타이밍 분산이지 자산 분산 아님.', 'combo has no trades — equity metrics only. single-stock = timing, not asset diversification.')}</i>
					</div>
				{/if}
				<!-- 단일 구간 in-sample 배너(상존) -->
				<div class="bdBanner" class:lag={!beats}>
					{#if !beats}{T('이 구간에선 단순 보유(B&H)가 전략을 앞섰습니다.', 'Buy & hold beat the strategy over this window.')} {/if}{T('단일 구간 시뮬레이션입니다 — 다구간 교차검증(walk-forward · DSR · PBO)은 로컬 정밀 모드. 미래 수익 보장 아님 · 추천 아님.', 'Single-window simulation. Cross-validation (walk-forward · DSR · PBO) is in local precision mode. Not a forecast, not advice.')}
				</div>

				<!-- ★히어로 5지표 — 결과의 주인공(큰 활자). 표본<10·Sharpe<60봉·CAGR<252봉 → '—'(위계만 승격). -->
				<div class="btHero5">
					<div class="heroCard">
						<span>{T('전략 순수익', 'net return')}</span><b class={'mono ' + cls(m.retPct)}>{sgn(m.retPct)}%</b>
					</div>
					<div class="heroCard">
						<span>CAGR</span><b class={'mono ' + (m.cagrPct != null ? cls(m.cagrPct) : 'tNeu')}>{m.cagrPct != null ? sgn(m.cagrPct) + '%' : '—'}</b>
					</div>
					<div class="heroCard">
						<span>{T('최대 낙폭', 'max DD')}</span><b class="mono tDn">{m.mddPct.toFixed(1)}%</b>
					</div>
					<div class="heroCard">
						<span>Sharpe</span><b class="mono">{m.sharpe != null ? m.sharpe.toFixed(2) : '—'}</b>
					</div>
					<div class="heroCard">
						<span>{T('승률', 'win rate')}</span><b class="mono">{m.winRatePct != null ? m.winRatePct.toFixed(0) + '%' : '—'}</b><em>{result.trades.filter((t) => t.retPct > 0).length}/{m.tradeCount}</em>
					</div>
				</div>

				<!-- 자산 곡선 + 언더워터 (실측px·축·크로스헤어) -->
				<section class="bdSec">
					<div class="bdSecHd">{T('자산 곡선 — 계좌가치 추이 (시작 = 100)', 'equity curve — account value (start = 100)')}</div>
					<EquityChart {eq} {bhq} {dd} ts={tsWin} {splitFrac} {eqRange} {ddMin} {stratColor} {lang} />
					{#if oos}
						<div class="bdSubHd">{T('학습 / 검증 (OOS) — 고정 파라미터를 안 본 구간에 적용 (walk-forward 아님)', 'train / test (OOS) — fixed params on unseen window (not walk-forward)')}</div>
						<div class="bdOos">
							<div class="bdOosCol">
								<div class="bdOosTtl">{T('학습 (in-sample)', 'train')}</div>
								<div class="bdOosRow"><span>{T('수익률', 'return')}</span><b class={'mono ' + cls(oos.train.retPct)}>{sgn(oos.train.retPct)}%</b></div>
								<div class="bdOosRow"><span>Sharpe</span><b class="mono">{oos.train.sharpe != null ? oos.train.sharpe.toFixed(2) : '—'}</b></div>
								<div class="bdOosRow"><span>MDD</span><b class="mono tDn">{oos.train.mddPct.toFixed(1)}%</b></div>
								<div class="bdOosRow"><span>{T('거래', 'trades')}</span><b class="mono">{oos.train.tradeCount}</b></div>
							</div>
							<div class="bdOosArrow">
								<span class="bdOosArr">→</span>
								{#if oosDecay != null}
									<span class="bdOosDecay" class:dn={oosDecay < -2} class:up={oosDecay > 2}>Sharpe {oosDecay >= 0 ? '+' : ''}{oosDecay.toFixed(0)}%</span>
									<span class="bdOosDecayCap">{T('감쇠', 'decay')}</span>
								{/if}
							</div>
							<div class="bdOosCol test">
								<div class="bdOosTtl">{T('검증 (OOS)', 'test (OOS)')}</div>
								<div class="bdOosRow"><span>{T('수익률', 'return')}</span><b class={'mono ' + cls(oos.test.retPct)}>{sgn(oos.test.retPct)}%</b></div>
								<div class="bdOosRow"><span>Sharpe</span><b class="mono">{oos.test.sharpe != null ? oos.test.sharpe.toFixed(2) : '—'}</b></div>
								<div class="bdOosRow"><span>MDD</span><b class="mono tDn">{oos.test.mddPct.toFixed(1)}%</b></div>
								<div class="bdOosRow"><span>{T('거래', 'trades')}</span><b class="mono">{oos.test.tradeCount}</b></div>
							</div>
							{#if oos.test.retPct < oos.train.retPct}<div class="bdOosWarn">{T('⚠ 검증 성과가 학습보다 낮음 — 과최적화 신호', '⚠ test underperforms train — overfit risk')}</div>{/if}
						</div>
					{/if}
				</section>

				<!-- 보조 지표 — 2열 label/value 표(13px, 히어로 강등) -->
				<section class="bdSec">
					<div class="bdSecHd">{T('보조 지표', 'secondary metrics')}</div>
					<div class="auxGrid">
						<div class="auxRow"><span>{T('보유(B&H)', 'buy & hold')}</span><b class={'mono ' + cls(result.bh.retPct)}>{sgn(result.bh.retPct)}%</b></div>
						<div class="auxRow"><span>{T('초과 수익', 'excess')}</span><b class={'mono ' + cls(m.retPct - result.bh.retPct)}>{sgn(m.retPct - result.bh.retPct)}%p</b></div>
						<div class="auxRow"><span>Sortino</span><b class="mono">{m.sortino != null ? m.sortino.toFixed(2) : '—'}</b></div>
						<div class="auxRow"><span>{T('보유(B&H) Sharpe', 'B&H Sharpe')}</span><b class="mono">{result.bh.sharpe != null ? result.bh.sharpe.toFixed(2) : '—'}</b></div>
						<div class="auxRow"><span>{T('손익비', 'profit factor')}</span><b class="mono">{m.profitFactor != null ? m.profitFactor.toFixed(2) : '—'}</b></div>
						{#if tradeStats}
							<div class="auxRow"><span>{T('기대값/거래', 'expectancy')}</span><b class={'mono ' + (tradeStats.exp >= 0 ? 'tUp' : 'tDn')}>{tradeStats.exp >= 0 ? '+' : ''}{tradeStats.exp.toFixed(2)}%</b></div>
							{#if tradeStats.mae != null && tradeStats.mfe != null}
								<div class="auxRow"><span>{T('평균 MAE / MFE', 'avg MAE/MFE')}</span><b class="mono">{tradeStats.mae.toFixed(1)} / +{tradeStats.mfe.toFixed(1)}%</b></div>
							{/if}
						{/if}
						<div class="auxRow"><span>{T('평균 거래', 'avg trade')}</span><b class={'mono ' + (m.avgTradePct != null ? cls(m.avgTradePct) : 'tNeu')}>{m.avgTradePct != null ? sgn(m.avgTradePct) + '%' : '—'}</b></div>
						<div class="auxRow"><span>{T('최고 / 최악 거래', 'best / worst trade')}</span><b class="mono">{m.bestTradePct != null && m.worstTradePct != null ? sgn(m.bestTradePct, 0) + ' / ' + sgn(m.worstTradePct, 0) + '%' : '—'}</b></div>
						<div class="auxRow"><span>{T('노출', 'exposure')}</span><b class="mono">{m.exposurePct.toFixed(0)}%</b></div>
						<div class="auxRow"><span>{T('비용 드래그', 'cost drag')}</span><b class="mono tDn">{m.costDragPct.toFixed(1)}%p</b></div>
						<div class="auxRow"><span>{T('베타(vs B&H)', 'beta')}</span><b class="mono">{m.beta != null ? m.beta.toFixed(2) : '—'}</b></div>
						<div class="auxRow"><span>{T('알파(연)', 'alpha p.a.')}</span><b class={'mono ' + (m.alphaPct != null ? cls(m.alphaPct) : 'tNeu')}>{m.alphaPct != null ? sgn(m.alphaPct) + '%' : '—'}</b></div>
						<div class="auxRow"><span>{T('정보비율', 'info ratio')}</span><b class={'mono ' + (m.infoRatio != null ? cls(m.infoRatio) : 'tNeu')}>{m.infoRatio != null ? m.infoRatio.toFixed(2) : '—'}</b></div>
					</div>
				</section>
			{/if}

			{#if viewTab === 'performance'}
				<!-- 월별 수익률 히트맵 — quant 시그니처 -->
				<section class="bdSec">
					<div class="bdSecHd">{T('월별 수익률', 'monthly returns')}</div>
					<MonthlyReturnsHeatmap {eq} ts={tsWin} {lang} />
				</section>

				<!-- 연간 수익률 — 전략 vs 보유. 연도 의존성(한두 해 몰아주기 여부) 노출 -->
				<section class="bdSec">
					<div class="bdSecHd">{T('연간 수익률 — 전략 vs 보유', 'yearly returns — strategy vs B&H')}</div>
					<YearlyReturnsBars {eq} {bhq} ts={tsWin} {lang} />
				</section>

				<!-- 거래별 수익률 분포 — 꼬리·치우침(Sharpe가 가리는 것) -->
				{#if result.trades.length >= 2}
					<section class="bdSec">
						<div class="bdSecHd">{T('거래 수익률 분포', 'trade return distribution')}</div>
						<ReturnHistogram rets={result.trades.map((t) => t.retPct)} {lang} />
					</section>
				{/if}

				<!-- 낙폭 분석 -->
				<section class="bdSec">
					<div class="bdSecHd">{T('낙폭 분석', 'drawdown analysis')}</div>
					<div class="auxGrid">
						<div class="auxRow"><span>{T('최대 낙폭', 'max drawdown')}</span><b class="mono tDn">{m.mddPct.toFixed(1)}%</b></div>
						<div class="auxRow"><span>{T('최장 수면', 'longest underwater')}</span><b class="mono">{m.mddDays != null ? m.mddDays + T('거래일', 'd') : '—'}</b></div>
						<div class="auxRow"><span>{T('회복 여부', 'recovered')}</span><b class={'mono ' + (recovered ? 'tUp' : 'tDn')}>{recovered ? T('회복함', 'yes') : T('미회복', 'no')}</b></div>
						<div class="auxRow"><span>{T('보유(B&H) MDD', 'B&H MDD')}</span><b class="mono tDn">{result.bh.mddPct.toFixed(1)}%</b></div>
					</div>
					{#if worstTrades.length}
						<div class="bdSubHd">{T('최악 거래 (낙폭 기여 상위)', 'worst trades')}</div>
						<div class="bdTableWrap">
							<table class="bdTable mono">
								<thead><tr><th>{T('진입', 'entry')}</th><th>{T('청산', 'exit')}</th><th class="r">{T('수익률', 'ret')}</th><th class="r">{T('보유일', 'days')}</th></tr></thead>
								<tbody>
									{#each worstTrades as t (t.entryT)}
										<tr class="bdRow" onclick={() => jumpToBar(t.entryT)}>
											<td>{fmtD(t.entryT)}</td><td>{t.exitT ? fmtD(t.exitT) : T('보유중', 'open')}</td>
											<td class={'r ' + cls(t.retPct)}>{sgn(t.retPct)}%</td><td class="r">{t.holdDays}</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{/if}
				</section>
			{/if}

			{#if viewTab === 'trades'}
				{#if result.trades.some((t) => t.maePct != null)}
					<section class="bdSec">
						<div class="bdSecHd">{T('거래별 위험·보상 (MAE 산점)', 'per-trade risk/reward (MAE scatter)')}</div>
						<TradeScatter trades={result.trades} {lang} onPick={jumpToBar} />
						<div class="bdNote">{T('각 점 = 한 거래. 왼쪽일수록 보유 중 깊은 역행(MAE)을 견딘 거래 — 왼쪽 위(초록)는 거의 손실 볼 뻔하다 살아난 승자. 점 클릭 → 차트의 진입봉.', 'each dot = one trade. Further left = endured a deeper drawdown while held; top-left greens nearly turned losing. Click a dot → entry bar on chart.')}</div>
					</section>
				{/if}
				<section class="bdSec">
					<div class="bdSecHd">{T('거래 내역', 'trades')} <span class="bdN">{m.tradeCount}</span><button class="bdCsv" onclick={exportCsv}>{T('CSV 내보내기', 'export CSV')}</button><span class="bdHint">{T('행 클릭 → 차트의 해당 진입봉으로', 'click row → jump to chart')}</span></div>
					{#if result.trades.length}
						<div class="bdTableWrap tall">
							<table class="bdTable mono">
								<thead><tr><th>{T('진입', 'entry')}</th><th class="r">{T('진입가', 'in')}</th><th>{T('청산', 'exit')}</th><th class="r">{T('청산가', 'out')}</th><th class="r">{T('수익률', 'ret')}</th><th class="r">{T('누적', 'cum')}</th><th class="r">{T('보유일', 'days')}</th><th>{T('사유', 'reason')}</th></tr></thead>
								<tbody>
									{#each result.trades.slice().reverse() as t, i (t.entryT)}
										{@const cum = cumPct[result.trades.length - 1 - i]}
										<tr class="bdRow" onclick={() => jumpToBar(t.entryT)} title={T('차트로 이동', 'jump to chart')}>
											<td>{fmtD(t.entryT)}</td>
											<td class="r">{num(t.entryPx)}</td>
											<td>{t.exitT ? fmtD(t.exitT) : T('보유중', 'open')}</td>
											<td class="r">{t.exitPx != null ? num(t.exitPx) : '—'}</td>
											<td class={'r ' + cls(t.retPct)}>{sgn(t.retPct)}%</td>
											<td class={'r ' + cls(cum)}>{sgn(cum)}%</td>
											<td class="r">{t.holdDays}</td>
											<td class="dim">{t.exitReason === 'finalMark' ? T('미청산', 'open') : t.exitReason === 'stop' ? T('손절', 'stop') : t.exitReason === 'take' ? T('익절', 'take') : T('신호', 'signal')}</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{:else}
						<div class="bdEmpty">{T('이 구간에서 진입 거래가 없습니다.', 'no entries in this window.')}</div>
					{/if}
				</section>
			{/if}

			{#if viewTab === 'properties'}
				<section class="bdSec">
					<div class="bdSecHd">{T('체결·데이터 가정', 'execution & data assumptions')}</div>
					<ul class="bdAssume">
						<li>{T('신호 t일 종가 확정 → t+1일 시가 체결 (미래참조 구조적 차단)', 'signal close(t) → fill open(t+1) · look-ahead blocked')}</li>
						<li>{T('거래정지(거래량 0) 봉 = 체결 자동 이연', 'halted bars defer fills')}{result.deferredBars > 0 ? ` · ${result.deferredBars}${T('봉 이연', ' bars deferred')}` : ''}</li>
						<li>{withCosts ? T('비용 반영 — 수수료 0.015% + 거래세 0.15% + 슬리피지 0.1% (편집 가능)', 'costs on — fee 0.015% + tax 0.15% + slippage 0.1%') : T('⚠ 비용 미포함 — 실거래 대비 낙관', '⚠ costs excluded — optimistic vs live')}</li>
						<li>{T('벤치마크 = 보유(B&H), 전략과 동일 비용 적용 (공정 비교)', 'benchmark = buy & hold, same costs')}</li>
						<li class="warn">{T('⚠ 배당 미반영', '⚠ dividends excluded')} · {adjusted ? T('수정주가 반영', 'split-adjusted') : T('⚠ 무수정주가 — 분할 시 B&H 왜곡', '⚠ unadjusted — splits distort B&H')} — {T('B&H를 체계적으로 깎아 전략이 상대적으로 좋아 보일 수 있음', 'depresses B&H; strategy may look relatively better')}</li>
					</ul>
					{#if rs}
						<div class="bdSubHd">{T('실행 명세 (RunSpec)', 'run spec')}</div>
						<div class="bdSpec mono">
							<span>{T('종목', 'symbol')}: {rs.symbol.name ?? ''} {rs.symbol.code}</span>
							<span>{T('전략', 'strategy')}: {rs.strategy.id} ({Object.entries(rs.strategy.params).map(([k, v]) => `${k}=${v}`).join(' ')})</span>
							<span>{T('구간', 'range')}: {fmtD(rs.range.from)} ~ {fmtD(rs.range.to)} · {rs.range.bars}{T('봉', ' bars')}</span>
							<span>{T('기준일', 'as of')}: {fmtD(rs.dataAsOf)} · {T('데이터', 'source')}: {rs.dataSource} · {T('엔진', 'engine')} {rs.engineVersion}</span>
						</div>
					{/if}
					<div class="bdFoot">⚠ {T('과거 가정 노출형 시뮬레이션 — 미래 수익 보장 없음 · 추천 아님', 'assumption-exposed historical simulation — no guarantee · not advice')} │ {GOV_ATTRIBUTION}</div>
				</section>
			{/if}
		</div>
	</div>
</div>

<style>
	.bdModal {
		width: min(1080px, 96vw);
		max-height: 92vh;
	}
	.bdStrat {
		font-size: 13px;
		font-weight: 700;
		color: var(--dl-ink, #c8cfdb);
	}
	.bdStrat i {
		font-style: normal;
		font-weight: 400;
		margin-left: 8px;
		font-size: 11px;
		color: #aeb6c2;
	}
	.bdHeadline {
		margin-left: auto;
		display: flex;
		align-items: baseline;
		gap: 9px;
		font-size: 17px;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
	}
	.bdHeadline i {
		font-style: normal;
		font-size: 11px;
		font-weight: 400;
		color: var(--dimmer);
	}
	.bdExcess {
		font-style: normal;
		font-size: 12px;
		font-weight: 700;
		padding: 1px 7px;
		border-radius: 9px;
		border: 1px solid var(--dl-line, #1b2130);
	}
	/* 전략 포커스 탭 */
	.bdTabs {
		display: flex;
		gap: 4px;
		padding: 6px 18px 0;
		flex-wrap: wrap;
	}
	.bdTab {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		background: none;
		border: 1px solid var(--dl-line, #1b2130);
		border-radius: 5px;
		padding: 4px 10px;
		cursor: pointer;
		font-family: inherit;
		font-size: 11.5px;
		color: #aeb6c2;
	}
	.bdTab.on {
		background: rgba(255, 255, 255, 0.03);
		color: var(--dl-ink, #c8cfdb);
		border-color: #2a3142;
	}
	.bdTab .bdSw {
		width: 9px;
		height: 9px;
		border-radius: 2px;
		display: inline-block;
	}
	.bdTab em {
		font-style: normal;
		font-family: var(--dl-font-mono, monospace);
		font-size: 11px;
		font-variant-numeric: tabular-nums;
	}
	/* 뷰 탭 — 개요·성과·거래·속성 */
	.bdViewTabs {
		display: flex;
		gap: 2px;
		padding: 8px 18px 0;
		border-bottom: 1px solid var(--dl-line, #1b2130);
	}
	.bdVtab {
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		color: var(--dim, #8b94a3);
		font-family: inherit;
		font-size: 11.5px;
		font-weight: 700;
		letter-spacing: 0.04em;
		text-transform: uppercase;
		padding: 5px 12px 7px;
		cursor: pointer;
		margin-bottom: -1px;
	}
	.bdVtab:hover {
		color: #aeb6c2;
	}
	.bdVtab.on {
		color: var(--dl-ink, #c8cfdb);
		border-bottom-color: var(--amber, #fb923c);
	}
	.bdBody {
		flex: 1 1 auto;
		min-height: 0;
		overflow-y: auto;
		padding: 14px 18px 18px;
		display: flex;
		flex-direction: column;
		gap: 18px;
	}
	.bdCombo {
		font-size: 11px;
		color: #cbb4f5;
		background: rgba(232, 121, 249, 0.07);
		border: 1px solid rgba(232, 121, 249, 0.25);
		border-radius: 4px;
		padding: 7px 12px;
		line-height: 1.6;
		display: flex;
		align-items: baseline;
		gap: 5px;
		flex-wrap: wrap;
		font-variant-numeric: tabular-nums;
	}
	.bdCombo b {
		font-weight: 700;
	}
	.bdCombo i {
		flex-basis: 100%;
		font-style: normal;
		font-size: 10px;
		color: #8b94a3;
	}
	.bdBanner {
		font-size: 11px;
		color: #93c5fd;
		background: rgba(96, 165, 250, 0.08);
		border: 1px solid rgba(96, 165, 250, 0.25);
		border-radius: 4px;
		padding: 7px 12px;
		line-height: 1.55;
	}
	.bdBanner.lag {
		color: #fbbf77;
		background: rgba(251, 146, 60, 0.08);
		border-color: rgba(251, 146, 60, 0.3);
	}
	/* ★히어로 5지표 */
	.btHero5 {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
		gap: 8px;
	}
	.heroCard {
		display: flex;
		flex-direction: column;
		gap: 2px;
		padding: 10px 12px;
		background: rgba(255, 255, 255, 0.02);
		border: 1px solid var(--dl-line, #1b2130);
		border-radius: 5px;
	}
	.heroCard > span {
		font-size: 11px;
		color: var(--dim, #8b94a3);
	}
	.heroCard > b {
		font-size: 22px;
		font-weight: 700;
		line-height: 1.1;
		color: var(--dl-ink, #c8cfdb);
		font-variant-numeric: tabular-nums;
	}
	.heroCard > em {
		font-style: normal;
		font-size: 10px;
		color: var(--dimmer);
		font-family: var(--dl-font-mono, monospace);
		font-variant-numeric: tabular-nums;
	}
	.bdSec {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.bdSecHd {
		font-size: 11.5px;
		font-weight: 700;
		letter-spacing: 0.04em;
		color: #aeb6c2;
		text-transform: uppercase;
		display: flex;
		align-items: center;
		gap: 10px;
	}
	.bdN {
		font-family: var(--dl-font-mono, monospace);
		font-size: 11px;
		color: var(--dimmer);
		font-weight: 400;
	}
	.bdCsv {
		background: none;
		border: 1px solid var(--dl-line-strong, #2a3142);
		color: #aeb6c2;
		font-size: 11px;
		padding: 2px 9px;
		border-radius: 3px;
		cursor: pointer;
		font-family: inherit;
	}
	.bdCsv:hover {
		color: var(--dl-ink, #c8cfdb);
		border-color: #3a4456;
	}
	.bdHint {
		font-size: 10px;
		color: var(--dimmer);
		font-weight: 400;
		text-transform: none;
		letter-spacing: 0;
		margin-left: auto;
	}
	/* 보조 지표 / 낙폭 분석 — 2열 label/value */
	.auxGrid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
		gap: 4px 16px;
	}
	.auxRow {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		padding: 5px 10px;
		background: rgba(255, 255, 255, 0.015);
		border: 1px solid var(--dl-line, #1b2130);
		border-radius: 4px;
		font-size: 13px;
	}
	.auxRow > span {
		color: #aeb6c2;
	}
	.auxRow > b {
		font-weight: 700;
		color: var(--dl-ink, #c8cfdb);
		font-variant-numeric: tabular-nums;
	}
	.bdSubHd {
		font-size: 11px;
		color: #8b94a3;
		margin-top: 8px;
		letter-spacing: 0.02em;
	}
	.bdNote {
		font-size: 10.5px;
		color: var(--dim, #8b94a3);
		line-height: 1.55;
		padding: 0 2px;
	}
	/* OOS 2열 */
	.bdOos {
		display: flex;
		align-items: stretch;
		gap: 12px;
		flex-wrap: wrap;
	}
	.bdOosCol {
		flex: 1 1 200px;
		border: 1px solid var(--dl-line, #1b2130);
		border-radius: 4px;
		padding: 8px 12px;
	}
	.bdOosCol.test {
		border-color: rgba(96, 165, 250, 0.4);
	}
	.bdOosTtl {
		font-size: 11px;
		font-weight: 700;
		color: #aeb6c2;
		margin-bottom: 5px;
	}
	.bdOosCol.test .bdOosTtl {
		color: #60a5fa;
	}
	.bdOosRow {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		font-size: 11.5px;
		color: #aeb6c2;
		padding: 2px 0;
		font-variant-numeric: tabular-nums;
	}
	.bdOosRow b {
		font-size: 13px;
		color: var(--dl-ink, #c8cfdb);
	}
	.bdOosArrow {
		align-self: center;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1px;
	}
	.bdOosArr {
		color: var(--dimmer);
		font-size: 16px;
		line-height: 1;
	}
	.bdOosDecay {
		font-family: var(--dl-font-mono, monospace);
		font-size: 12px;
		font-weight: 700;
		color: #aeb6c2;
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}
	.bdOosDecay.dn {
		color: var(--dn, #f0616f);
	}
	.bdOosDecay.up {
		color: var(--up, #34d399);
	}
	.bdOosDecayCap {
		font-size: 9.5px;
		color: var(--dimmer);
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}
	.bdOosWarn {
		flex-basis: 100%;
		font-size: 11px;
		color: var(--amber, #fb923c);
	}
	/* 거래표 */
	.bdTableWrap {
		max-height: 300px;
		overflow-y: auto;
		border: 1px solid var(--dl-line, #1b2130);
		border-radius: 4px;
	}
	.bdTableWrap.tall {
		max-height: 460px;
	}
	.bdTable {
		width: 100%;
		border-collapse: collapse;
		font-size: 13px;
		font-variant-numeric: tabular-nums;
	}
	.bdTable thead th {
		position: sticky;
		top: 0;
		background: var(--dl-bg-raised, #0e141f);
		text-align: left;
		color: #8b94a3;
		font-weight: 600;
		padding: 6px 10px;
		border-bottom: 1px solid var(--dl-line-strong, #2a3142);
		font-size: 11px;
	}
	.bdTable th.r,
	.bdTable td.r {
		text-align: right;
	}
	.bdTable td {
		padding: 5px 10px;
		border-bottom: 1px solid rgba(27, 33, 48, 0.6);
		color: #aeb6c2;
	}
	.bdTable td.dim {
		color: var(--dimmer);
	}
	.bdRow {
		cursor: pointer;
	}
	.bdRow:hover td {
		background: rgba(96, 165, 250, 0.1);
	}
	.bdEmpty {
		font-size: 11px;
		color: var(--dimmer);
		padding: 14px;
		text-align: center;
	}
	/* 가정 */
	.bdAssume {
		margin: 0;
		padding-left: 18px;
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.bdAssume li {
		font-size: 11.5px;
		color: #aeb6c2;
		line-height: 1.55;
	}
	.bdAssume li.warn {
		color: var(--amber, #fb923c);
	}
	.bdSpec {
		display: flex;
		flex-direction: column;
		gap: 2px;
		font-size: 11px;
		color: #8b94a3;
	}
	.bdFoot {
		font-size: 11px;
		color: var(--dimmer);
		margin-top: 6px;
		line-height: 1.5;
	}
	/* 톤 색 */
	.tUp {
		color: var(--up, #34d399);
	}
	.tDn {
		color: var(--dn, #f0616f);
	}
	.tNeu {
		color: #aeb6c2;
	}
</style>
