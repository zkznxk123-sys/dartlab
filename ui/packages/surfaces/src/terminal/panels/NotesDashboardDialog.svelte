<script lang="ts">
	// 주석 상세 — 비용 체질 + 부문별 매출, 둘 다 분기 시계열 100% 적층 area + 최신 랭크. 단일 스크롤.
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
	// 표시명 정리 — camelCase 공백·짧은 코드 대문자(DX/DS/SDC)·택소노미 꼬리 제거.
	const niceName = (n: string): string => {
		const t = n.replace(/\s*및\s*/g, '·').replace(/(매입액|사용액|비용|비$)/g, '').trim();
		if (/^[A-Za-z]{1,4}$/.test(t)) return t.toUpperCase();
		return t.replace(/([a-z])([A-Z])/g, '$1 $2').slice(0, 16);
	};

	const W = 640;
	const H = 116;
	interface VizCard {
		titleKr: string;
		titleEn: string;
		subKr: string;
		subEn: string;
		series: CompositionSeries;
		single: boolean;
		bands: { name: string; color: string; points: string }[];
		ticks: { x: number; label: string }[];
		latestPeriod: string;
		latestTotal: number;
		annual: boolean;
		rank: { name: string; color: string; pct: number; value: number }[];
	}
	function makeCard(series: CompositionSeries | null, titleKr: string, titleEn: string, subKr: string, subEn: string): VizCard | null {
		if (!series || !series.points.length) return null;
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
		for (let j = 0; j < n; j++) if (pts[j]!.quarter === '4분기' || j === 0 || j === n - 1) ticks.push({ x: n <= 1 ? 50 : (j / (n - 1)) * 100, label: pts[j]!.period.slice(2) });
		const latest = pts[n - 1]!;
		const rank = series.categories
			.map((name, c) => ({ name, color: catColor(c, name), pct: latest.shares[c] ?? 0, value: ((latest.shares[c] ?? 0) / 100) * latest.total }))
			.filter((r) => r.pct > 0.05)
			.sort((a, b) => b.pct - a.pct);
		return { titleKr, titleEn, subKr, subEn, series, single: n <= 1, bands, ticks, latestPeriod: latest.period, latestTotal: latest.total, annual: latest.quarter === '4분기', rank };
	}
	const cards = $derived(
		[makeCard(cost, '비용 체질', 'COST CHASSIS', '돈을 뭐에 쓰나 — 분기별', 'where the money goes'), makeCard(segment, '부문별 매출', 'SEGMENT REVENUE', '어디서 버나 — 분기별', 'revenue by segment')].filter((c): c is VizCard => c != null)
	);
</script>

<div class="scrimWrap" role="presentation" onclick={onClose}>
	<div class="scrModal ndModal" role="dialog" aria-modal="true" aria-label={T('주석 상세', 'notes detail')} onclick={(e) => e.stopPropagation()}>
		<div class="scrHead">
			<span class="scrTitle">{T('주석', 'NOTES')} · {co.name.kr}</span>
			<button class="scrClose" onclick={onClose} aria-label="close">✕</button>
		</div>
		<div class="ndBody">
			{#each cards as c (c.titleEn)}
				<div class="ndHero">
					<div class="ndCardHd">
						<span class="ndCardTitle">{T(c.titleKr, c.titleEn)} <span class="dim">· {T(c.subKr, c.subEn)}</span></span>
						<span class="ndHdRight"><span class="ndScope">{c.latestPeriod}</span></span>
					</div>
					{#if !c.single}
						<div class="ndAreaWrap">
							<svg class="ndArea" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label={T(c.titleKr, c.titleEn)}>
								{#each c.ticks as t (t.x)}<line x1={(t.x / 100) * W} y1="0" x2={(t.x / 100) * W} y2={H} class="ndGrid" />{/each}
								{#each c.bands as b (b.name)}<polygon points={b.points} fill={b.color} class="ndAreaSeg"><title>{niceName(b.name)}</title></polygon>{/each}
							</svg>
							<div class="ndAxis">{#each c.ticks as t (t.x)}<span class="ndTick" style={`left:${t.x}%`}>{t.label}</span>{/each}</div>
						</div>
					{/if}
					<div class="ndScale">{T('당기', 'period')} <b class="mono">{fmtKRW(c.latestTotal)}</b> · {c.annual ? T('연간 누적', 'annual') : T('분기 누적', 'YTD')}</div>
					<div class="ndLegend">
						{#each c.rank as r (r.name)}<span class="ndLeg"><i style={`background:${r.color}`}></i>{r.name === '기타' ? T('기타', 'other') : niceName(r.name)} {r.pct.toFixed(0)}</span>{/each}
					</div>
					<div class="ndRanks">
						{#each c.rank as r (r.name)}
							<div class="ndRank">
								<span class="ndRankName" title={r.name}>{r.name === '기타' ? T('기타', 'other') : niceName(r.name)}</span>
								<span class="ndRankPct mono">{r.pct.toFixed(1)}%</span>
								<span class="ndRankBar"><i style={`width:${Math.max(1, r.pct)}%;background:${r.color}`}></i></span>
								<span class="ndRankAmt mono">{fmtKRW(r.value)}</span>
							</div>
						{/each}
					</div>
				</div>
			{/each}
			{#if !cards.length}
				<div class="storyEmpty">{T('비용 성격별·부문 주석 미공시 (또는 단일부문). 상세는 뷰어 참고.', 'no cost-by-nature / segment note (or single-segment).')}</div>
			{/if}
			<div class="ndFoot">{T('정기보고서 주석 — 정부 XBRL 태그 직독 · 최근 분기 · 분기=YTD 누적 · 종합점수·동종백분위 없음 · 상세는 뷰어', 'periodic-report notes — gov XBRL tags · recent quarters · no composite score / peer percentile')}</div>
		</div>
	</div>
</div>
