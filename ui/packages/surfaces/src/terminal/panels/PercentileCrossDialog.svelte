<script lang="ts">
	// 유니버스 교차 백분위 다이얼로그 — 한 회사의 분야별 백분위를 *여러 잣대*(업종 / 소속시장 / 전체상장사)에서 한 좌표로.
	// ★핵심 통찰: "잣대를 바꾸니 순위가 뒤집힌다"(유니버스-민감도). scan-grade(종합평가·판정)와 레인 분리 — 본 화면은 *분포 사실(상위 N%)만, 판정 0*.
	// ★신규 능력 0: 데이터는 engine.percentileIn(code, universe)(EcoNode 전종목 raw 재필터·새 데이터 0). 모달 크롬은 전역 .scrimWrap/.scrModal/.scrHead/.scrClose 재사용.
	// 정직: composite/verdict/매수매도·목표주가 금지(scan-grade 레인). 결손 축은 "—"(0대체 금지). 가격은 펀더와 분리 격자. n<10 띠·곡선 숨김. 유니버스별 출처·cross-sector caveat 강제.
	import type { Company, Lang, Universe, UniversePercentile, PercentileMetric } from '../lib/types';
	import DistCurve from './DistCurve.svelte';

	interface Props {
		co: Company;
		lang: Lang;
		percentileIn: (code: string, universe: Universe) => UniversePercentile | null;
		onClose: () => void;
	}
	let { co, lang, percentileIn, onClose }: Props = $props();

	const UNIS: Universe[] = ['industry', 'market', 'all'];
	const MIN_N = 10; // 표본 부족 임계 — n<10 유니버스는 띠·곡선 숨김(02 정직 가드).
	const SPREAD_FLIP = 30; // 유니버스 백분위 max-min ≥ 이 값이면 "잣대 민감"(뒤집힘) 표식 ⇄.

	// 3 유니버스 산출 — 다이얼로그 열 때 1회(라이브). null(노드 없음)은 제외.
	const data = $derived(UNIS.map((u) => percentileIn(co.code, u)).filter((d): d is UniversePercentile => d != null));
	const uniName = (d: UniversePercentile): string =>
		d.universe === 'all' ? (lang === 'en' ? 'All listed' : '전체상장') : d.label;

	// 정량 행 = 비-gov 지표(거버넌스는 정성 등급으로 분리 — RightStack 패널과 동일). 행 순서 = 지표 가장 많은 유니버스 기준.
	const rowDefs = $derived.by<PercentileMetric[]>(() => {
		if (!data.length) return [];
		const best = data.reduce((a, b) => (b.metrics.length > a.metrics.length ? b : a), data[0]);
		return best.metrics.filter((m) => m.axis !== 'gov');
	});
	const uniMaps = $derived(data.map((d) => new Map(d.metrics.map((m) => [m.en, m] as const))));

	// 정성 등급 행 — union by key(순서 = 첫 유니버스).
	const qualKeys = $derived.by<{ key: string; kr: string; en: string }[]>(() => {
		const seen = new Map<string, { key: string; kr: string; en: string }>();
		for (const d of data) for (const g of d.grades) if (!seen.has(g.key)) seen.set(g.key, { key: g.key, kr: g.kr, en: g.en });
		return [...seen.values()];
	});
	const qualMaps = $derived(data.map((d) => new Map(d.grades.map((g) => [g.key, g] as const))));

	// 드릴다운 — 한 번에 한 지표만(36 곡선 동시 = 허위정밀 격자판 방지).
	let openRow = $state<string | null>(null);
	const toggleRow = (en: string) => (openRow = openRow === en ? null : en);

	// 뒤집힘 표식 — 유니버스 백분위 max-min(분포 사실, 판정 아님). n<10 유니버스는 제외.
	const spreadOf = (en: string): number => {
		const ps = data
			.map((d, i) => (d.n >= MIN_N ? uniMaps[i].get(en)?.p : null))
			.filter((p): p is number => p != null);
		return ps.length >= 2 ? Math.max(...ps) - Math.min(...ps) : 0;
	};

	const pcCol = (p: number): string => (p >= 80 ? 'var(--up)' : p >= 55 ? 'var(--good)' : p >= 35 ? 'var(--warn)' : 'var(--dn)');
	const tcls = (t: string) => (({ up: 'tUp', good: 'tGood', neutral: 'tNeu', warn: 'tWarn', down: 'tDn' }) as Record<string, string>)[t] || 'tNeu';
	const topPct = (p: number): string => (lang === 'en' ? 'top ' + (100 - p + 1) + '%' : '상위 ' + (100 - p + 1) + '%');
	const fmtVal = (m: { unit: string; v: number | null } | undefined): string => {
		if (!m || m.v == null) return '—';
		if (m.unit === '배') return m.v.toFixed(1) + (lang === 'en' ? 'x' : '배');
		if (m.unit === '일') return m.v.toFixed(0) + (lang === 'en' ? 'd' : '일');
		if (m.unit === '') return m.v.toFixed(2);
		if (m.unit === '점') return m.v.toFixed(0);
		return m.v.toFixed(1) + (m.unit === '%' ? '%' : '');
	};
	// 값(절대 사실, 유니버스 무관) — 먼저 발견되는 유니버스에서.
	const valOf = (en: string): string => {
		for (const map of uniMaps) { const m = map.get(en); if (m) return fmtVal(m); }
		return '—';
	};
	const fmtX = (v: number | null): string => (v == null ? '—' : v.toFixed(v < 10 ? 2 : 1) + (lang === 'en' ? 'x' : '배'));

	$effect(() => {
		const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});
</script>

<div class="scrimWrap" role="presentation" onclick={onClose}>
	<div
		class="scrModal pcxModal"
		role="dialog"
		aria-modal="true"
		aria-label={lang === 'en' ? 'Cross-universe percentile' : '유니버스 교차 백분위'}
		onclick={(e) => e.stopPropagation()}
		style={`--ucols:${data.length}`}
	>
		<div class="scrHead">
			<span class="scrTitle">{lang === 'en' ? 'CROSS-UNIVERSE PERCENTILE' : '유니버스 교차 백분위'}</span>
			<span class="pcxWho">{co.name.kr}<i>{co.marketLabel} · {co.sector.kr}</i></span>
			<span class="pcxLens">{lang === 'en' ? 'distribution facts · top N% (not a verdict)' : '분포 사실 · 상위 N% (판정 아님)'}</span>
			<button class="scrClose" onclick={onClose} aria-label="close">✕</button>
		</div>

		<div class="pcxBody">
			{#if !data.length}
				<div class="pcxNone">{lang === 'en' ? 'No ecosystem node for this company.' : '이 회사의 ecosystem 노드가 없습니다.'}</div>
			{:else}
				<!-- 정량 격자: 행=지표 × 열=유니버스 백분위 띠. 업종(앵커) 좌측 강조, 시장/전체는 넓은 잣대. -->
				<div class="pcxTable">
					<div class="pcxHead">
						<span class="pcxNameH">{lang === 'en' ? 'metric' : '지표'}</span>
						{#each data as d, i (d.universe)}
							<span class={'pcxColH' + (d.universe === 'industry' ? ' anchor' : '')}>{uniName(d)}<i>n={d.n}</i></span>
						{/each}
						<span class="pcxValH">{lang === 'en' ? 'value' : '값'}</span>
					</div>

					{#each rowDefs as row (row.en)}
						{@const spread = spreadOf(row.en)}
						{@const flip = spread >= SPREAD_FLIP}
						<button class={'pcxRow' + (openRow === row.en ? ' open' : '')} onclick={() => toggleRow(row.en)} aria-expanded={openRow === row.en}>
							<span class="pcxName">{#if flip}<span class="pcxFlip" title={lang === 'en' ? 'lens-sensitive (rank flips by universe)' : '잣대 민감 — 유니버스 따라 순위 뒤집힘'}>⇄</span>{/if}{lang === 'en' ? row.en : row.kr}</span>
							{#each data as d, i (d.universe)}
								{@const m = uniMaps[i].get(row.en)}
								<span class={'pcxCell' + (d.universe === 'industry' ? ' anchor' : '')}>
									{#if d.n < MIN_N}
										<span class="pcxThin">{lang === 'en' ? 'n<10' : '표본부족'}</span>
									{:else if m && m.p != null}
										<span class="pcxTrack"><span class="pcxFill" style={`width:${m.p}%;background:${pcCol(m.p)}`}></span></span>
										<span class="pcxP" style={`color:${pcCol(m.p)}`}>{topPct(m.p)}</span>
									{:else}
										<span class="pcxDash">—</span>
									{/if}
								</span>
							{/each}
							<span class="pcxVal mono">{valOf(row.en)}</span>
						</button>

						{#if openRow === row.en}
							<!-- 드릴다운: 유니버스별 분포곡선 세로 스택(같은 회사값, 곡선마다 마크 위치가 달라 = 뒤집힘을 분포로 재확인). -->
							<div class="pcxDrill">
								{#each data as d, i (d.universe)}
									{@const m = uniMaps[i].get(row.en)}
									<div class="pcxDc">
										<span class="pcxDcL">{uniName(d)} <i>n={d.n}</i></span>
										{#if d.n >= MIN_N && m && m.band && m.p != null && m.v != null}
											<div class="pcxDcCurve"><DistCurve band={m.band} value={m.v} p={m.p} unit={m.unit} {lang} w={280} h={28} /></div>
											<span class="pcxDcP mono" style={`color:${pcCol(m.p)}`}>{topPct(m.p)}</span>
										{:else}
											<span class="pcxDcEmpty">{lang === 'en' ? 'distribution hidden (n<10)' : '분포 숨김 (n<10)'}</span>
										{/if}
									</div>
								{/each}
							</div>
						{/if}
					{/each}
				</div>

				<!-- 정성 등급 — 백분위 아님(띠 없음). 등급 칩 + 이 유니버스 내 동급 비중. 정량과 dashed 분리. -->
				{#if qualKeys.length}
					<div class="pcxQualHead">{lang === 'en' ? 'qualitative — grade & same-grade share (not a percentile)' : '정성 — 등급 · 동급 비중 (백분위 아님)'}</div>
					<div class="pcxTable">
						{#each qualKeys as q (q.key)}
							<div class="pcxRow qual">
								<span class="pcxName">{lang === 'en' ? q.en : q.kr}</span>
								{#each data as d, i (d.universe)}
									{@const g = qualMaps[i].get(q.key)}
									<span class={'pcxCell' + (d.universe === 'industry' ? ' anchor' : '')}>
										{#if g}
											<span class={'pcxChip ' + tcls(g.tone)}>{g.v}</span>
											{#if g.sameShare != null}<span class="pcxShare">{lang === 'en' ? g.sameShare + '%' : '동급 ' + g.sameShare + '%'}</span>{/if}
										{:else}
											<span class="pcxDash">—</span>
										{/if}
									</span>
								{/each}
								<span class="pcxVal"></span>
							</div>
						{/each}
					</div>
				{/if}

				<!-- 가격(PER/PBR) — 펀더와 *분리*. 시장 시세 기반(펀더멘털 아님). 톤색·우열 프레이밍 없음(02 KILL#2). -->
				{#if data.some((d) => d.price.per.v != null || d.price.pbr.v != null)}
					<div class="pcxPriceHead">{lang === 'en' ? 'price (market quote — not fundamentals · lower = cheaper, not a verdict)' : '가격 지표 — 시장 시세 기반 (펀더멘털 아님 · 낮을수록 저평가, 판정 아님)'} · {co.price.asOf}</div>
					<div class="pcxTable">
						{#each [{ k: 'per', kr: 'PER', en: 'PER' }, { k: 'pbr', kr: 'PBR', en: 'PBR' }] as pr (pr.k)}
							<div class="pcxRow price">
								<span class="pcxName">{lang === 'en' ? pr.en : pr.kr}</span>
								{#each data as d, i (d.universe)}
									{@const ps = pr.k === 'per' ? d.price.per : d.price.pbr}
									<span class={'pcxCell' + (d.universe === 'industry' ? ' anchor' : '')}>
										{#if d.n >= MIN_N && ps.v != null && ps.p != null && ps.n >= MIN_N}
											<span class="pcxTrack"><span class="pcxFill priceFill" style={`width:${ps.p}%`}></span></span>
											<span class="pcxP dim">{lang === 'en' ? ps.p + '%ile' : '분포 ' + ps.p + '%'}</span>
										{:else}
											<span class="pcxDash">—</span>
										{/if}
									</span>
								{/each}
								<span class="pcxVal mono">{fmtX(pr.k === 'per' ? data[0]?.price.per.v ?? null : data[0]?.price.pbr.v ?? null)}</span>
							</div>
						{/each}
					</div>
				{/if}

				<!-- 정직 라벨 — 출처·cross-sector·결손·BLOCKED. provenance 없는 셀 = 회귀(02 가드). -->
				<div class="pcxNotes">
					<div>※ {lang === 'en'
						? 'Industry band: industryStats · KSIC sector · equal-weight · listed primary (≠ KRX cap-weighted index). Market/All: live 5-quantile from EcoNode population.'
						: '업종 분포: industryStats · KSIC 섹터 · 동일가중 · 상장 primary (≠ KRX 시총가중 업종지수). 시장·전체: EcoNode 모집단 라이브 5분위.'}</div>
					<div>※ {lang === 'en'
						? 'All-listed mixes sectors (financials · manufacturing) → margin/ROE percentile is sector-dependent (context, not a headline). Industry is the anchor.'
						: '전체상장 = 금융·제조 혼재 → 마진·ROE 백분위는 섹터 의존(맥락용 잣대, 헤드라인 아님). 업종이 기본 앵커.'}</div>
					<div>※ {lang === 'en'
						? '"—" = absent from filings (not 0). "n<10" = sample too small (band/curve hidden). This is distribution facts only — not a buy/sell signal or composite verdict.'
						: '"—" = 공시에 없음(0 아님). "표본부족" = n<10(띠·곡선 숨김). 분포 사실만 — 매수/매도·종합판정 아님.'}</div>
					<div>※ {lang === 'en'
						? 'Index membership (KOSPI200 · KOSDAQ150) is BLOCKED — constituent data absent. No "top-N by cap ≈ index" approximation (would be fabrication).'
						: '소속지수(KOSPI200·코스닥150) = BLOCKED — 구성종목 데이터 부재. "시총 상위 N = 지수 근사" 우회 안 함(위조 금지).'}</div>
				</div>
			{/if}
		</div>
	</div>
</div>

<style>
	.pcxModal {
		width: min(940px, 96vw);
	}
	.pcxWho {
		font-size: 12px;
		font-weight: 700;
		color: var(--dl-ink, #c8cfdb);
	}
	.pcxWho i {
		font-style: normal;
		font-weight: 400;
		margin-left: 7px;
		font-size: 10.5px;
		color: var(--dl-ink-dim, #5b6473);
	}
	.pcxLens {
		font-size: 10px;
		color: var(--dl-ink-dim, #5b6473);
		font-style: italic;
	}
	.pcxBody {
		flex: 1 1 auto;
		min-height: 0;
		overflow-y: auto;
		padding: 12px 14px 16px;
	}
	.pcxNone {
		padding: 40px 0;
		text-align: center;
		font-size: 12px;
		color: var(--dl-ink-dim, #5b6473);
	}
	/* 행×열 격자 — head·row 동일 grid template (지표명 | 유니버스 N칸 | 값). */
	.pcxHead,
	.pcxRow {
		display: grid;
		grid-template-columns: minmax(78px, 0.85fr) repeat(var(--ucols, 3), minmax(0, 1fr)) 62px;
		gap: 10px;
		align-items: center;
	}
	.pcxHead {
		padding: 0 6px 5px;
		border-bottom: 1px solid var(--dl-line, #1b2130);
		margin-bottom: 2px;
	}
	.pcxNameH,
	.pcxColH,
	.pcxValH {
		font-size: 9.5px;
		font-weight: 700;
		letter-spacing: 0.03em;
		color: var(--dl-ink-dim, #5b6473);
		text-transform: uppercase;
	}
	.pcxColH {
		display: flex;
		flex-direction: column;
		line-height: 1.25;
	}
	.pcxColH.anchor {
		color: var(--amber, #fb923c);
	}
	.pcxColH i {
		font-style: normal;
		font-weight: 400;
		font-size: 9px;
		font-variant-numeric: tabular-nums;
		color: var(--dl-ink-dim, #5b6473);
	}
	.pcxValH {
		text-align: right;
	}
	/* 행 = 클릭 가능(드릴다운 토글). 버튼 리셋. */
	.pcxRow {
		width: 100%;
		background: none;
		border: 0;
		border-bottom: 1px solid var(--dl-line, #1b2130);
		padding: 6px 6px;
		cursor: pointer;
		text-align: left;
		font: inherit;
		color: inherit;
	}
	.pcxRow.qual,
	.pcxRow.price {
		cursor: default;
	}
	.pcxRow:hover:not(.qual):not(.price) {
		background: rgba(255, 255, 255, 0.022);
	}
	.pcxRow.open {
		background: rgba(255, 255, 255, 0.03);
	}
	.pcxName {
		font-size: 11px;
		font-weight: 600;
		color: var(--dl-ink, #c8cfdb);
		display: flex;
		align-items: center;
		gap: 3px;
		min-width: 0;
	}
	.pcxFlip {
		color: var(--dl-ink-dim, #8a93a3);
		font-size: 11px;
		font-weight: 700;
		flex: 0 0 auto;
	}
	.pcxCell {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
	}
	.pcxTrack {
		height: 8px;
		width: 100%;
		background: var(--dl-bg-overlay, rgba(255, 255, 255, 0.05));
		border-radius: 2px;
		overflow: hidden;
	}
	.pcxFill {
		display: block;
		height: 100%;
		border-radius: 2px;
	}
	.pcxFill.priceFill {
		background: rgba(139, 148, 158, 0.55); /* 가격 = 중립 회색(우열 프레이밍 금지) */
	}
	.pcxP {
		font-size: 9px;
		font-family: var(--dl-font-mono, ui-monospace, monospace);
		font-variant-numeric: tabular-nums;
		font-weight: 700;
	}
	.pcxP.dim {
		color: var(--dl-ink-dim, #5b6473) !important;
		font-weight: 400;
	}
	.pcxThin,
	.pcxDash {
		font-size: 9.5px;
		color: var(--dl-ink-dim, #5b6473);
		font-style: italic;
	}
	.pcxVal {
		font-size: 10px;
		text-align: right;
		font-variant-numeric: tabular-nums;
		color: var(--dl-ink, #c8cfdb);
		white-space: nowrap;
	}
	/* 드릴다운 — 유니버스별 분포곡선 세로 스택 */
	.pcxDrill {
		display: flex;
		flex-direction: column;
		gap: 6px;
		padding: 8px 6px 10px;
		border-bottom: 1px solid var(--dl-line, #1b2130);
		background: rgba(255, 255, 255, 0.012);
	}
	.pcxDc {
		display: grid;
		grid-template-columns: 96px 1fr 64px;
		align-items: center;
		gap: 8px;
	}
	.pcxDcL {
		font-size: 10px;
		color: var(--dl-ink-dim, #5b6473);
	}
	.pcxDcL i {
		font-style: normal;
		font-variant-numeric: tabular-nums;
	}
	.pcxDcCurve {
		min-width: 0;
	}
	.pcxDcP {
		font-size: 9.5px;
		text-align: right;
		font-variant-numeric: tabular-nums;
		font-weight: 700;
	}
	.pcxDcEmpty {
		grid-column: 2 / 4;
		font-size: 9.5px;
		font-style: italic;
		color: var(--dl-ink-dim, #5b6473);
	}
	/* 정성 칩 + 동급비중 */
	.pcxQualHead,
	.pcxPriceHead {
		margin-top: 14px;
		padding: 6px 6px 4px;
		font-size: 9.5px;
		font-weight: 700;
		letter-spacing: 0.02em;
		color: var(--dl-ink-dim, #5b6473);
		border-top: 1px dashed var(--dl-line, #1b2130);
	}
	.pcxChip {
		font-size: 10.5px;
		font-weight: 700;
		padding: 1px 7px;
		border-radius: 9px;
		border: 1px solid var(--dl-line, #1b2130);
		background: rgba(255, 255, 255, 0.03);
		align-self: flex-start;
		white-space: nowrap;
	}
	.pcxShare {
		font-size: 9px;
		color: var(--dl-ink-dim, #5b6473);
		font-variant-numeric: tabular-nums;
	}
	.pcxNotes {
		margin-top: 12px;
		padding-top: 8px;
		border-top: 1px solid var(--dl-line, #1b2130);
		display: flex;
		flex-direction: column;
		gap: 3px;
	}
	.pcxNotes div {
		font-size: 9px;
		line-height: 1.45;
		color: var(--dl-ink-dim, #5b6473);
	}
	/* 톤 색 — 터미널 토큰(신규 색 0) */
	.tUp {
		color: var(--up);
	}
	.tGood {
		color: var(--good);
	}
	.tNeu {
		color: var(--dl-ink-dim, #8a93a3);
	}
	.tWarn {
		color: var(--warn);
	}
	.tDn {
		color: var(--dn);
	}
</style>
