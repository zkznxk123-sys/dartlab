<script lang="ts">
	// 한 슬라이드 — 인스타 4:5 에디토리얼. 회사 hero 사진을 배경으로 깔고(전 슬라이드), 헤드라인은
	// AccentText(`[[구절]]`=rose-red). 색감·레이아웃은 기존 SNS 캐러셀(colors.ts/PhotoFrame/InsightCard)
	// 재현 — 새로 짓지 않음. 차트는 $lib/report/render 순수 SVG(klinecharts·백테스트 0), finChart 만 MiniFinChart.
	import type { DartLabRuntime, FinCard } from '@dartlab/ui-contracts';
	import { MiniFinChart } from '@dartlab/ui-surfaces/terminal';
	import { CARD, CARD_SERIES, accentParts, stripDots } from './theme';
	import { cellTone, verdictTone, TXT_COLS, lineGeo, wonLabel } from '$lib/report/render';
	import type { CarouselCard } from './model';

	let { card, rt }: { card: CarouselCard; rt: DartLabRuntime } = $props();

	// 사진 모드 — 편집 카드=monochrome+강한 하단 그라데이션(기존 SNS editorial), 텍스트=풀, 차트=dim.
	const CHART_KINDS = new Set(['kpis', 'line', 'bars', 'share', 'table', 'finChart']);
	const EDITORIAL_KINDS = new Set(['editorial', 'editorialBeat', 'editorialStat']);
	const photoMode = $derived(
		card.kind === 'cover'
			? 'cover'
			: EDITORIAL_KINDS.has(card.kind)
				? 'editorial'
				: CHART_KINDS.has(card.kind)
					? 'dim'
					: 'full'
	);

	let finCards = $state<{ card: FinCard; periods: string[] } | null>(null);
	let finState = $state<'idle' | 'loading' | 'ready' | 'empty'>('idle');

	// 조 단위 카드인데 작은 항목이 0.0조로 반올림돼 표가 무의미해지는 작은 회사 → 전 시리즈 억으로 환산
	// (×1e4·unit='억'). 차트(MiniFinChart unitScale)·표(finTable)가 같은 단위. 큰 회사는 그대로 조.
	function demoteUnit(c: FinCard): FinCard {
		if (c.unit !== '조') return c;
		// 최근 표시구간(말단 6) 기준 — 역사적 고점이 강등을 막지 않게(현재 매출 0.6조여도 과거 2.2조면 조 유지되던 버그).
		const recent = c.series.flatMap((s) => s.data.slice(-6)).filter((v): v is number => typeof v === 'number' && Number.isFinite(v));
		const nz = recent.map((v) => Math.abs(v)).filter((v) => v > 1e-9);
		if (!nz.length) return c;
		const minNz = Math.min(...nz);
		const maxAbs = Math.max(...recent.map((v) => Math.abs(v)));
		// 작은 항목이 0.05조 미만(=0.0 으로 반올림)이고 최근 최대도 1조 미만(=진짜 작은 회사)이면 억으로. 큰 회사는 조 유지.
		if (minNz < 0.05 && maxAbs < 1.0) {
			return {
				...c,
				unit: '억',
				series: c.series.map((s) => ({ ...s, data: s.data.map((v) => (typeof v === 'number' && Number.isFinite(v) ? v * 1e4 : v)) }))
			};
		}
		return c;
	}

	$effect(() => {
		if (card.kind !== 'finChart') return;
		finState = 'loading';
		const code = card.stockCode;
		rt.finance
			.bundle(code)
			.then((b) => {
				// 분기 우선(밀도 — 데이터 작업대 기본 결) → 없으면 연간 폴백. FY 표지화 금지.
				const view = b?.views?.quarter ?? b?.views?.annual ?? Object.values(b?.views ?? {}).find(Boolean);
				const c0 = view?.cards?.[0];
				if (c0 && view) {
					// ★작은 회사 단위 강등 — 조 단위인데 작은 항목(영업익·순익)이 0.0조로 뭉개지면 억으로(차트+표
					// 일괄, 데이터·축 환산만·구조 불변). 매출 0.8조→8,000억, 영업익 0.0조→320억 처럼 읽히게.
					const c = demoteUnit(c0);
					// 캐러셀 팔레트로 재색(엔진 기본 블루/주황/그린 → 로즈 계열).
					const recolored = { ...c, series: c.series.map((s, i) => ({ ...s, color: CARD_SERIES[i % CARD_SERIES.length] })) };
					finCards = { card: recolored, periods: view.periods };
					finState = 'ready';
				} else finState = 'empty';
			})
			.catch(() => (finState = 'empty'));
	});

	// 차트 밑에 같이 둘 수치표 — 시리즈(매출·영업이익·순이익…) × 최근 6기간. 정적 카드는 hover 가 없어
	// 차트만으론 정확값을 못 보니 표를 병치(추세=시각, 정확값=표). 우축은 작은 값(예 영업이익)을 큰 매출
	// 막대 옆에 보이게 한 2차 *같은 단위* 스케일이라 % 가 아님 → 단위 접미 없이 원값 그대로(헤더에 단위 1회).
	const finTable = $derived.by(() => {
		if (!finCards) return null;
		const all = finCards.periods;
		const periods = all.slice(-6);
		const off = all.length - periods.length;
		const fmt = (v: unknown): string => {
			if (typeof v !== 'number' || !Number.isFinite(v)) return '–';
			const a = Math.abs(v);
			if (a >= 100) return Math.round(v).toLocaleString();
			if (a >= 1) return v.toFixed(1);
			return v.toFixed(2); // 1 미만(조 유지된 작은 값 0.02 등)도 0.0 으로 안 뭉개지게 2 자리
		};
		const rows = finCards.card.series.map((s) => ({
			name: s.name,
			values: periods.map((_, i) => fmt(s.data[off + i]))
		}));
		return { unit: finCards.card.unit ?? '', periods, rows };
	});

	// 표 슬라이드에도 그래프 — 각 행(지표)을 한 선으로. 단위는 셀의 '%' 유무로 금액/비율 그룹 분리.
	// ★자릿수 차 처리: 그룹 안에서 행들의 스케일 차가 크면(>8배, 예 매출 vs 영업익) 행별 정규화(작은 항목이
	// 바닥에 안 깔림), 비슷하면(마진·성장) 공유축으로 상대 높이 비교. 정확값은 아래 표가 준다.
	const tableChart = $derived.by(() => {
		if (card.kind !== 'table') return null;
		const periodCols = card.cols.slice(1);
		if (periodCols.length < 2) return null;
		const parse = (s: unknown): number => parseFloat(String(s ?? '').replace(/[^0-9.\-]/g, ''));
		const rows = card.data
			.map((row) => {
				const cells = periodCols.map((c) => String(row[c] ?? ''));
				return {
					name: String(row[card.cols[0]] ?? ''),
					isPct: cells.some((s) => s.includes('%')),
					vals: cells.map((s) => parse(s))
				};
			})
			.filter((r) => r.vals.filter((n) => Number.isFinite(n)).length >= 2);
		if (!rows.length) return null;
		const W = 100;
		const H = 38;
		const rangeOf = (vals: number[]) => {
			const ok = vals.filter((n) => Number.isFinite(n));
			let lo = ok.length ? Math.min(...ok) : 0;
			let hi = ok.length ? Math.max(...ok) : 1;
			if (lo === hi) hi = lo + Math.abs(lo || 1);
			return { lo, hi };
		};
		const toLine = (r: (typeof rows)[number], rng: { lo: number; hi: number }, color: string) => {
			const step = W / (r.vals.length - 1);
			const points = r.vals
				.map((v, i) => (Number.isFinite(v) ? `${(i * step).toFixed(1)},${(H - ((v - rng.lo) / (rng.hi - rng.lo)) * H).toFixed(1)}` : null))
				.filter(Boolean)
				.join(' ');
			return { name: r.name, color, points };
		};
		const groupLines = (group: typeof rows, startCi: number) => {
			if (!group.length) return [] as { name: string; color: string; points: string }[];
			const scales = group.map((r) => Math.max(0, ...r.vals.filter((n) => Number.isFinite(n)).map(Math.abs)));
			const nz = scales.filter((s) => s > 1e-9);
			const spread = nz.length ? Math.max(...nz) / Math.min(...nz) : 1;
			const shared = spread > 8 ? null : rangeOf(group.flatMap((r) => r.vals)); // 차 크면 행별, 비슷하면 공유축
			return group.map((r, i) => toLine(r, shared ?? rangeOf(r.vals), CARD_SERIES[(startCi + i) % CARD_SERIES.length]));
		};
		const absRows = rows.filter((r) => !r.isPct);
		const pctRows = rows.filter((r) => r.isPct);
		const lines = [...groupLines(absRows, 0), ...groupLines(pctRows, absRows.length)].filter((l) => l.points);
		return lines.length ? { lines, W, H } : null;
	});

	const line = $derived(card.kind === 'line' ? lineGeo(card.series, card.markers ?? []) : null);
	const barMax = $derived(card.kind === 'bars' ? Math.max(1, ...card.rows.map((r) => Math.abs(r.value))) : 1);
	// 비중 차트 세그먼트 색 — 캐러셀 팔레트(로즈+그레이)만. 초록/앰버/보라/시안 금지.
	const SHARE_C = ['#ff3f6f', '#ff9ab0', '#d8e2f0', '#9aa7c0', '#6b7794', '#c0cad8', '#7f8aa3'];
	const shareColor = (i: number) => SHARE_C[i % SHARE_C.length];
</script>

{#snippet accent(text: string, cls = '')}
	<span class={cls}>{#each accentParts(stripDots(text)) as p}<span class:hl={p.accent}>{p.text}</span>{/each}</span>
{/snippet}

<article class="slide pm-{photoMode}">
	{#if card.bg}
		<img class="bg" src={card.bg} alt="" loading="lazy" />
		<div class="scrim"></div>
	{/if}

	<div class="content" class:txtSlide={card.kind === 'narrative' || card.kind === 'closing'}>
		{#if card.kind === 'cover'}
			<div class="cover">
				<span class="kicker"><i></i>{card.perspectiveLabel}</span>
				<h2 class="bigName">{card.corpName}</h2>
				<p class="lead">{@render accent(card.conclusion)}</p>
				<p class="mono">{card.stockCode} · {card.dataBasis}</p>
			</div>
		{:else if card.kind === 'editorial' || card.kind === 'editorialBeat'}
			<div class="editorial">
				{#if card.kind === 'editorialBeat' && card.kicker}<span class="eyebrow">{card.kicker}</span>{/if}
				<h2 class="eLine">{@render accent(card.line)}</h2>
				{#if card.sub}<p class="eSub">{stripDots(card.sub)}</p>{/if}
			</div>
		{:else if card.kind === 'editorialStat'}
			<div class="editorial">
				{#if card.kicker}<span class="eyebrow">{card.kicker}</span>{/if}
				<div class="eStat"><span class="eNum">{card.bigNumber}</span>{#if card.unit}<span class="eUnit">{card.unit}</span>{/if}</div>
				{#if card.context}<p class="eSub">{stripDots(card.context)}</p>{/if}
			</div>
		{:else}
			{#if card.heading}
				<header class="sHead">
					<span class="kicker"><i></i>{card.heading}</span>
					{#if card.sub}<p class="sSub">{@render accent(card.sub)}</p>{/if}
				</header>
			{/if}
			{#if card.note}<p class="note">{@render accent(card.note)}</p>{/if}

			{#if card.kind === 'kpis'}
				<div class="kpis">
					{#each card.metrics as m (m.label)}
						<div class="kpi"><span class="kL">{m.label}</span><span class="kV {cellTone(m.value)}">{m.value}</span></div>
					{/each}
				</div>
			{:else if card.kind === 'narrative'}
				<p class="narr">{@render accent(card.text)}</p>
			{:else if card.kind === 'flags'}
				<ul class="flags {card.tone}">{#each card.items as f}<li>{@render accent(f)}</li>{/each}</ul>
			{:else if card.kind === 'line' && line}
				<div class="chart">
					<svg viewBox="0 0 100 30" preserveAspectRatio="none" class="lineChart">
						<polygon points={line.area} class="lArea" />
						<polyline points={line.pts} class="lLine" />
						{#each line.mk as m}<line x1="0" x2="100" y1={m.y} y2={m.y} class="lMark" />{/each}
						<circle cx={line.lastX} cy={line.lastY} r="0.9" class="lDot" />
					</svg>
					{#if card.markers?.length}
						<div class="lMarkers">{#each card.markers as m}<span>{m.label} {card.valueFmt === 'won' ? wonLabel(m.v) : m.v}</span>{/each}</div>
					{/if}
				</div>
			{:else if card.kind === 'bars'}
				<div class="bars">
					{#each card.rows as r (r.label)}
						<div class="bar"><span class="bL">{r.label}</span><span class="bT"><span class="bF" class:neg={r.tone === 'neg'} style="width:{(Math.abs(r.value) / barMax) * 100}%"></span></span><span class="bV">{r.display}</span></div>
					{/each}
				</div>
			{:else if card.kind === 'share'}
				<div class="share">
					{#each card.rows as row (row.year)}
						<div class="shRow"><span class="shY">{row.year}</span><span class="shBar">{#each row.segs as s (s.key)}<span class="shSeg" style="width:{s.pct}%;background:{shareColor(card.legend.findIndex((l) => l.key === s.key))}" title="{s.label} {s.pct}%"></span>{/each}</span></div>
					{/each}
					<div class="shLeg">{#each card.legend as l, i (l.key)}<span class="shLi"><i style="background:{shareColor(i)}"></i>{l.label}</span>{/each}</div>
				</div>
			{:else if card.kind === 'table'}
				<div class="tWrap">
						{#if tableChart}
							<svg viewBox="0 0 {tableChart.W} {tableChart.H}" preserveAspectRatio="none" class="tChart">
								{#each tableChart.lines as ln (ln.name)}<polyline points={ln.points} style="stroke:{ln.color}" />{/each}
							</svg>
							<div class="tLegend">{#each tableChart.lines as ln (ln.name)}<span class="tLi"><i style="background:{ln.color}"></i>{ln.name}</span>{/each}</div>
						{/if}
					<table class="cT">
						<thead><tr>{#each card.cols as c}<th class:num={c !== card.cols[0]}>{c}</th>{/each}</tr></thead>
						<tbody>
							{#each card.data as row}
								<tr>
									{#each card.cols as c, ci}<td class:num={ci !== 0} class="{ci === 0 || TXT_COLS.has(c) ? verdictTone(row[c]) : cellTone(row[c])}">{row[c] ?? '-'}</td>{/each}
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else if card.kind === 'finChart'}
				<div class="finWrap">
					{#if finState === 'ready' && finCards}
						<MiniFinChart card={finCards.card} periods={finCards.periods} h={190} />
						{#if finTable}
							<table class="cT finT">
								<thead>
									<tr><th class="finUnit">{finTable.unit}</th>{#each finTable.periods as p (p)}<th class="num">{p}</th>{/each}</tr>
								</thead>
								<tbody>
									{#each finTable.rows as r (r.name)}
										<tr><td>{r.name}</td>{#each r.values as v, i (i)}<td class="num">{v}</td>{/each}</tr>
									{/each}
								</tbody>
							</table>
						{/if}
					{:else if finState === 'loading'}<p class="muted">재무 추이 불러오는 중…</p>
					{:else}<p class="muted">재무 추이 데이터가 아직 없습니다.</p>{/if}
				</div>
			{:else if card.kind === 'closing'}
				<blockquote class="closing">{@render accent(card.thesis)}</blockquote>
			{:else if card.kind === 'empty'}
				<div class="empty"><p>{card.reason}</p></div>
			{/if}
		{/if}
	</div>
</article>

<style>
	.slide {
		position: relative;
		width: 100%;
		height: 100%;
		background: #050811;
		color: #f1f5f9;
		overflow: hidden;
		text-align: left; /* 좌측 정렬 못박음 — <button>(CoverThumb) 안에서 text-align:center 상속 차단 */
		container-type: inline-size; /* cqw = 슬라이드 폭 기준 반응형 타이포(인스타 1080 기준 스케일) */
		font-family: 'Pretendard Variable', 'Pretendard', system-ui, sans-serif;
	}
	.bg {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		object-fit: cover;
	}
	.pm-cover .bg {
		opacity: 1;
	}
	.pm-full .bg {
		opacity: 0.74;
	}
	.pm-dim .bg {
		opacity: 0.68; /* 차트 슬라이드도 회사 사진이 또렷이(모든 슬라이드에 이미지) — 차트는 아래 패널로 가독 확보 */
	}
	.scrim {
		position: absolute;
		inset: 0;
	}
	/* 배경 밝게 — 하단만 가독용 어둠, 상·중단은 사진 노출(전체 어둠 금지). */
	.pm-cover .scrim {
		background: linear-gradient(180deg, rgba(5, 8, 17, 0.05) 0%, rgba(5, 8, 17, 0.16) 48%, rgba(5, 8, 17, 0.88) 100%);
	}
	.pm-full .scrim {
		background: linear-gradient(180deg, rgba(5, 8, 17, 0.4) 0%, rgba(5, 8, 17, 0.24) 42%, rgba(5, 8, 17, 0.8) 100%);
	}
	.pm-dim .scrim {
		background: linear-gradient(180deg, rgba(5, 8, 17, 0.36) 0%, rgba(5, 8, 17, 0.24) 45%, rgba(5, 8, 17, 0.58) 100%);
	}
	/* 편집 카드 = 기존 SNS editorial: 사진 monochrome(원본 grayscale) + 하단 그라데이션. 원본 brightness
	   0.48 보다 밝게(사용자 "조금만 밝게") → 1.04. 강조색=로즈. */
	.pm-editorial .bg {
		opacity: 0.96;
		filter: grayscale(0.82) contrast(1.04) brightness(1.04);
	}
	.pm-editorial .scrim {
		background: linear-gradient(180deg, rgba(3, 5, 9, 0.22) 0%, rgba(3, 5, 9, 0.32) 44%, rgba(3, 5, 9, 0.86) 100%);
	}
	.pm-editorial .content {
		--hl: var(--dl-accent);
	}
	.content {
		position: relative;
		z-index: 1;
		height: 100%;
		box-sizing: border-box;
		padding: 7% 7.5% 9%;
		display: flex;
		flex-direction: column;
		overflow: hidden; /* 텍스트가 4:5 프레임을 절대 안 넘치게(hook() 단축 + 하드 클립 belt-and-suspenders) */
	}
	/* 다중행 클램프 — 긴 데이터 산문이 카드를 넘치지 않게(인스타 카피는 짧다). 블록 요소만(.narr/.closing
	   는 flex-center 라 .content overflow:hidden + hook() 단축으로 클립). */
	.lead,
	.sSub,
	.note {
		display: -webkit-box;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
	.lead {
		-webkit-line-clamp: 3;
	}
	.sSub {
		-webkit-line-clamp: 2;
	}
	.note {
		-webkit-line-clamp: 2;
	}
	/* kicker (accent dot + label) */
	.kicker {
		display: inline-flex;
		align-items: center;
		gap: 0.6em;
		font-size: clamp(11px, 2.4cqw, 17px);
		color: var(--dl-accent);
		font-weight: 800;
		letter-spacing: 0.12em;
		text-transform: uppercase;
	}
	.kicker i {
		width: 0.55em;
		height: 0.55em;
		border-radius: 999px;
		background: var(--dl-accent);
	}
	.hl {
		color: var(--hl, var(--dl-accent));
	}
	/* editorial (기존 SNS editorial 재현 — 하단 텍스트 블록) */
	.editorial {
		margin-top: auto;
		display: flex;
		flex-direction: column;
	}
	.eyebrow {
		font-size: clamp(11px, 2.4cqw, 18px);
		font-weight: 800;
		letter-spacing: 0.04em;
		color: #fb3f6c;
		margin-bottom: 0.5em;
	}
	.eLine {
		margin: 0;
		font-size: clamp(26px, 7cqw, 64px);
		font-weight: 900;
		line-height: 1.13;
		letter-spacing: -0.01em;
		color: #f4f6fb;
		white-space: pre-line;
		word-break: keep-all;
		display: -webkit-box;
		-webkit-box-orient: vertical;
		-webkit-line-clamp: 4;
		overflow: hidden;
	}
	.eSub {
		margin: 0.7em 0 0;
		font-size: clamp(13px, 3cqw, 26px);
		font-weight: 500;
		line-height: 1.46;
		color: #a4adba;
		white-space: pre-line;
		word-break: keep-all;
		display: -webkit-box;
		-webkit-box-orient: vertical;
		-webkit-line-clamp: 4;
		overflow: hidden;
	}
	.eStat {
		display: flex;
		align-items: baseline;
		gap: 0.2em;
	}
	.eNum {
		font-size: clamp(56px, 18cqw, 200px);
		font-weight: 900;
		line-height: 0.92;
		color: #fb3f6c;
	}
	.eUnit {
		font-size: clamp(20px, 6cqw, 56px);
		font-weight: 800;
		color: #f4f6fb;
		white-space: nowrap;
	}
	/* cover */
	.cover {
		margin-top: auto;
		display: flex;
		flex-direction: column;
		gap: 0.5em;
	}
	.bigName {
		margin: 0.1em 0 0;
		font-size: clamp(32px, 9cqw, 76px);
		font-weight: 900;
		line-height: 1.05;
		letter-spacing: -0.03em;
	}
	.lead {
		margin: 0.2em 0 0;
		font-size: clamp(16px, 4cqw, 32px);
		font-weight: 600;
		line-height: 1.35;
		color: #e7edf5;
	}
	.mono {
		margin: 0.6em 0 0;
		font-family: Menlo, Consolas, monospace;
		font-size: clamp(11px, 2.4cqw, 18px);
		letter-spacing: 0.12em;
		color: #94a3b8;
	}
	/* section head */
	.sHead {
		margin-bottom: 1.2em;
	}
	.sSub {
		margin: 0.4em 0 0;
		font-size: clamp(20px, 5cqw, 44px);
		font-weight: 800;
		line-height: 1.15;
		letter-spacing: -0.02em;
	}
	.note {
		margin: 0 0 1em;
		font-size: clamp(13px, 2.8cqw, 22px);
		line-height: 1.5;
		color: #cdd9e6;
		border-left: 2px solid var(--dl-accent);
		padding-left: 0.7em;
	}
	/* kpis */
	.kpis {
		flex: 1;
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 4%;
		align-content: center;
	}
	.kpi {
		display: flex;
		flex-direction: column;
		gap: 0.3em;
		padding: 6%;
		background: rgba(15, 18, 25, 0.72);
		border: 1px solid #1e2433;
		border-radius: 14px;
	}
	.kL {
		font-size: clamp(12px, 2.6cqw, 20px);
		color: #94a3b8;
	}
	.kV {
		font-size: clamp(22px, 6cqw, 50px);
		font-weight: 800;
		font-variant-numeric: tabular-nums;
	}
	.kV.neg {
		color: #ea4647;
	}
	.kV.pos {
		color: #d8e2f0;
	}
	/* 텍스트 슬라이드(narrative·closing) = 에디토리얼처럼 좌측 정렬 + 하단 고정(중앙정렬 금지). */
	.content.txtSlide {
		justify-content: flex-end;
	}
	/* narrative */
	.narr {
		margin: 0;
		font-size: clamp(22px, 5.6cqw, 52px);
		font-weight: 800;
		line-height: 1.25;
		letter-spacing: -0.02em;
		white-space: pre-line; /* 손글 줄바꿈(\n) 보존 */
		word-break: keep-all;
	}
	/* flags */
	.flags {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 0.7em;
		justify-content: center;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.flags li {
		padding: 0.7em 0.9em;
		border-radius: 12px;
		font-size: clamp(15px, 3.4cqw, 28px);
		font-weight: 600;
		border-left: 4px solid;
		background: rgba(5, 8, 17, 0.5);
	}
	.flags.warning li {
		border-color: #ea4647;
	}
	.flags.opportunity li {
		border-color: #d8e2f0;
	}
	/* charts — 사진 위에서도 가독되게 반투명 패널 + 사진 일부 노출 */
	.chart,
	.bars,
	.share,
	.finWrap,
	.tWrap {
		flex: 1;
		display: flex;
		flex-direction: column;
		justify-content: center;
		gap: 0.7em;
		background: rgba(5, 8, 17, 0.58);
		border: 1px solid rgba(30, 36, 51, 0.7);
		border-radius: 14px;
		padding: 5%;
		box-sizing: border-box;
	}
	/* MiniFinChart 가 패널 폭을 꽉 채우게(.mfc 가 content 폭으로 줄어 작은 정사각으로 뜨던 것 교정).
	   svg 는 width:100%·height:auto(terminal.css) → 폭 = 패널 폭. 차트(h=190) 위 + 수치표 아래 병치. */
	.finWrap {
		justify-content: center; /* 차트+표를 패널 수직 중앙에 */
		gap: 0.5em;
	}
	.finWrap :global(.mfc) {
		width: 100%;
		flex: 0 0 auto;
	}
	/* 차트 밑 수치표 — 시리즈×기간(compact). 시리즈명 열은 auto·좌측, 값은 우측. */
	.finT {
		font-size: clamp(8px, 1.85cqw, 13px);
		flex: 0 0 auto;
	}
	.finT th,
	.finT td {
		padding: 0.3em 0.4em;
	}
	.finT th:first-child,
	.finT td:first-child {
		width: auto;
		white-space: nowrap;
		color: #cdd9e6;
		font-weight: 600;
	}
	.finUnit {
		color: #9aa3ad !important;
		font-weight: 600;
		font-size: 0.9em;
	}
	.lineChart {
		width: 100%;
		height: 40%;
		min-height: 180px;
	}
	.lArea {
		fill: rgba(234, 70, 71, 0.16);
	}
	.lLine {
		fill: none;
		stroke: #ea4647;
		stroke-width: 0.7;
		vector-effect: non-scaling-stroke;
	}
	.lMark {
		stroke: #475569;
		stroke-width: 0.3;
		stroke-dasharray: 1 1;
		vector-effect: non-scaling-stroke;
	}
	.lDot {
		fill: #ea4647;
	}
	.lMarkers {
		display: flex;
		gap: 1.2em;
		font-size: clamp(12px, 2.4cqw, 18px);
		color: #94a3b8;
	}
	.bar {
		display: grid;
		grid-template-columns: 28% 1fr auto;
		gap: 0.7em;
		align-items: center;
		font-size: clamp(13px, 2.8cqw, 22px);
	}
	.bT {
		height: 1.1em;
		background: rgba(15, 18, 25, 0.8);
		border-radius: 4px;
		overflow: hidden;
	}
	.bF {
		display: block;
		height: 100%;
		background: var(--dl-accent);
	}
	.bF.neg {
		background: #ea4647;
	}
	.bV {
		font-variant-numeric: tabular-nums;
		color: #cbd5e1;
	}
	.shRow {
		display: grid;
		grid-template-columns: 18% 1fr;
		gap: 0.7em;
		align-items: center;
	}
	.shY {
		font-size: clamp(12px, 2.4cqw, 18px);
		color: #94a3b8;
	}
	.shBar {
		display: flex;
		height: 1.3em;
		border-radius: 4px;
		overflow: hidden;
	}
	.shSeg {
		height: 100%;
	}
	.shLeg {
		display: flex;
		flex-wrap: wrap;
		gap: 1em;
		font-size: clamp(11px, 2.2cqw, 16px);
		color: #94a3b8;
	}
	.shLi {
		display: inline-flex;
		align-items: center;
		gap: 0.4em;
	}
	.shLi i {
		width: 0.7em;
		height: 0.7em;
		border-radius: 2px;
	}
	.cT {
		width: 100%;
		table-layout: fixed; /* 4:5 프레임에 맞게 — 컬럼이 균등 축소(가로 스크롤·넘침 금지) */
		border-collapse: collapse;
		font-size: clamp(9px, 2.1cqw, 15px);
	}
	.cT th,
	.cT td {
		padding: 0.45em 0.4em;
		text-align: left;
		border-bottom: 1px solid rgba(30, 36, 51, 0.9);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.cT th:first-child,
	.cT td:first-child {
		width: 26%; /* 라벨 열 — 좁혀서 기간 열에 폭을 양보(헤더 '24Q1' 절단 방지) */
		white-space: normal;
		word-break: keep-all;
	}
	.cT th.num,
	.cT td.num {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}
	.cT td.neg {
		color: #ea4647;
	}
	.cT td.pos,
	.cT td.ok {
		color: #d8e2f0;
	}
	.cT td.warn {
		color: #ff9ab0;
	}
	/* 표 위 다중 라인 차트(각 행=한 선) — 행별 정규화(이중축 효과)·로즈 팔레트. 정확값은 아래 표. */
	.tChart {
		width: 100%;
		height: 26%;
		min-height: 92px;
		max-height: 150px;
		flex: 0 0 auto;
	}
	.tChart polyline {
		fill: none;
		stroke-width: 1.4;
		vector-effect: non-scaling-stroke;
	}
	.tLegend {
		display: flex;
		flex-wrap: wrap;
		gap: 0.3em 0.9em;
		font-size: clamp(9px, 2cqw, 14px);
		color: #cdd9e6;
		margin: 0.3em 0 0.5em;
		flex: 0 0 auto;
	}
	.tLi {
		display: inline-flex;
		align-items: center;
		gap: 0.35em;
	}
	.tLi i {
		width: 0.95em;
		height: 0.18em;
		border-radius: 1px;
		display: inline-block;
	}
	.muted {
		color: #64748b;
		font-size: clamp(13px, 2.6cqw, 20px);
	}
	/* closing / empty */
	.closing {
		margin: 0;
		font-size: clamp(20px, 5cqw, 44px);
		font-weight: 700;
		line-height: 1.3;
		white-space: pre-line; /* 손글 줄바꿈 보존 */
		word-break: keep-all;
	}
	.empty {
		flex: 1;
		display: flex;
		align-items: center;
		color: #94a3b8;
		font-size: clamp(14px, 3cqw, 24px);
		text-align: left;
	}
</style>
