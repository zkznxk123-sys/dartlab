<script lang="ts">
	// 타법인 출자 관계 분석 — 전체화면 다이얼로그. 신규 능력 0: 3축 진단은 전부 lib/holdings.ts(렌더 0 계산
	// 모듈) 산물(공동배선 = 퍼블릭·로컬 동일). 모달 크롬은 전역 .scrimWrap/.scrModal/.scrHead 재사용, 표는 finTable.
	// 정직: 매수/매도·목표주가·인과 금지. 결손(null)은 0 으로 뭉개지 않고 '—'/분리. parentNet 미상이면 contribShare 생략.
	import type { Company, Lang } from '../lib/types';
	import type { InvestmentRow, InvestmentTrendYear } from '@dartlab/ui-contracts';
	import { buildHoldingsModel, type ListedLookup, type HoldingTier } from '../lib/holdings';
	import { fmtKRW } from '../lib/engine';

	interface Props {
		co: Company;
		year: string;
		rows: InvestmentRow[];
		trend: InvestmentTrendYear[];
		lang: Lang;
		lookupListed: ListedLookup;
		onPick: (code: string) => void;
		onClose: () => void;
	}
	let { co, year, rows, trend, lang, lookupListed, onPick, onClose }: Props = $props();
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);

	// 본체 재무 주입(원) — 시총 = 캔들 보정 mktcapRaw(원). 순익은 시총/PER 근사(둘 다 원 → 단위 안전).
	// PER null·≤0(적자·미산출)면 parentNet=null → contribShare 자동 생략(정직, 0 대체 금지).
	const parentMktcap = $derived(co.price.mktcapRaw ?? null);
	const parentNet = $derived(co.fundamentals.per && co.fundamentals.per > 0 && co.price.mktcapRaw ? co.price.mktcapRaw / co.fundamentals.per : null);
	const m = $derived(buildHoldingsModel(year, rows, lookupListed, parentMktcap, parentNet));

	const TIER_LABEL: Record<HoldingTier, { kr: string; en: string; cls: string }> = {
		consolidated: { kr: '연결', en: 'CONS', cls: 'tUp' },
		equity: { kr: '지분법', en: 'EQ', cls: 'tGood' },
		simple: { kr: '단순', en: 'SIMPLE', cls: 'tNeu' },
		unknown: { kr: '분류불가', en: 'n/a', cls: 'tNeu' }
	};
	const krw = (v: number | null) => (v == null ? '—' : fmtKRW(v));
	const ratioCls = (r: number | null, mid = 1) => (r == null ? 'tNeu' : r > mid ? 'tUp' : r < mid ? 'tDn' : 'tNeu');
	const trendMax = $derived(Math.max(...trend.map((t) => t.bookTotal ?? 0), 1));

	$effect(() => {
		const onKey = (e: KeyboardEvent) => {
			if (e.key === 'Escape') onClose();
		};
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});
</script>

<div class="scrimWrap" role="presentation" onclick={onClose}>
	<div class="scrModal hdModal" role="dialog" aria-modal="true" aria-label={T('출자 관계 분석', 'holdings analysis')} onclick={(e) => e.stopPropagation()}>
		<div class="scrHead">
			<span class="scrTitle">{T('출자 관계 분석', 'HOLDINGS — relationship analysis')} · {co.name.kr} · {m.year}</span>
			<span class="hdSub dim">{T('피출자사', 'holdings')} {m.rows.length}{T('개', '')} · {T('장부가 합', 'book')} {krw(m.bookTotal)}</span>
			<button class="scrClose" onclick={onClose} aria-label="close">✕</button>
		</div>

		<div class="hdBody">
			<!-- 3축 요약: ① 성격·위계(tier) ② 가치(상장지분 시가·본체비중) ③ 효율(이익기여·본체순익비중) -->
			<div class="hdSummary">
				<div class="hdSumCard">
					<div class="hdSumLbl">{T('성격 · 위계', 'TIER')}</div>
					<div class="hdTierRow">
						{#if m.counts.consolidated}<span class="hdTier tUp">{T('연결', 'cons')} {m.counts.consolidated}</span>{/if}
						{#if m.counts.equity}<span class="hdTier tGood">{T('지분법', 'eq')} {m.counts.equity}</span>{/if}
						{#if m.counts.simple}<span class="hdTier tNeu">{T('단순', 'simple')} {m.counts.simple}</span>{/if}
						{#if m.counts.unknown}<span class="hdTier tNeu">{T('분류불가', 'n/a')} {m.counts.unknown}</span>{/if}
					</div>
					<div class="hdSumSub dim">{T('상장', 'listed')} {m.counts.listed} · {T('비상장', 'unlisted')} {m.counts.unlisted}{m.counts.loss ? ' · ' + T('적자피출자', 'loss') + ' ' + m.counts.loss : ''}</div>
				</div>
				<div class="hdSumCard">
					<div class="hdSumLbl">{T('가치 — 상장 보유지분 시가', 'VALUE — listed stake')}</div>
					<div class="hdSumV mono">{krw(m.listedStakeSum)}</div>
					<div class="hdSumSub dim">{m.pctOfParentCap != null ? T('본체 시총 대비 ', 'of parent cap ') + m.pctOfParentCap.toFixed(1) + '%' : T('본체 시총 대비 — (미산출)', 'parent cap n/a')}</div>
				</div>
				<div class="hdSumCard">
					<div class="hdSumLbl">{T('효율 — 지분법 이익기여(근사)', 'EFFICIENCY — equity earnings (approx)')}</div>
					<div class={'hdSumV mono ' + (m.sumEquityEarn > 0 ? 'tUp' : m.sumEquityEarn < 0 ? 'tDn' : 'tNeu')}>{krw(m.sumEquityEarn)}</div>
					<div class="hdSumSub dim">{m.contribShare != null ? T('본체 순익 대비 ', 'of parent net ') + m.contribShare.toFixed(1) + '%' : T('본체 순익 대비 — (참고·미산출)', 'parent net n/a')}</div>
				</div>
			</div>

			{#if trend.length > 1}
				<!-- 출자 추이 — 장부가 합 연도별(자본 잠김 방향). 그래프 금지 구역 아님(다이얼로그 = 중앙 확장) -->
				<div class="hdTrend">
					<span class="hdTrendLbl dim">{T('출자 장부가 추이', 'book trend')}</span>
					{#each trend as t (t.year)}
						<div class="hdTrendBar" title={`${t.year} · ${krw(t.bookTotal)} · ${t.count}${T('사', '')}`}>
							<div class="hdTrendFill" style={`height:${Math.round(((t.bookTotal ?? 0) / trendMax) * 100)}%`}></div>
							<span class="hdTrendYr">{t.year.slice(2)}</span>
						</div>
					{/each}
				</div>
			{/if}

			<div class="hdScroll">
				<table class="finTable hdTable">
					<thead>
						<tr>
							<th class="finAcct">{T('법인명', 'COMPANY')}</th>
							<th>{T('성격', 'TIER')}</th>
							<th class="r">{T('지분', 'STAKE')}</th>
							<th class="r">{T('장부가', 'BOOK')}</th>
							<th class="r">{T('시가지분', 'MKT STAKE')}</th>
							<th class="r" title={T('시가/장부 (>1 숨은가치, <1 잠재손상) — 상장만', 'market/book')}>{T('시가/장부', 'M/B')}</th>
							<th class="r" title={T('장부/취득 (>1 평가이익 누적, <1 손상가능)', 'book/cost')}>{T('장부/취득', 'B/C')}</th>
							<th class="r">{T('피출자 순익', 'TGT NET')}</th>
							<th class="r" title={T('지분법 이익기여 근사 (지분% × 피출자순익)', 'equity earnings approx')}>{T('이익기여', 'EQ EARN')}</th>
							<th class="r" title={T('이익기여/장부가', 'eq earn / book')}>{T('투자ROIC', 'iROIC')}</th>
						</tr>
					</thead>
					<tbody>
						{#each m.rows as h (h.name)}
							<tr class={h.tier === 'consolidated' ? 'finKey' : ''}>
								<td class="finAcct" title={h.purpose}>
									{#if h.code}
										<button type="button" class="hdLink" onclick={() => onPick(h.code!)}>{h.name}</button>
									{:else}{h.name}{/if}
									{#if h.intent}<span class="hdIntent" title={T('경영참여 의사', 'management intent')}>{T('경영참여', 'intent')}</span>{/if}
								</td>
								<td><span class={'hdTierMini ' + TIER_LABEL[h.tier].cls}>{T(TIER_LABEL[h.tier].kr, TIER_LABEL[h.tier].en)}</span></td>
								<td class="r mono">{h.stakePct != null ? h.stakePct.toFixed(1) + '%' : '—'}</td>
								<td class="r mono">{krw(h.bookValue)}</td>
								<td class="r mono">{krw(h.marketStake)}</td>
								<td class={'r mono ' + ratioCls(h.gapRatio)}>{h.gapRatio != null ? h.gapRatio.toFixed(2) + '×' : '—'}</td>
								<td class={'r mono ' + ratioCls(h.markRatio)}>{h.markRatio != null ? h.markRatio.toFixed(2) + '×' : '—'}</td>
								<td class={'r mono ' + (h.targetNet != null && h.targetNet < 0 ? 'tDn' : '')}>{h.targetNet != null ? (h.targetNet < 0 ? '-' : '') + fmtKRW(Math.abs(h.targetNet)) : '—'}</td>
								<td class={'r mono ' + (h.equityEarn != null && h.equityEarn < 0 ? 'tDn' : h.equityEarn != null && h.equityEarn > 0 ? 'tUp' : '')}>{h.equityEarn != null ? (h.equityEarn < 0 ? '-' : '') + fmtKRW(Math.abs(h.equityEarn)) : '—'}</td>
								<td class={'r mono ' + (h.investROIC != null ? (h.investROIC > 0 ? 'tUp' : h.investROIC < 0 ? 'tDn' : 'tNeu') : 'tNeu')}>{h.investROIC != null ? (h.investROIC * 100).toFixed(1) + '%' : '—'}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>

			<div class="hdNote dim">
				{T(
					'report · 타법인 출자현황. 이익기여는 지분법 근사(내부거래·공정가치 미반영), 시가지분은 상장 해소된 피출자사만, 피출자 순익은 최근 1기 단일값. 미해소·null 은 0 대체 없이 분리 표기. 판정·목표주가 아님.',
					'report · holdings. Equity earnings are an approximation; market stake covers listed holdings only; target net is the latest single period. Nulls are not coerced to zero. Not a verdict or price target.'
				)}
			</div>
		</div>
	</div>
</div>

<style>
	.hdModal {
		width: min(1100px, 96vw);
		max-height: 90vh;
		display: flex;
		flex-direction: column;
	}
	.hdSub {
		font-size: 10px;
		margin-left: auto;
		margin-right: 10px;
	}
	.hdBody {
		overflow: auto;
		padding: 10px 12px 12px;
	}
	.hdSummary {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 8px;
		margin-bottom: 10px;
	}
	.hdSumCard {
		border: 1px solid var(--bd);
		border-radius: 3px;
		padding: 7px 9px;
		background: var(--dl-bg-base, rgba(255, 255, 255, 0.02));
	}
	.hdSumLbl {
		font-size: 9px;
		color: var(--dim);
		letter-spacing: 0.4px;
		text-transform: uppercase;
		margin-bottom: 4px;
	}
	.hdSumV {
		font-size: 15px;
		font-weight: 700;
	}
	.hdSumSub {
		font-size: 9.5px;
		margin-top: 2px;
	}
	.hdTierRow {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
	}
	.hdTier {
		font-size: 11px;
		font-weight: 700;
		border: 1px solid currentColor;
		border-radius: 2px;
		padding: 1px 5px;
	}
	.hdTrend {
		display: flex;
		align-items: flex-end;
		gap: 4px;
		height: 56px;
		margin-bottom: 10px;
		padding-left: 4px;
	}
	.hdTrendLbl {
		font-size: 9px;
		align-self: center;
		writing-mode: horizontal-tb;
		margin-right: 6px;
		white-space: nowrap;
	}
	.hdTrendBar {
		position: relative;
		width: 22px;
		height: 100%;
		display: flex;
		flex-direction: column;
		justify-content: flex-end;
		align-items: center;
	}
	.hdTrendFill {
		width: 14px;
		background: var(--good, #5b9bf0);
		opacity: 0.7;
		border-radius: 1px 1px 0 0;
		min-height: 1px;
	}
	.hdTrendYr {
		font-size: 8px;
		color: var(--dim);
		margin-top: 1px;
	}
	.hdScroll {
		overflow-x: auto;
	}
	.hdTable {
		width: 100%;
		font-size: 11px;
	}
	.hdLink {
		background: none;
		border: none;
		color: var(--accent, #5b9bf0);
		cursor: pointer;
		padding: 0;
		font: inherit;
		text-align: left;
	}
	.hdLink:hover {
		text-decoration: underline;
	}
	.hdIntent {
		font-size: 8px;
		color: var(--amber, #fb923c);
		border: 1px solid rgba(251, 146, 60, 0.4);
		border-radius: 2px;
		padding: 0 3px;
		margin-left: 5px;
		vertical-align: 1px;
	}
	.hdTierMini {
		font-size: 9.5px;
		font-weight: 700;
	}
	.hdNote {
		font-size: 9px;
		line-height: 1.5;
		margin-top: 8px;
		padding-top: 6px;
		border-top: 1px solid var(--bd);
	}
</style>
