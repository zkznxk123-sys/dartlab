<script lang="ts">
	// 주석 상세 — 비용 체질 + 부문별 매출, 둘 다 분기 시계열 100% 적층 area. 단일 스크롤.
	// 데이터 = panel 정부 XBRL 태그 런타임 직독(reportSource.noteSeries). 빠른 글랜스 우선·상세는 viewer.
	// 색·바·mono 전부 design 토큰. 종합점수·판정 0(NEVER-CLAIM).
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

	// 카테고리 색 = design 카테고리 팔레트(6 고유 hue) + 기타=회색.
	const PAL = ['var(--dl-cat-start)', 'var(--dl-cat-operation)', 'var(--dl-cat-engines)', 'var(--dl-cat-runtime)', 'var(--dl-cat-recipes)', 'var(--dl-accent)', 'var(--up)', 'var(--warn)'];
	const catColor = (i: number, name: string): string => (name === '기타' ? 'var(--dimmer)' : (PAL[i % PAL.length] ?? 'var(--dim)'));
	const shortName = (n: string): string => n.replace(/\s*및\s*/g, '·').replace(/(매입액|사용액|비용|비$)/g, '').replace(/([a-z])([A-Z])/g, '$1 $2').trim().slice(0, 12);

	const W = 640;
	const H = 120;
	// CompositionSeries → 적층 area 밴드(폴리곤) + 연도눈금 + 최신점.
	function viz(series: CompositionSeries) {
		const pts = series.points;
		const n = pts.length;
		const ncat = series.categories.length;
		const x = (j: number): number => (n <= 1 ? W / 2 : (j / (n - 1)) * W);
		const y = (cum: number): number => H * (1 - cum / 100);
		const cum = pts.map((p) => {
			const a = [0];
			let s = 0;
			for (let c = 0; c < ncat; c++) {
				s += p.shares[c] ?? 0;
				a.push(s);
			}
			return a;
		});
		const bands = series.categories.map((name, c) => {
			let top = '';
			let bot = '';
			for (let j = 0; j < n; j++) top += `${x(j).toFixed(1)},${y(cum[j]![c + 1]!).toFixed(1)} `;
			for (let j = n - 1; j >= 0; j--) bot += `${x(j).toFixed(1)},${y(cum[j]![c]!).toFixed(1)} `;
			return { name, color: catColor(c, name), points: (top + bot).trim() };
		});
		const ticks: { x: number; label: string }[] = [];
		for (let j = 0; j < n; j++) if (pts[j]!.quarter === '4분기' || j === 0 || j === n - 1) ticks.push({ x: (n <= 1 ? 50 : (j / (n - 1)) * 100), label: pts[j]!.period.slice(2) });
		const latest = pts[n - 1]!;
		// 최신 랭크 — 카테고리별 최신 비중·절대(share/100*total)
		const rank = series.categories
			.map((name, c) => ({ name, color: catColor(c, name), pct: latest.shares[c] ?? 0, value: ((latest.shares[c] ?? 0) / 100) * latest.total }))
			.filter((r) => r.pct > 0.05)
			.sort((a, b) => b.pct - a.pct);
		return { bands, ticks, latest, rank, single: n <= 1 };
	}
	const costViz = $derived(cost ? viz(cost) : null);
	const segViz = $derived(segment ? viz(segment) : null);
</script>

{#snippet card(v: ReturnType<typeof viz>, titleKr: string, titleEn: string, subKr: string, subEn: string)}
	<div class="ndHero">
		<div class="ndCardHd">
			<span class="ndCardTitle">{T(titleKr, titleEn)} <span class="dim">· {T(subKr, subEn)}</span></span>
			<span class="ndHdRight"><span class="ndScope">{v.latest.period}{#if !v.single} · {v.bands[0] ? '' : ''}{/if}</span></span>
		</div>
		{#if !v.single}
			<div class="ndAreaWrap">
				<svg class="ndArea" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label={T(titleKr, titleEn)}>
					{#each v.ticks as t (t.x)}<line x1={(t.x / 100) * W} y1="0" x2={(t.x / 100) * W} y2={H} class="ndGrid" />{/each}
					{#each v.bands as b (b.name)}<polygon points={b.points} fill={b.color} class="ndAreaSeg"><title>{shortName(b.name)}</title></polygon>{/each}
				</svg>
				<div class="ndAxis">{#each v.ticks as t (t.x)}<span class="ndTick" style={`left:${t.x}%`}>{t.label}</span>{/each}</div>
			</div>
		{/if}
		<div class="ndScale">{T('당기', 'period')} <b class="mono">{fmtKRW(v.latest.total)}</b> · {v.latest.quarter === '4분기' ? T('연간 누적', 'annual') : T('분기 누적', 'YTD')}{#if !v.single} · {v.bands.length}{T('개 카테고리', ' cats')}{/if}</div>
		<div class="ndLegend">
			{#each v.rank as r (r.name)}<span class="ndLeg"><i style={`background:${r.color}`}></i>{r.name === '기타' ? T('기타', 'other') : shortName(r.name)} {r.pct.toFixed(0)}</span>{/each}
		</div>
		<div class="ndRanks">
			{#each v.rank as r (r.name)}
				<div class="ndRank">
					<span class="ndRankName" title={r.name}>{r.name === '기타' ? T('기타', 'other') : shortName(r.name)}</span>
					<span class="ndRankPct mono">{r.pct.toFixed(1)}%</span>
					<span class="ndRankBar"><i style={`width:${Math.max(1, r.pct)}%;background:${r.color}`}></i></span>
					<span class="ndRankAmt mono">{fmtKRW(r.value)}</span>
				</div>
			{/each}
		</div>
	</div>
{/snippet}

<div class="scrimWrap" role="presentation" onclick={onClose}>
	<div class="scrModal ndModal" role="dialog" aria-modal="true" aria-label={T('주석 상세', 'notes detail')} onclick={(e) => e.stopPropagation()}>
		<div class="scrHead">
			<span class="scrTitle">{T('주석', 'NOTES')} · {co.name.kr}</span>
			<button class="scrClose" onclick={onClose} aria-label="close">✕</button>
		</div>
		<div class="ndBody">
			{#if costViz}{@render card(costViz, '비용 체질', 'COST CHASSIS', '돈을 뭐에 쓰나 — 분기별', 'where the money goes')}{/if}
			{#if segViz}{@render card(segViz, '부문별 매출', 'SEGMENT REVENUE', '어디서 버나 — 분기별', 'revenue by segment')}{/if}
			{#if !costViz && !segViz}
				<div class="storyEmpty">{T('비용 성격별·부문 주석 미공시 (또는 단일부문). 상세는 뷰어 참고.', 'no cost-by-nature / segment note (or single-segment).')}</div>
			{/if}
			<div class="ndFoot">{T('정기보고서 주석 — 정부 XBRL 태그 직독 · 최근 분기 · 분기=YTD 누적 · 종합점수·동종백분위 없음 · 상세는 뷰어', 'periodic-report notes — gov XBRL tags · recent quarters · no composite score / peer percentile')}</div>
		</div>
	</div>
</div>
