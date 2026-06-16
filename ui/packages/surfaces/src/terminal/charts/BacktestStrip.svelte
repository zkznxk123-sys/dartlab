<script lang="ts">
	// 백테스트 결과 바 — 차트 하단 슬림 1줄(읽히는 헤드라인만). 깨알 15-KPI·OOS 2열·도크 폐기 →
	// 상세 전부는 [백테스팅 상세] 버튼 → BacktestDialog(전문 화면). 전략 열위 시 dim(초록 축포 금지).
	import type { BtResult, BtWarning } from '../lib/backtest';
	import { GOV_ATTRIBUTION } from '@dartlab/ui-contracts';
	import type { Lang } from '../lib/types';

	interface Props {
		result: BtResult;
		presetLabel: string;
		period: string;
		withCosts: boolean;
		adjusted: boolean; // 수정주가 입력 여부 — 각주 정확성
		lang: Lang;
		onClear: () => void;
		onOpenReport: () => void; // [백테스팅 상세] → 부모가 BacktestDialog 오픈
	}
	let { result, presetLabel, period, withCosts, adjusted, lang, onClear, onOpenReport }: Props = $props();
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	const m = $derived(result.metrics);
	const sgn = (v: number, d = 1) => (v >= 0 ? '+' : '') + v.toFixed(d);
	const cls = (v: number) => (v > 0 ? 'tUp' : v < 0 ? 'tDn' : 'tNeu');
	const beats = $derived(m.retPct >= result.bh.retPct);
	const fmtDate = (t: string) => `${t.slice(2, 4)}.${t.slice(4, 6)}.${t.slice(6, 8)}`;
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
		<span class={'btExcess mono ' + cls(m.retPct - result.bh.retPct)}>{sgn(m.retPct - result.bh.retPct)}%p</span>
		<span class="btSpacer"></span>
		{#each result.warnings as w (w.kind)}
			<span class="btWarn" title={w.date ?? ''}>{T(WARN_LABEL[w.kind].kr, WARN_LABEL[w.kind].en)}{w.date ? ' ' + fmtDate(w.date) : ''}</span>
		{/each}
		<button class="btMore" onclick={onOpenReport} title={T('전문 화면 — 자산곡선·거래·낙폭·가정', 'professional view')}>{T('백테스팅 상세', 'details')} ▸</button>
		<button class="btClose" onclick={onClear} title={T('백테스트 해제', 'clear backtest')}>✕</button>
	</div>
	<div class="btFoot">
		⚠ {T('과거 시뮬레이션 — 미래 수익 보장 없음 · 익일 시가 체결', 'historical simulation — no guarantee · next-open fills')}
		· {withCosts ? T('수수료·세금·슬리피지 반영', 'fees·tax·slippage on') : T('비용 미포함', 'costs excluded')}
		· {adjusted ? T('배당 미반영 · 수정주가', 'dividends excluded · adjusted') : T('배당 미반영 · 무수정주가', 'dividends excluded · unadjusted')}{#if result.runSpec} · {T('기준일', 'as of')} {fmtDate(result.runSpec.dataAsOf)}{/if} │ {GOV_ATTRIBUTION}
	</div>
</div>
