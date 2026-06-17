<script lang="ts">
	// 백테스트 전문 화면 — 차트 위 [백테스팅 상세] 버튼 → 모달. 깨알 하단 strip(못 읽음) 폐기.
	// 구성: ① 에쿼티·낙폭 곡선 시각화(전략 vs 보유 + OOS 음영 = "어떻게 흘러갔는지") ② 아래로 스크롤되는 읽히는 상세내역
	//   (개요 KPI 격자 · 거래표 · 낙폭 · 가정/RunSpec). 큰 활자(11~16px) — 증권사 리포트 가독성.
	// 거래행 클릭 → onFocusBar(날짜) + onClose → 메인차트 해당 진입봉 센터링. 정직 라벨·동일비용 B&H·추천 아님.
	import type { PortfolioBtResult, StrategySlot } from '../lib/backtest';
	import { GOV_ATTRIBUTION } from '@dartlab/ui-contracts';
	import type { Lang } from '../lib/types';

	interface Props {
		pf: PortfolioBtResult;
		slots: StrategySlot[]; // 전체 슬롯(메타) — pf.slots 는 워밍업 통과분만이라 id 매칭
		focus: number;
		period: string;
		withCosts: boolean;
		adjusted: boolean;
		lang: Lang;
		onFocus: (i: number) => void;
		onClose: () => void;
		onFocusBar?: (t: string) => void; // 거래/낙폭 행 클릭 → 차트 해당 봉 (PriceChart 가 scrollToTimestamp)
	}
	let { pf, slots, focus, period, withCosts, adjusted, lang, onFocus, onClose, onFocusBar }: Props = $props();
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	// 본문은 포커스 1전략 단수 유지(01 §5 dialog 무전면개조) — result 를 포커스 슬롯 파생으로 두면 기존 본문 무변경.
	const focusId = $derived(slots[focus]?.id ?? slots[0]?.id);
	const result = $derived(pf.slots.find((s) => s.id === focusId)?.result ?? pf.slots[0].result);
	const presetLabel = $derived(slots.find((s) => s.id === focusId)?.label ?? '');
	const combo = $derived(pf.combo);
	const multi = $derived(pf.slots.length >= 2);
	const metaOf = (id: string) => slots.find((s) => s.id === id);
	const idxOf = (id: string) => slots.findIndex((s) => s.id === id);
	const m = $derived(result.metrics);
	const rs = $derived(result.runSpec);
	const oos = $derived(result.oos);
	const sgn = (v: number, d = 1) => (v >= 0 ? '+' : '') + v.toFixed(d);
	const cls = (v: number) => (v > 0 ? 'tUp' : v < 0 ? 'tDn' : 'tNeu');
	const fmtD = (t: string) => (t && t.length >= 8 ? `${t.slice(0, 4)}.${t.slice(4, 6)}.${t.slice(6, 8)}` : '—');
	const num = (v: number, d = 0) => v.toLocaleString('en-US', { maximumFractionDigits: d });
	const beats = $derived(m.retPct >= result.bh.retPct);

	// ── 에쿼티 곡선 데이터 — 평가창 내 non-null 슬라이스(전략·보유 동일 길이). x=봉 인덱스, y=계좌가치(시작 100). ──
	const eq = $derived(result.equity.filter((v): v is number => v != null));
	const bhq = $derived(result.bhEquity.filter((v): v is number => v != null));
	const nBars = $derived(eq.length);
	// 낙폭(언더워터) — 전략 누적 최고점 대비 하락률(≤0).
	const dd = $derived.by(() => {
		let peak = -Infinity;
		return eq.map((v) => { if (v > peak) peak = v; return peak > 0 ? (v / peak - 1) * 100 : 0; });
	});
	// OOS 분할 위치(평가창 내 상대 비율) — 곡선 위 검증구간 음영.
	const splitFrac = $derived.by<number | null>(() => {
		if (!oos || nBars < 2) return null;
		const rel = oos.splitIdx - result.startIdx;
		if (rel <= 0 || rel >= nBars) return null;
		return rel / (nBars - 1);
	});
	// y 범위(전략+보유 합산) — 두 곡선이 한 스케일에 정직 비교되도록.
	const eqRange = $derived.by(() => {
		const all = [...eq, ...bhq];
		if (!all.length) return { lo: 90, hi: 110 };
		let lo = Math.min(...all), hi = Math.max(...all);
		if (hi - lo < 1) { lo -= 1; hi += 1; }
		return { lo, hi };
	});
	const ddMin = $derived(dd.length ? Math.min(...dd, -1) : -1);
	const W = 1000, H_EQ = 230, H_DD = 78, VPAD = 8;
	function poly(arr: number[], lo: number, hi: number, h: number): string {
		const span = (hi - lo) || 1;
		const n = arr.length;
		return arr.map((v, i) => `${(n < 2 ? 0 : (i / (n - 1)) * W).toFixed(1)},${(h - ((v - lo) / span) * (h - 2 * VPAD) - VPAD).toFixed(1)}`).join(' ');
	}
	// 낙폭 영역 채움 path — 0라인에서 곡선 아래로.
	const ddArea = $derived.by(() => {
		if (dd.length < 2) return '';
		const lo = ddMin, hi = 0, span = (hi - lo) || 1, n = dd.length;
		const y = (v: number) => (H_DD - ((v - lo) / span) * (H_DD - 2 * VPAD) - VPAD).toFixed(1);
		const x = (i: number) => ((i / (n - 1)) * W).toFixed(1);
		let d = `M0,${y(0)}`;
		dd.forEach((v, i) => { d += ` L${x(i)},${y(v)}`; });
		d += ` L${W},${y(0)} Z`;
		return d;
	});
	const baseY = $derived.by(() => {
		const { lo, hi } = eqRange;
		const span = (hi - lo) || 1;
		return (H_EQ - ((100 - lo) / span) * (H_EQ - 2 * VPAD) - VPAD).toFixed(1); // 시작값(100) 기준선 y
	});

	// 누적 P&L (시간순) — 거래표 누적 칸.
	const cumPct = $derived.by(() => {
		let acc = 1;
		return result.trades.map((t) => { acc *= 1 + t.retPct / 100; return (acc - 1) * 100; });
	});
	const worstTrades = $derived([...result.trades].sort((a, b) => a.retPct - b.retPct).slice(0, 6));
	const recovered = $derived(result.mddWindow?.recoverIdx != null);

	function jumpToBar(t: string) { onFocusBar?.(t); onClose(); }

	// Trades CSV — 브라우저 zero-dep Blob (egress 전체는 table-export PRD 영역, 여기선 거래내역만).
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

	// KPI 카드 정의 — 라벨·값·툴팁. 값 포맷은 인라인.
	$effect(() => {
		const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});
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
			<!-- 전략 탭 — 포커스 전환(본문은 포커스 1전략). 조합은 아래 배너(거래 단위 없어 별도 탭 아님). -->
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

		<div class="bdBody">
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
			<!-- 정직 배너 — 단일 구간 in-sample. 다구간 교차검증은 로컬 정밀 모드. -->
			<div class="bdBanner" class:lag={!beats}>
				{#if !beats}{T('이 구간에선 단순 보유(B&H)가 전략을 앞섰습니다.', 'Buy & hold beat the strategy over this window.')} {/if}{T('단일 구간 시뮬레이션입니다 — 다구간 교차검증(walk-forward · DSR · PBO)은 로컬 정밀 모드. 미래 수익 보장 아님 · 추천 아님.', 'Single-window simulation. Cross-validation (walk-forward · DSR · PBO) is in local precision mode. Not a forecast, not advice.')}
			</div>

			<!-- ① 에쿼티·낙폭 곡선 — 전략(앰버) vs 보유(슬레이트), 시작 100 기준. 검증(OOS) 구간 음영. -->
			<section class="bdSec">
				<div class="bdSecHd">{T('자산 곡선 — 계좌가치 추이 (시작 = 100)', 'equity curve — account value (start = 100)')}</div>
				<div class="bdChartWrap">
					<div class="bdYlab top">{sgn(eqRange.hi - 100, 0)}%</div>
					<div class="bdYlab bot">{sgn(eqRange.lo - 100, 0)}%</div>
					<svg class="bdSvg" viewBox={`0 0 ${W} ${H_EQ}`} preserveAspectRatio="none" role="img" aria-label={T('자산 곡선', 'equity curve')}>
						{#if splitFrac != null}
							<rect x={(splitFrac * W).toFixed(1)} y="0" width={((1 - splitFrac) * W).toFixed(1)} height={H_EQ} fill="rgba(96,165,250,0.07)" />
							<line x1={(splitFrac * W).toFixed(1)} y1="0" x2={(splitFrac * W).toFixed(1)} y2={H_EQ} stroke="rgba(96,165,250,0.55)" stroke-width="1" stroke-dasharray="4 3" />
						{/if}
						<line x1="0" y1={baseY} x2={W} y2={baseY} stroke="rgba(139,145,158,0.3)" stroke-width="1" stroke-dasharray="2 4" />
						<polyline points={poly(bhq, eqRange.lo, eqRange.hi, H_EQ)} fill="none" stroke="#8b919e" stroke-width="1.4" stroke-dasharray="5 3" vector-effect="non-scaling-stroke" />
						<polyline points={poly(eq, eqRange.lo, eqRange.hi, H_EQ)} fill="none" stroke="#fb923c" stroke-width="2" vector-effect="non-scaling-stroke" />
					</svg>
				</div>
				{#if splitFrac != null}
					<div class="bdSplitLbls"><span style={`width:${(splitFrac * 100).toFixed(1)}%`}>{T('학습 (in-sample)', 'train (in-sample)')}</span><span class="test">{T('검증 (out-of-sample)', 'test (out-of-sample)')}</span></div>
				{/if}
				<div class="bdSecHd dd">{T('낙폭 (언더워터) — 누적 최고점 대비 하락', 'drawdown (underwater)')}</div>
				<div class="bdChartWrap dd">
					<svg class="bdSvg" viewBox={`0 0 ${W} ${H_DD}`} preserveAspectRatio="none" role="img" aria-label={T('낙폭', 'drawdown')}>
						<path d={ddArea} fill="rgba(240,97,111,0.18)" stroke="none" />
						<polyline points={poly(dd, ddMin, 0, H_DD)} fill="none" stroke="#f0616f" stroke-width="1.4" vector-effect="non-scaling-stroke" />
					</svg>
					<div class="bdYlab bot dn">{ddMin.toFixed(0)}%</div>
				</div>
				<div class="bdXlabs"><span>{rs ? fmtD(rs.range.from) : ''}</span>{#if oos}<span>{fmtD(oos.splitT)}</span>{/if}<span>{rs ? fmtD(rs.range.to) : ''}</span></div>
				<div class="bdLegend"><span class="lk strat"></span>{T('전략', 'strategy')}<span class="lk bh"></span>{T('보유(B&H) · 동일 비용', 'buy & hold · same costs')}<span class="lk ddk"></span>{T('낙폭', 'drawdown')}</div>
			</section>

			<!-- ② 개요 — 핵심 지표 카드(큰 활자). -->
			<section class="bdSec">
				<div class="bdSecHd">{T('개요 — 성과 지표', 'overview — performance')}</div>
				<div class="bdGrid">
					<div class="bdCard"><span>{T('전략 수익률', 'strategy return')}</span><b class={'mono ' + cls(m.retPct)}>{sgn(m.retPct)}%</b></div>
					<div class="bdCard"><span>{T('보유(B&H)', 'buy & hold')}</span><b class={'mono ' + cls(result.bh.retPct)}>{sgn(result.bh.retPct)}%</b></div>
					<div class="bdCard"><span>{T('초과 수익', 'excess')}</span><b class={'mono ' + cls(m.retPct - result.bh.retPct)}>{sgn(m.retPct - result.bh.retPct)}%p</b></div>
					<div class="bdCard"><span>CAGR</span><b class={'mono ' + (m.cagrPct != null ? cls(m.cagrPct) : 'tNeu')}>{m.cagrPct != null ? sgn(m.cagrPct) + '%' : '—'}</b></div>
					<div class="bdCard" title={T('일수익률 연환산 · 무위험 0', 'annualized daily · rf=0')}><span>Sharpe</span><b class="mono">{m.sharpe != null ? m.sharpe.toFixed(2) : '—'}</b><i>{result.bh.sharpe != null ? `${T('보유', 'B&H')} ${result.bh.sharpe.toFixed(2)}` : ''}</i></div>
					<div class="bdCard" title={T('하방 변동성 기준', 'downside deviation')}><span>Sortino</span><b class="mono">{m.sortino != null ? m.sortino.toFixed(2) : '—'}</b></div>
					<div class="bdCard"><span>MDD</span><b class="mono tDn">{m.mddPct.toFixed(1)}%</b><i>{T('보유', 'B&H')} {result.bh.mddPct.toFixed(1)}%</i></div>
					<div class="bdCard"><span>{T('승률', 'win rate')}</span><b class="mono">{m.winRatePct != null ? m.winRatePct.toFixed(0) + '%' : '—'}</b><i>{result.trades.filter((t) => t.retPct > 0).length}/{m.tradeCount}</i></div>
					<div class="bdCard"><span>{T('손익비', 'profit factor')}</span><b class="mono">{m.profitFactor != null ? m.profitFactor.toFixed(2) : '—'}</b></div>
					<div class="bdCard" title={T('거래당 평균 (최고/최악)', 'avg per trade')}><span>{T('평균 거래', 'avg trade')}</span><b class={'mono ' + (m.avgTradePct != null ? cls(m.avgTradePct) : 'tNeu')}>{m.avgTradePct != null ? sgn(m.avgTradePct) + '%' : '—'}</b>{#if m.bestTradePct != null && m.worstTradePct != null}<i>{sgn(m.bestTradePct, 0)}/{sgn(m.worstTradePct, 0)}</i>{/if}</div>
					<div class="bdCard"><span>{T('노출', 'exposure')}</span><b class="mono">{m.exposurePct.toFixed(0)}%</b></div>
					<div class="bdCard"><span>{T('비용 드래그', 'cost drag')}</span><b class="mono tDn">{m.costDragPct.toFixed(1)}%p</b></div>
					<div class="bdCard" title={T('전략 일수익률의 보유 대비 민감도', 'sensitivity to B&H')}><span>{T('베타(vs B&H)', 'beta')}</span><b class="mono">{m.beta != null ? m.beta.toFixed(2) : '—'}</b></div>
					<div class="bdCard" title={T('베타 설명분 초과 수익(연환산)', 'beta-adj excess, annualized')}><span>{T('알파(연)', 'alpha p.a.')}</span><b class={'mono ' + (m.alphaPct != null ? cls(m.alphaPct) : 'tNeu')}>{m.alphaPct != null ? sgn(m.alphaPct) + '%' : '—'}</b></div>
					<div class="bdCard" title={T('액티브 수익 / 추적오차(연환산)', 'active return / tracking error')}><span>{T('정보비율', 'info ratio')}</span><b class={'mono ' + (m.infoRatio != null ? cls(m.infoRatio) : 'tNeu')}>{m.infoRatio != null ? m.infoRatio.toFixed(2) : '—'}</b></div>
				</div>
				{#if oos}
					<div class="bdSubHd">{T('학습 / 검증 (OOS) — 고정 파라미터를 안 본 구간에 적용 (walk-forward 아님)', 'train / test (OOS) — fixed params on unseen window (not walk-forward)')}</div>
					<div class="bdOos">
						<div class="bdOosCol"><div class="bdOosTtl">{T('학습 (in-sample)', 'train')}</div>
							<div class="bdOosRow"><span>{T('수익률', 'return')}</span><b class={'mono ' + cls(oos.train.retPct)}>{sgn(oos.train.retPct)}%</b></div>
							<div class="bdOosRow"><span>Sharpe</span><b class="mono">{oos.train.sharpe != null ? oos.train.sharpe.toFixed(2) : '—'}</b></div>
							<div class="bdOosRow"><span>MDD</span><b class="mono tDn">{oos.train.mddPct.toFixed(1)}%</b></div>
							<div class="bdOosRow"><span>{T('거래', 'trades')}</span><b class="mono">{oos.train.tradeCount}</b></div>
						</div>
						<div class="bdOosArrow">→</div>
						<div class="bdOosCol test"><div class="bdOosTtl">{T('검증 (OOS)', 'test (OOS)')}</div>
							<div class="bdOosRow"><span>{T('수익률', 'return')}</span><b class={'mono ' + cls(oos.test.retPct)}>{sgn(oos.test.retPct)}%</b></div>
							<div class="bdOosRow"><span>Sharpe</span><b class="mono">{oos.test.sharpe != null ? oos.test.sharpe.toFixed(2) : '—'}</b></div>
							<div class="bdOosRow"><span>MDD</span><b class="mono tDn">{oos.test.mddPct.toFixed(1)}%</b></div>
							<div class="bdOosRow"><span>{T('거래', 'trades')}</span><b class="mono">{oos.test.tradeCount}</b></div>
						</div>
						{#if oos.test.retPct < oos.train.retPct}<div class="bdOosWarn">{T('⚠ 검증 성과가 학습보다 낮음 — 과최적화 신호', '⚠ test underperforms train — overfit risk')}</div>{/if}
					</div>
				{/if}
			</section>

			<!-- ③ 거래 — 전체 내역. 행 클릭 → 다이얼로그 닫고 차트 해당 진입봉. -->
			<section class="bdSec">
				<div class="bdSecHd">{T('거래 내역', 'trades')} <span class="bdN">{m.tradeCount}</span><button class="bdCsv" onclick={exportCsv}>{T('CSV 내보내기', 'export CSV')}</button><span class="bdHint">{T('행 클릭 → 차트의 해당 진입봉으로', 'click row → jump to chart')}</span></div>
				{#if result.trades.length}
					<div class="bdTableWrap">
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
										<td class="dim">{t.exitReason === 'finalMark' ? T('미청산', 'open') : T('신호', 'signal')}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{:else}
					<div class="bdEmpty">{T('이 구간에서 진입 거래가 없습니다.', 'no entries in this window.')}</div>
				{/if}
			</section>

			<!-- ④ 낙폭 분석 -->
			<section class="bdSec">
				<div class="bdSecHd">{T('낙폭 분석', 'drawdown analysis')}</div>
				<div class="bdGrid">
					<div class="bdCard"><span>{T('최대 낙폭', 'max drawdown')}</span><b class="mono tDn">{m.mddPct.toFixed(1)}%</b></div>
					<div class="bdCard"><span>{T('최장 수면', 'longest underwater')}</span><b class="mono">{m.mddDays != null ? m.mddDays + T('거래일', 'd') : '—'}</b></div>
					<div class="bdCard"><span>{T('회복 여부', 'recovered')}</span><b class={'mono ' + (recovered ? 'tUp' : 'tDn')}>{recovered ? T('회복함', 'yes') : T('미회복', 'no')}</b></div>
					<div class="bdCard"><span>{T('보유(B&H) MDD', 'B&H MDD')}</span><b class="mono tDn">{result.bh.mddPct.toFixed(1)}%</b></div>
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

			<!-- ⑤ 가정 · 실행 명세 -->
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
		</div>
	</div>
</div>

<style>
	.bdModal { width: min(1080px, 96vw); max-height: 92vh; }
	.bdStrat { font-size: 13px; font-weight: 700; color: var(--dl-ink, #c8cfdb); }
	.bdStrat i { font-style: normal; font-weight: 400; margin-left: 8px; font-size: 10.5px; color: #aeb6c2; }
	.bdHeadline { margin-left: auto; display: flex; align-items: baseline; gap: 8px; font-size: 14px; font-weight: 700; }
	.bdHeadline i { font-style: normal; font-size: 10px; font-weight: 400; color: var(--dimmer); }
	.bdExcess { font-style: normal; font-size: 11px; font-weight: 700; padding: 1px 7px; border-radius: 9px; border: 1px solid var(--dl-line, #1b2130); }
	/* 전략 탭 */
	.bdTabs { display: flex; gap: 4px; padding: 6px 18px 0; flex-wrap: wrap; border-bottom: 1px solid var(--dl-line, #1b2130); }
	.bdTab { display: inline-flex; align-items: center; gap: 6px; background: none; border: 1px solid var(--dl-line, #1b2130); border-bottom: none; border-radius: 5px 5px 0 0; padding: 5px 11px; cursor: pointer; font-family: inherit; font-size: 11.5px; color: #aeb6c2; }
	.bdTab.on { background: rgba(255, 255, 255, 0.03); color: var(--dl-ink, #c8cfdb); border-color: #2a3142; }
	.bdTab .bdSw { width: 9px; height: 9px; border-radius: 2px; display: inline-block; }
	.bdTab em { font-style: normal; font-family: var(--dl-font-mono, monospace); font-size: 11px; }
	.bdCombo { font-size: 11px; color: #cbb4f5; background: rgba(232, 121, 249, 0.07); border: 1px solid rgba(232, 121, 249, 0.25); border-radius: 4px; padding: 7px 12px; line-height: 1.6; display: flex; align-items: baseline; gap: 5px; flex-wrap: wrap; }
	.bdCombo b { font-weight: 700; }
	.bdCombo i { flex-basis: 100%; font-style: normal; font-size: 10px; color: #8b94a3; }
	.bdBody { flex: 1 1 auto; min-height: 0; overflow-y: auto; padding: 14px 18px 18px; display: flex; flex-direction: column; gap: 18px; }
	.bdBanner { font-size: 11px; color: #93c5fd; background: rgba(96, 165, 250, 0.08); border: 1px solid rgba(96, 165, 250, 0.25); border-radius: 4px; padding: 7px 12px; line-height: 1.55; }
	.bdBanner.lag { color: #fbbf77; background: rgba(251, 146, 60, 0.08); border-color: rgba(251, 146, 60, 0.3); }
	.bdSec { display: flex; flex-direction: column; gap: 8px; }
	.bdSecHd { font-size: 11.5px; font-weight: 700; letter-spacing: 0.04em; color: #aeb6c2; text-transform: uppercase; display: flex; align-items: center; gap: 10px; }
	.bdSecHd.dd { margin-top: 6px; }
	.bdN { font-family: var(--dl-font-mono, monospace); font-size: 11px; color: var(--dimmer); font-weight: 400; }
	.bdCsv { background: none; border: 1px solid var(--dl-line-strong, #2a3142); color: #aeb6c2; font-size: 10px; padding: 2px 9px; border-radius: 3px; cursor: pointer; font-family: inherit; }
	.bdCsv:hover { color: var(--dl-ink, #c8cfdb); border-color: #3a4456; }
	.bdHint { font-size: 10px; color: var(--dimmer); font-weight: 400; text-transform: none; letter-spacing: 0; margin-left: auto; }
	/* 자산 곡선 */
	.bdChartWrap { position: relative; width: 100%; height: 230px; background: rgba(8, 11, 18, 0.55); border: 1px solid var(--dl-line, #1b2130); border-radius: 4px; }
	.bdChartWrap.dd { height: 78px; }
	.bdSvg { display: block; width: 100%; height: 100%; }
	.bdYlab { position: absolute; right: 6px; font-family: var(--dl-font-mono, monospace); font-size: 9.5px; color: var(--dimmer); pointer-events: none; }
	.bdYlab.top { top: 4px; }
	.bdYlab.bot { bottom: 4px; }
	.bdYlab.dn { color: rgba(240, 97, 111, 0.8); }
	.bdSplitLbls { display: flex; font-size: 9.5px; color: var(--dimmer); }
	.bdSplitLbls span { padding: 0 4px; }
	.bdSplitLbls .test { color: #60a5fa; }
	.bdXlabs { display: flex; justify-content: space-between; font-family: var(--dl-font-mono, monospace); font-size: 9.5px; color: var(--dimmer); margin-top: -2px; }
	.bdLegend { display: flex; align-items: center; gap: 5px; font-size: 10px; color: #aeb6c2; }
	.bdLegend .lk { display: inline-block; width: 14px; height: 0; border-top-width: 2px; border-top-style: solid; margin: 0 1px 0 10px; }
	.bdLegend .lk:first-child { margin-left: 0; }
	.bdLegend .lk.strat { border-top-color: #fb923c; }
	.bdLegend .lk.bh { border-top-color: #8b919e; border-top-style: dashed; }
	.bdLegend .lk.ddk { border-top-color: #f0616f; }
	/* KPI 카드 격자 — 읽히는 큰 활자 */
	.bdGrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
	.bdCard { display: flex; flex-direction: column; gap: 2px; padding: 8px 10px; background: rgba(255, 255, 255, 0.02); border: 1px solid var(--dl-line, #1b2130); border-radius: 4px; }
	.bdCard > span { font-size: 10.5px; color: #aeb6c2; }
	.bdCard > b { font-size: 17px; font-weight: 700; color: var(--dl-ink, #c8cfdb); line-height: 1.1; }
	.bdCard > i { font-style: normal; font-size: 9.5px; color: var(--dimmer); font-family: var(--dl-font-mono, monospace); }
	.bdSubHd { font-size: 10.5px; color: #8b94a3; margin-top: 8px; letter-spacing: 0.02em; }
	/* OOS 2열 */
	.bdOos { display: flex; align-items: stretch; gap: 12px; flex-wrap: wrap; }
	.bdOosCol { flex: 1 1 200px; border: 1px solid var(--dl-line, #1b2130); border-radius: 4px; padding: 8px 12px; }
	.bdOosCol.test { border-color: rgba(96, 165, 250, 0.4); }
	.bdOosTtl { font-size: 10.5px; font-weight: 700; color: #aeb6c2; margin-bottom: 5px; }
	.bdOosCol.test .bdOosTtl { color: #60a5fa; }
	.bdOosRow { display: flex; justify-content: space-between; align-items: baseline; font-size: 11px; color: #aeb6c2; padding: 2px 0; }
	.bdOosRow b { font-size: 13px; color: var(--dl-ink, #c8cfdb); }
	.bdOosArrow { align-self: center; color: var(--dimmer); font-size: 16px; }
	.bdOosWarn { flex-basis: 100%; font-size: 10.5px; color: var(--amber, #fb923c); }
	/* 거래표 */
	.bdTableWrap { max-height: 320px; overflow-y: auto; border: 1px solid var(--dl-line, #1b2130); border-radius: 4px; }
	.bdTable { width: 100%; border-collapse: collapse; font-size: 11.5px; }
	.bdTable thead th { position: sticky; top: 0; background: var(--dl-bg-raised, #0e141f); text-align: left; color: #8b94a3; font-weight: 600; padding: 6px 10px; border-bottom: 1px solid var(--dl-line-strong, #2a3142); }
	.bdTable th.r, .bdTable td.r { text-align: right; }
	.bdTable td { padding: 5px 10px; border-bottom: 1px solid rgba(27, 33, 48, 0.6); color: #aeb6c2; }
	.bdTable td.dim { color: var(--dimmer); }
	.bdRow { cursor: pointer; }
	.bdRow:hover td { background: rgba(96, 165, 250, 0.1); }
	.bdEmpty { font-size: 11px; color: var(--dimmer); padding: 14px; text-align: center; }
	/* 가정 */
	.bdAssume { margin: 0; padding-left: 18px; display: flex; flex-direction: column; gap: 4px; }
	.bdAssume li { font-size: 11px; color: #aeb6c2; line-height: 1.55; }
	.bdAssume li.warn { color: var(--amber, #fb923c); }
	.bdSpec { display: flex; flex-direction: column; gap: 2px; font-size: 10.5px; color: #8b94a3; }
	.bdFoot { font-size: 10px; color: var(--dimmer); margin-top: 6px; line-height: 1.5; }
	/* 톤 색 — 터미널 토큰 */
	.tUp { color: var(--up, #34d399); }
	.tDn { color: var(--dn, #f0616f); }
	.tNeu { color: #aeb6c2; }
</style>
