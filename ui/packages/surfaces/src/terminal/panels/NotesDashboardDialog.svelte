<script lang="ts">
	// 주석 상세 — 비용 체질 + 부문별 매출. 카드별 = 100% 스택바(당기 구성 한눈에) + 분기별 구성 테이블(밀도).
	// 데이터 = panel 정부 XBRL 태그 런타임 직독(reportSource.noteSeries). 종합점수·판정 0(NEVER-CLAIM).
	import type { Company, Lang } from '../lib/types';
	import type { CompositionSeries } from '@dartlab/ui-contracts';
	import { fmtKRW } from '../lib/engine';

	interface Props {
		co: Company;
		lang: Lang;
		cost: CompositionSeries | null;
		segment: CompositionSeries | null;
		onClose: () => void;
	}
	let { co, lang, cost, segment, onClose }: Props = $props();
	const T = (kr: string, en: string): string => (lang === 'en' ? en : kr);

	$effect(() => {
		const onKey = (e: KeyboardEvent) => {
			if (e.key === 'Escape') onClose();
		};
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});

	const PAL = ['var(--dl-cat-start)', 'var(--dl-cat-operation)', 'var(--dl-cat-engines)', 'var(--dl-cat-runtime)', 'var(--dl-cat-recipes)', 'var(--dl-accent)', 'var(--up)', 'var(--warn)'];
	const catColor = (i: number, name: string): string => (name === '기타' ? 'var(--dimmer)' : (PAL[i % PAL.length] ?? 'var(--dim)'));
	const niceName = (n: string): string => {
		if (n === '기타') return T('기타', 'other');
		const t = n.replace(/\s*및\s*/g, '·').replace(/(매입액|사용액|비용|비$)/g, '').trim();
		if (/^[A-Za-z]{1,4}$/.test(t)) return t.toUpperCase();
		return t.replace(/([a-z])([A-Z])/g, '$1 $2').slice(0, 16);
	};
	const shortPeriod = (p: string): string => p.replace(/^20/, '');

	interface TblRow {
		name: string;
		color: string;
		pcts: (number | null)[];
		latestPct: number;
		amt: number;
	}
	interface TblCard {
		titleKr: string;
		titleEn: string;
		subKr: string;
		subEn: string;
		quarters: string[];
		rows: TblRow[];
		latestPeriod: string;
		latestTotal: number;
		annual: boolean;
	}
	function makeCard(series: CompositionSeries | null, titleKr: string, titleEn: string, subKr: string, subEn: string): TblCard | null {
		if (!series || !series.points.length) return null;
		const pts = series.points;
		const last = pts[pts.length - 1]!;
		const rows: TblRow[] = series.categories
			.map((name, c) => ({
				name,
				color: catColor(c, name),
				pcts: pts.map((p) => p.shares[c] ?? null),
				latestPct: last.shares[c] ?? 0,
				amt: ((last.shares[c] ?? 0) / 100) * last.total
			}))
			.filter((r) => r.latestPct > 0.05) // 당기 0 인 사족 행 제거(태그 변경 잔여 등)
			.sort((a, b) => b.latestPct - a.latestPct);
		if (!rows.length) return null;
		return { titleKr, titleEn, subKr, subEn, quarters: pts.map((p) => shortPeriod(p.period)), rows, latestPeriod: last.period, latestTotal: last.total, annual: last.quarter === '4분기' };
	}
	const cards = $derived(
		[makeCard(cost, '비용 체질', 'COST CHASSIS', '돈을 뭐에 쓰나', 'where the money goes'), makeCard(segment, '부문별 매출', 'SEGMENT REVENUE', '어디서 버나', 'revenue by segment')].filter((c): c is TblCard => c != null)
	);
</script>

<div class="scrimWrap" role="presentation" onclick={onClose}>
	<div class="scrModal ndModal" role="dialog" aria-modal="true" tabindex="-1" aria-label={T('주석 상세', 'notes detail')} onclick={(e) => e.stopPropagation()}>
		<div class="scrHead">
			<span class="scrTitle">{T('주석', 'NOTES')} · {co.name.kr}</span>
			<span class="ndHeadMeta">{T('정부 XBRL 직독 · 분기=YTD 누적', 'gov XBRL · quarterly YTD')}</span>
			<button class="scrClose" onclick={onClose} aria-label="close">✕</button>
		</div>
		<div class="ndBody">
			{#each cards as c (c.titleEn)}
				<div class="ndHero">
					<div class="ndCardHd">
						<span class="ndCardTitle">{T(c.titleKr, c.titleEn)} <span class="dim">· {T(c.subKr, c.subEn)}</span></span>
						<span class="ndHdRight">{T('당기', 'period')} <b class="mono">{fmtKRW(c.latestTotal)}</b> · {c.latestPeriod}</span>
					</div>
					<div class="ndBar" role="img" aria-label={T(c.titleKr, c.titleEn)}>
						{#each c.rows as r (r.name)}
							<i class="ndBarSeg" style={`width:${r.latestPct}%;background:${r.color}`} title={`${niceName(r.name)} ${r.latestPct.toFixed(1)}%`}>
								{#if r.latestPct >= 7}<span>{niceName(r.name)} {Math.round(r.latestPct)}</span>{/if}
							</i>
						{/each}
					</div>
					<table class="ndTbl">
						<thead>
							<tr>
								<th class="ndTblName">{T('카테고리', 'category')}</th>
								{#each c.quarters as q (q)}<th class="r mono">{q}</th>{/each}
								<th class="r mono ndTblAmt">{T('당기', 'amt')}</th>
							</tr>
						</thead>
						<tbody>
							{#each c.rows as r (r.name)}
								<tr>
									<td class="ndTblName"><i class="ndDot" style={`background:${r.color}`}></i>{niceName(r.name)}</td>
									{#each r.pcts as p, i (i)}<td class={'r mono ' + (i === r.pcts.length - 1 ? 'ndCur' : 'dim')}>{p == null ? '·' : p.toFixed(1)}</td>{/each}
									<td class="r mono ndTblAmt">{fmtKRW(r.amt)}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/each}
			{#if !cards.length}
				<div class="storyEmpty">{T('비용 성격별·부문 주석 미공시 (또는 단일부문). 상세는 뷰어.', 'no cost-by-nature / segment note (or single-segment).')}</div>
			{/if}
		</div>
	</div>
</div>

<style>
	.ndHeadMeta {
		font-family: var(--cond);
		font-size: 9.5px;
		color: var(--dimmer);
		letter-spacing: 0.03em;
	}
	.ndBar {
		display: flex;
		height: 22px;
		border-radius: 3px;
		overflow: hidden;
		gap: 1px;
		background: var(--dl-bg-deep);
		margin: 7px 0 8px;
	}
	.ndBar .ndBarSeg {
		height: 100%;
		min-width: 2px;
		display: flex;
		align-items: center;
		padding: 0 5px;
		overflow: hidden;
		white-space: nowrap;
	}
	.ndBar .ndBarSeg span {
		font-family: var(--cond);
		font-size: 9.5px;
		font-weight: 700;
		color: rgba(0, 0, 0, 0.72);
		text-shadow: 0 0 2px rgba(255, 255, 255, 0.25);
	}
	.ndTbl {
		width: 100%;
		border-collapse: collapse;
		font-family: var(--mono);
		font-size: 11px;
	}
	.ndTbl th {
		font-family: var(--cond);
		font-size: 9px;
		letter-spacing: 0.04em;
		color: var(--dimmer);
		font-weight: 600;
		padding: 2px 7px;
		border-bottom: 1px solid var(--bd);
		text-transform: uppercase;
	}
	.ndTbl td {
		padding: 3px 7px;
		border-bottom: 1px solid color-mix(in srgb, var(--bd) 40%, transparent);
		color: var(--txt);
	}
	.ndTbl tbody tr:hover td {
		background: rgba(91, 155, 240, 0.06);
	}
	.ndTbl .r {
		text-align: right;
	}
	.ndTblName {
		text-align: left;
		white-space: nowrap;
		max-width: 180px;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.ndDot {
		display: inline-block;
		width: 8px;
		height: 8px;
		border-radius: 2px;
		margin-right: 6px;
	}
	.ndTbl .dim {
		color: var(--dim);
	}
	.ndTbl .ndCur {
		color: var(--fg);
		font-weight: 600;
	}
	.ndTblAmt {
		color: var(--fg);
	}
</style>
