<script lang="ts">
	// 주석 상세 — 비용 체질 + 부문별 매출. 둘 다 분기별 구성 테이블(카테고리 × 분기 비중% + 당기 금액).
	// 차트 폐기(운영자 결정 — 적층 area 는 구성이 거의 안 변해 검토거리 0). 데이터 = panel 정부 XBRL 태그
	// 런타임 직독(reportSource.noteSeries). 종합점수·판정 0(NEVER-CLAIM).
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
	// 표시명 정리 — camelCase 공백·짧은 코드 대문자(DX/DS/SDC)·택소노미 꼬리 제거.
	const niceName = (n: string): string => {
		if (n === '기타') return T('기타', 'other');
		const t = n.replace(/\s*및\s*/g, '·').replace(/(매입액|사용액|비용|비$)/g, '').trim();
		if (/^[A-Za-z]{1,4}$/.test(t)) return t.toUpperCase();
		return t.replace(/([a-z])([A-Z])/g, '$1 $2').slice(0, 18);
	};
	const shortPeriod = (p: string): string => p.replace(/^20/, '').replace('Q', 'Q'); // 2026Q1 → 26Q1

	interface TblRow {
		name: string;
		color: string;
		pcts: (number | null)[]; // 분기별 비중% (열 = quarters)
		latestPct: number;
		amt: number; // 당기 금액(원)
	}
	interface TblCard {
		titleKr: string;
		titleEn: string;
		subKr: string;
		subEn: string;
		quarters: string[]; // 열 라벨(최신 우측)
		rows: TblRow[];
		latestPeriod: string;
		latestTotal: number;
		annual: boolean;
	}
	function makeCard(series: CompositionSeries | null, titleKr: string, titleEn: string, subKr: string, subEn: string): TblCard | null {
		if (!series || !series.points.length) return null;
		const pts = series.points;
		const last = pts[pts.length - 1]!;
		const quarters = pts.map((p) => shortPeriod(p.period));
		const rows: TblRow[] = series.categories
			.map((name, c) => ({
				name,
				color: catColor(c, name),
				pcts: pts.map((p) => (p.shares[c] ?? null)),
				latestPct: last.shares[c] ?? 0,
				amt: ((last.shares[c] ?? 0) / 100) * last.total
			}))
			.filter((r) => r.latestPct > 0.05 || r.pcts.some((v) => v != null && v > 0.05))
			.sort((a, b) => b.latestPct - a.latestPct);
		return { titleKr, titleEn, subKr, subEn, quarters, rows, latestPeriod: last.period, latestTotal: last.total, annual: last.quarter === '4분기' };
	}
	const cards = $derived(
		[makeCard(cost, '비용 체질', 'COST CHASSIS', '돈을 뭐에 쓰나', 'where the money goes'), makeCard(segment, '부문별 매출', 'SEGMENT REVENUE', '어디서 버나', 'revenue by segment')].filter((c): c is TblCard => c != null)
	);
</script>

<div class="scrimWrap" role="presentation" onclick={onClose}>
	<div class="scrModal ndModal" role="dialog" aria-modal="true" tabindex="-1" aria-label={T('주석 상세', 'notes detail')} onclick={(e) => e.stopPropagation()}>
		<div class="scrHead">
			<span class="scrTitle">{T('주석', 'NOTES')} · {co.name.kr}</span>
			<button class="scrClose" onclick={onClose} aria-label="close">✕</button>
		</div>
		<div class="ndBody">
			{#each cards as c (c.titleEn)}
				<div class="ndHero">
					<div class="ndCardHd">
						<span class="ndCardTitle">{T(c.titleKr, c.titleEn)} <span class="dim">· {T(c.subKr, c.subEn)}</span></span>
						<span class="ndHdRight">{T('당기', 'period')} <b class="mono">{fmtKRW(c.latestTotal)}</b> · {c.latestPeriod} · {c.annual ? T('연간 누적', 'annual') : T('분기 누적', 'YTD')}</span>
					</div>
					<table class="ndTbl">
						<thead>
							<tr>
								<th class="ndTblName">{T('카테고리', 'category')}</th>
								{#each c.quarters as q (q)}<th class="r mono">{q}</th>{/each}
								<th class="r mono ndTblAmt">{T('당기 금액', 'amount')}</th>
							</tr>
						</thead>
						<tbody>
							{#each c.rows as r (r.name)}
								<tr>
									<td class="ndTblName"><i class="ndDot" style={`background:${r.color}`}></i>{niceName(r.name)}</td>
									{#each r.pcts as p, i (i)}<td class={'r mono ' + (i === r.pcts.length - 1 ? 'ndCur' : 'dim')}>{p == null ? '—' : p.toFixed(1)}</td>{/each}
									<td class="r mono ndTblAmt">{fmtKRW(r.amt)}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/each}
			{#if !cards.length}
				<div class="storyEmpty">{T('비용 성격별·부문 주석 미공시 (또는 단일부문). 상세는 뷰어 참고.', 'no cost-by-nature / segment note (or single-segment).')}</div>
			{/if}
			<div class="ndFoot">{T('정기보고서 주석 — 정부 XBRL 태그 직독 · 최근 분기 · 분기=YTD 누적 · 비중 % · 종합점수·동종백분위 없음 · 상세는 뷰어', 'periodic-report notes — gov XBRL tags · recent quarters · share % · no composite score / peer percentile')}</div>
		</div>
	</div>
</div>

<style>
	.ndTbl {
		width: 100%;
		border-collapse: collapse;
		font-family: var(--mono);
		font-size: 11.5px;
		margin-top: 6px;
	}
	.ndTbl th {
		font-family: var(--cond);
		font-size: 9.5px;
		letter-spacing: 0.04em;
		color: var(--dimmer);
		font-weight: 600;
		padding: 3px 8px;
		border-bottom: 1px solid var(--bd);
		text-transform: uppercase;
	}
	.ndTbl td {
		padding: 4px 8px;
		border-bottom: 1px solid color-mix(in srgb, var(--bd) 45%, transparent);
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
		max-width: 220px;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.ndDot {
		display: inline-block;
		width: 8px;
		height: 8px;
		border-radius: 2px;
		margin-right: 7px;
		vertical-align: baseline;
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
