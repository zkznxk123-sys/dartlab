<script lang="ts">
	// 주석 대시보드 — 정기보고서 주석에서 파싱한 찐정보를 시각적으로 한눈에. 단일 스크롤·탭 없음(7에이전트 UI/UX 설계).
	// 비용 체질 HERO = *시계열* — 분기마다 다 있는 비용 성격별 구성의 변화(100% 적층 area). 단일점 폴백 가능.
	// 정직: 못 파싱한 건 발췌 폴백·날조 0·종합점수/백분위 0. 색·바·mono 전부 design 토큰. scope=section 동적 도출.
	import type { Company, Lang } from '../lib/types';
	import type { CostNatureSeries, ReportNoteBlock } from '@dartlab/ui-contracts';
	import { fmtKRW } from '../lib/engine';
	import { viewerUrl, marketForCode } from '../../viewer/lib/dartUrl';

	interface Props {
		co: Company;
		lang: Lang;
		notes: ReportNoteBlock[];
		loadCostSeries: () => Promise<CostNatureSeries | null>;
		onClose: () => void;
	}
	let { co, lang, notes, loadCostSeries, onClose }: Props = $props();
	const T = (kr: string, en: string): string => (lang === 'en' ? en : kr);

	$effect(() => {
		const onKey = (e: KeyboardEvent) => {
			if (e.key === 'Escape') onClose();
		};
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});

	// 비용 시계열 — 다이얼로그 열릴 때만 지연 로드(panel 전 기간 본문, 무거움). 단일점/미공시면 series=null → snapshot 폴백.
	let series = $state<CostNatureSeries | null>(null);
	let seriesState = $state<'loading' | 'ready' | 'empty'>('loading');
	$effect(() => {
		let cancelled = false;
		seriesState = 'loading';
		Promise.resolve()
			.then(() => loadCostSeries())
			.then(
				(s) => {
					if (cancelled) return;
					series = s && s.points.length >= 2 ? s : null;
					seriesState = series ? 'ready' : 'empty';
				},
				() => {
					if (cancelled) return;
					seriesState = 'empty';
				}
			);
		return () => {
			cancelled = true;
		};
	});

	const cost = $derived(notes.find((n) => n.topic === 'costNature' && n.composition) ?? null);
	const scopeLabel = (section: string): string => (section.includes('연결') ? T('연결', 'CONS') : T('별도', 'SEP'));
	const costSrc = $derived(cost ? viewerUrl(marketForCode(co.code), cost.rceptNo) : null);

	// 카테고리 색 = design 카테고리 팔레트(6 고유 hue) + 기타=회색. series 카테고리 인덱스 = 색 SSOT(area·범례·랭크 공유).
	const PAL = ['var(--dl-cat-start)', 'var(--dl-cat-operation)', 'var(--dl-cat-engines)', 'var(--dl-cat-runtime)', 'var(--dl-cat-recipes)', 'var(--dl-accent)'];
	const catColor = (i: number, name: string): string => (name === '기타' ? 'var(--dimmer)' : (PAL[i % PAL.length] ?? 'var(--dim)'));
	const normKey = (n: string): string => n.replace(/\s+/g, '');
	// 랭크(최신 원본 명칭) 항목 → series 카테고리 색 매칭(같은 비용이 area·랭크에서 같은 색). 미스=기타로 묻힘.
	const itemColor = (name: string): string => {
		if (!series) return 'var(--dim)';
		const k = normKey(name);
		const i = series.categories.findIndex((c) => normKey(c) === k);
		return i >= 0 ? catColor(i, series.categories[i]!) : 'var(--dimmer)';
	};
	// 긴 항목명 → 범례용 단축
	const shortName = (n: string): string => n.replace(/\s*및\s*/g, '·').replace(/(매입액|사용액|비용|비$)/g, '').trim().slice(0, 7);

	// ── 100% 적층 area (SVG) — x=기간(분기), 세그=카테고리. preserveAspectRatio none 으로 컨테이너 폭 채움. ──
	const W = 640;
	const H = 132;
	const bands = $derived.by(() => {
		if (!series || series.points.length < 2) return [] as { name: string; color: string; points: string; lastPct: number }[];
		const pts = series.points;
		const n = pts.length;
		const ncat = series.categories.length;
		const x = (j: number): number => (j / (n - 1)) * W;
		const y = (cum: number): number => H * (1 - cum / 100);
		// 각 기간 누적(0, c0, c0+c1, ...)
		const cum = pts.map((p) => {
			const a = [0];
			let s = 0;
			for (let c = 0; c < ncat; c++) {
				s += p.shares[c] ?? 0;
				a.push(s);
			}
			return a;
		});
		const out: { name: string; color: string; points: string; lastPct: number }[] = [];
		for (let c = 0; c < ncat; c++) {
			let top = '';
			let bot = '';
			for (let j = 0; j < n; j++) top += `${x(j).toFixed(1)},${y(cum[j]![c + 1]!).toFixed(1)} `;
			for (let j = n - 1; j >= 0; j--) bot += `${x(j).toFixed(1)},${y(cum[j]![c]!).toFixed(1)} `;
			out.push({ name: series.categories[c]!, color: catColor(c, series.categories[c]!), points: (top + bot).trim(), lastPct: pts[n - 1]!.shares[c] ?? 0 });
		}
		return out;
	});
	// 연도 눈금 — 각 4분기(연말) 위치에 2자리 연도 + 가는 세로선
	const yearTicks = $derived.by(() => {
		if (!series || series.points.length < 2) return [] as { x: number; label: string }[];
		const pts = series.points;
		const n = pts.length;
		const ticks: { x: number; label: string }[] = [];
		for (let j = 0; j < n; j++) if (pts[j]!.quarter === '4분기') ticks.push({ x: (j / (n - 1)) * 100, label: "'" + pts[j]!.year.slice(2) });
		return ticks;
	});
	const latestPt = $derived(series ? series.points[series.points.length - 1] : null);
	const firstPt = $derived(series ? series.points[0] : null);

	// 체질 태그 = 최대 세그먼트(30%↑ 명확할 때만). 사실 라벨이지 판정 아님(NEVER-CLAIM).
	const chassis = $derived.by<string | null>(() => {
		const top = cost?.composition?.items.find((i) => !i.name.startsWith('기타'));
		if (!top || top.pct < 30) return null;
		const n = top.name;
		if (/원재료|원·부재료|부재료|재료/.test(n)) return T('원재료형', 'material-heavy');
		if (/외주|가공/.test(n)) return T('외주형', 'outsourcing-heavy');
		if (/급여|인건|종업원|노무|복리/.test(n)) return T('인건비형', 'labor-heavy');
		if (/상품|매입/.test(n)) return T('상품매입형', 'merchandise');
		if (/수수료|용역/.test(n)) return T('수수료형', 'fee-heavy');
		return null;
	});
</script>

<div class="scrimWrap" role="presentation" onclick={onClose}>
	<div class="scrModal ndModal" role="dialog" aria-modal="true" aria-label={T('주석 대시보드', 'notes dashboard')} onclick={(e) => e.stopPropagation()}>
		<div class="scrHead">
			<span class="scrTitle">{T('주석', 'NOTES')} · {co.name.kr}{#if cost} · {cost.period}{/if}</span>
			<button class="scrClose" onclick={onClose} aria-label="close">✕</button>
		</div>
		<div class="ndBody">
			{#if cost?.composition}
				{@const comp = cost.composition}
				<div class="ndHero">
					<div class="ndCardHd">
						<span class="ndCardTitle">{T('비용 체질', 'COST CHASSIS')} <span class="dim">· {T('돈을 뭐에 쓰나 — 분기별 변화', 'where the money goes — over time')}</span></span>
						<span class="ndHdRight">
							<span class="ndScope">[{scopeLabel(cost.section)}]</span>
							{#if costSrc}<a class="factSrc" href={costSrc} target="_blank" rel="noopener" title={T('원문 공시', 'source filing')}>↗{T('원문', '')}</a>{/if}
						</span>
					</div>

					{#if seriesState === 'ready' && series && latestPt}
						<!-- 시계열 100% 적층 area — 분기마다 다 있는 비용 체질의 변화 -->
						<div class="ndAreaWrap">
							<svg class="ndArea" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label={T('비용 성격별 구성 추이', 'cost composition over time')}>
								{#each yearTicks as t (t.x)}
									<line x1={(t.x / 100) * W} y1="0" x2={(t.x / 100) * W} y2={H} class="ndGrid" />
								{/each}
								{#each bands as b (b.name)}
									<polygon points={b.points} fill={b.color} class="ndAreaSeg"><title>{b.name} · {T('최신', 'latest')} {b.lastPct.toFixed(1)}%</title></polygon>
								{/each}
							</svg>
							<div class="ndAxis">
								{#each yearTicks as t (t.x)}<span class="ndTick" style={`left:${t.x}%`}>{t.label}</span>{/each}
							</div>
						</div>
						<div class="ndScale">
							{firstPt?.period}–{latestPt.period} · {series.points.length}{T('개 기간', ' periods')} ·
							{T('당기 비용', 'period cost')} <b class="mono">{fmtKRW(latestPt.total)}</b>
							<span class="dim">({latestPt.quarter === '4분기' ? T('연간', 'annual') : T('분기 누적', 'YTD')})</span>
						</div>
						<!-- 범례 = 카테고리 + 최신 비중% (현재 믹스 한눈에) -->
						<div class="ndLegend">
							{#each bands as b, i (b.name)}
								<span class="ndLeg"><i style={`background:${b.color}`}></i>{b.name === '기타' ? T('기타', 'other') : shortName(b.name)} {b.lastPct.toFixed(0)}</span>
							{/each}
						</div>
					{:else}
						<!-- 폴백: 시계열 없음(단일점/미공시) → 최신 단일 100% 적층바 -->
						{#if seriesState === 'loading'}<div class="ndAreaLoad" role="status" aria-busy="true">{T('추이 불러오는 중 …', 'loading trend …')}</div>{/if}
						<div class="ndTotal">{T('합계', 'total')} <b class="mono">{fmtKRW(comp.total)}</b> = 100% · {comp.items.length}{T('개 항목', ' items')}</div>
						<div class="ndStack">
							{#each comp.items as it, i (it.name)}
								<div class="ndSeg" style={`width:${it.pct}%;background:${itemColor(it.name)}`} title={`${it.name} · ${it.pct.toFixed(1)}% · ${fmtKRW(it.amount)}`}></div>
							{/each}
						</div>
					{/if}

					<!-- 최신 항목 랭크 (금액 desc) — 정밀 디테일(원본 명칭) -->
					<div class="ndRanksHd">{T('최신', 'latest')} {cost.period} · {T('항목별', 'by item')}</div>
					<div class="ndRanks">
						{#each comp.items as it (it.name)}
							<div class="ndRank">
								<span class="ndRankName" title={it.name}>{it.name}</span>
								<span class="ndRankPct mono">{it.pct.toFixed(1)}%</span>
								<span class="ndRankBar"><i style={`width:${Math.max(1, it.pct)}%;background:${itemColor(it.name)}`}></i></span>
								<span class="ndRankAmt mono">{fmtKRW(it.amount)}</span>
							</div>
						{/each}
					</div>
					{#if chassis}<div class="ndChassis">⟨{chassis}⟩ <span class="dim">{T('최대 항목 기준', 'largest item')}</span></div>{/if}
				</div>
			{:else}
				<div class="storyEmpty">{T('이 회사는 비용 성격별 주석 미공시 (또는 비정형 — 파싱 불가). 0 대체 안 함.', 'no cost-by-nature note disclosed (or non-standard).')}</div>
			{/if}
			<div class="ndFoot">{T('정기보고서 주석 파싱 · 당기 컬럼 · 분기 = YTD 누적(절대액 비교는 연간 4분기 기준) · 못 뽑은 값은 원문 발췌(날조 0) · 종합점수·동종백분위 없음 · 숫자 ↗원문', 'parsed from periodic-report notes · current-period column · quarterly = YTD · no composite score / peer percentile')}</div>
		</div>
	</div>
</div>
