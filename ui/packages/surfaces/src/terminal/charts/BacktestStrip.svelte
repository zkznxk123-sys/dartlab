<script lang="ts">
	// 백테스트 결과 바 — 차트 하단 슬림. 다전략(N≤3): 조합 헤드라인 + 전략별 미니행(클릭=포커스).
	// 전략 열위 시 dim(초록 축포 금지). 상세 전부는 [백테스팅 상세] → BacktestDialog.
	// 정직(04 §2.2·2.4): N≥2 = selection 경고 + "타이밍 분산이지 자산 분산 아님" 상존(닫기 불가).
	import type { PortfolioBtResult, StrategySlot, BtWarning } from '../lib/backtest';
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
		onClear: () => void;
		onOpenReport: () => void;
	}
	let { pf, slots, focus, period, withCosts, adjusted, lang, onFocus, onClear, onOpenReport }: Props = $props();
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	const sgn = (v: number, d = 1) => (v >= 0 ? '+' : '') + v.toFixed(d);
	const cls = (v: number) => (v > 0 ? 'tUp' : v < 0 ? 'tDn' : 'tNeu');
	const fmtDate = (t: string) => `${t.slice(2, 4)}.${t.slice(4, 6)}.${t.slice(6, 8)}`;

	const multi = $derived(pf.slots.length >= 2);
	const bhRet = $derived(pf.slots[0]?.result.bh.retPct ?? 0);
	const focusId = $derived(slots[focus]?.id ?? slots[0]?.id);
	const focusRes = $derived(pf.slots.find((s) => s.id === focusId)?.result ?? pf.slots[0]?.result ?? null);
	// 헤드라인 = 조합(있으면) 또는 포커스 전략. 조합 곡선이 개별 위/아래인지 한 자 비교.
	const headRet = $derived(pf.combo ? pf.combo.metrics.retPct : focusRes?.metrics.retPct ?? 0);
	const headLabel = $derived(pf.combo ? T('조합', 'combo') : slots.find((s) => s.id === focusId)?.label ?? '');
	// 조합 MDD < 개별 MDD = 분산효과 시각 증거(타이밍 분산). null 안전.
	const comboMddBetter = $derived.by(() => {
		if (!pf.combo) return false;
		const worst = Math.min(...pf.slots.map((s) => s.result.metrics.mddPct));
		return pf.combo.metrics.mddPct > worst; // 덜 깊으면(0 에 가까우면) 개선
	});
	const metaOf = (id: string) => slots.find((s) => s.id === id);
	const idxOf = (id: string) => slots.findIndex((s) => s.id === id);
	const WARN_LABEL: Record<BtWarning['kind'], { kr: string; en: string }> = {
		fewTrades: { kr: '표본 부족', en: 'few trades' },
		shortRange: { kr: '기간 부족 — 참고용', en: 'short range' },
		splitSuspect: { kr: '분할 의심 — 구간 무효', en: 'split suspect' },
		costsOff: { kr: '비용 미포함', en: 'costs off' }
	};
</script>

<div class="btStrip" class:btLag={headRet < bhRet}>
	<div class="btHead">
		<b class={'btRet mono ' + cls(headRet)}>{headLabel} {sgn(headRet)}%</b>
		<span class="btVs">vs</span>
		<b class={'btRet mono ' + cls(bhRet)}>{T('보유', 'B&H')} {sgn(bhRet)}%</b>
		<span class={'btExcess mono ' + cls(headRet - bhRet)}>{sgn(headRet - bhRet)}%p</span>
		<span class="btDot">·</span>
		<!-- 전략별 미니행 — 색칩 + 라벨 + 수익률. 클릭 = 포커스(마커·리포트 전환). -->
		{#each pf.slots as s (s.id)}
			{@const meta = metaOf(s.id)}
			<button class="btChip" class:on={s.id === focusId} onclick={() => onFocus(idxOf(s.id))} title={T('이 전략에 포커스 (마커·상세)', 'focus this strategy')}>
				<i class="btSw" style={`background:${meta?.color ?? '#8b919e'}`}></i>
				<span class="btChipLbl">{meta?.label ?? s.id}</span>
				<b class={'mono ' + cls(s.result.metrics.retPct)}>{sgn(s.result.metrics.retPct)}%</b>
			</button>
		{/each}
		<span class="btSpacer"></span>
		{#each focusRes?.warnings ?? [] as w (w.kind)}
			<span class="btWarn" title={w.date ?? ''}>{T(WARN_LABEL[w.kind].kr, WARN_LABEL[w.kind].en)}{w.date ? ' ' + fmtDate(w.date) : ''}</span>
		{/each}
		<button class="btMore" onclick={onOpenReport} title={T('전문 화면 — 자산곡선·거래·낙폭·가정', 'professional view')}>{T('백테스팅 상세', 'details')} ▸</button>
		<button class="btClose" onclick={onClear} title={T('백테스트 해제', 'clear backtest')}>✕</button>
	</div>
	{#if multi}
		<div class="btSel">
			⚠ {T('여러 전략을 같은 데이터에 비교 = 사후선택 편향(위 곡선이 미래 최고 아님)', 'comparing strategies on the same data = selection bias')}
			· {T('단일종목 조합 = 타이밍 분산이지 자산 분산 아님(분산효과 주장 금지)', 'single-stock combo = timing diversification, not asset diversification')}
			{#if pf.combo}· {T('조합 = 동일가중 보유합성(리밸런싱 없음)', 'combo = equal-weight, no rebalancing')}{#if comboMddBetter} · {T('조합 낙폭이 개별보다 얕음', 'combo MDD shallower than singles')}{/if}{/if}
		</div>
	{/if}
	<div class="btFoot">
		⚠ {T('과거 시뮬레이션 — 미래 수익 보장 없음 · 익일 시가 체결', 'historical simulation — no guarantee · next-open fills')}
		· {withCosts ? T('수수료·세금·슬리피지 반영', 'fees·tax·slippage on') : T('비용 미포함', 'costs excluded')}
		· {adjusted ? T('배당 미반영 · 수정주가', 'dividends excluded · adjusted') : T('배당 미반영 · 무수정주가', 'dividends excluded · unadjusted')}{#if focusRes?.runSpec} · {T('기준일', 'as of')} {fmtDate(focusRes.runSpec.dataAsOf)}{/if} │ {GOV_ATTRIBUTION}
	</div>
</div>

<style>
	.btStrip { background: var(--dl-bg-raised, #0e141f); border-top: 1px solid var(--dl-line, #1b2130); padding: 5px 12px 4px; font-size: 11.5px; }
	.btStrip.btLag { opacity: 0.92; }
	.btHead { display: flex; align-items: center; gap: 7px; flex-wrap: wrap; }
	.btRet { font-size: 12.5px; font-weight: 700; }
	.btVs { color: #6b7280; font-size: 10px; }
	.btExcess { font-size: 10.5px; font-weight: 700; padding: 1px 6px; border-radius: 8px; border: 1px solid var(--dl-line, #1b2130); }
	.btDot { color: #3a4456; }
	.btChip { display: inline-flex; align-items: center; gap: 5px; background: none; border: 1px solid var(--dl-line, #1b2130); border-radius: 12px; padding: 1px 8px 1px 5px; cursor: pointer; font-family: inherit; font-size: 10.5px; color: #aeb6c2; }
	.btChip:hover { border-color: #3a4456; }
	.btChip.on { border-color: #3a4456; background: rgba(255, 255, 255, 0.04); }
	.btSw { width: 9px; height: 9px; border-radius: 2px; display: inline-block; }
	.btChipLbl { color: var(--dl-ink, #c8cfdb); }
	.btChip b { font-size: 10.5px; }
	.btSpacer { flex: 1 1 auto; }
	.btWarn { font-size: 9.5px; color: var(--amber, #fb923c); border: 1px solid rgba(251, 146, 60, 0.3); border-radius: 3px; padding: 0 5px; }
	.btMore { background: none; border: 1px solid var(--dl-line-strong, #2a3142); color: #aeb6c2; font-size: 10px; padding: 2px 9px; border-radius: 3px; cursor: pointer; font-family: inherit; }
	.btMore:hover { color: var(--dl-ink, #c8cfdb); border-color: #3a4456; }
	.btClose { background: none; border: none; color: #6b7280; cursor: pointer; font-size: 13px; padding: 0 2px; }
	.btClose:hover { color: var(--dl-ink, #c8cfdb); }
	.btSel { font-size: 9.5px; color: #8b94a3; margin-top: 3px; line-height: 1.5; }
	.btFoot { font-size: 9.5px; color: #6b7280; margin-top: 3px; line-height: 1.4; }
	.tUp { color: var(--up, #34d399); }
	.tDn { color: var(--dn, #f0616f); }
	.tNeu { color: #aeb6c2; }
</style>
