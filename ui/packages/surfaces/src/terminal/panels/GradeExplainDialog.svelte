<script lang="ts">
	// 스캔 등급 설명 다이얼로그 — "왜 이 등급인가". 좌 스파이더 / 우 근거 / 아래 기준.
	// ★신규 능력 0: 데이터(co.radar·co.verdict·co.analysis.tracks·co.credit·co.grades)는 전부 엔진 산물(공동배선
	//   = 퍼블릭·로컬 동일). 모달 크롬은 전역 .scrimWrap/.scrModal/.scrHead/.scrClose 재사용. 레이더는 map RadarChart 재사용.
	// 정직: 매수/매도 신호·목표주가·인과 금지. 결손 축은 채우지 않고 뺀다(0대체 금지). 등급 = 판정(근거+기준 동반).
	import type { Company, Lang } from '../lib/types';
	import { GRADE_SCALE } from '../lib/engine';
	import { GRADE_GUIDE } from '../lib/gradeGuide';
	import { txc } from '../ui/helpers';
	import RadarChart from '../../map/components/RadarChart.svelte';
	import DistCurve from './DistCurve.svelte';

	interface Props {
		co: Company;
		lang: Lang;
		onClose: () => void;
	}
	let { co, lang, onClose }: Props = $props();

	// 단위 인식 숫자 포맷 — % / 배(times) / 일(days) / 무단위(발생액비율, 소수 2자리). 결손 = "—".
	function fmtNum(v: number | null, unit: string): string {
		if (v == null) return '—';
		if (unit === '배') return v.toFixed(1) + (lang === 'en' ? 'x' : '배');
		if (unit === '일') return v.toFixed(0) + (lang === 'en' ? 'd' : '일');
		if (unit === '점') return v.toFixed(0) + (lang === 'en' ? '' : '점');
		if (unit === '') return v.toFixed(2);
		return v.toFixed(1) + '%';
	}

	const tcls = (t: string) =>
		(({ up: 'tUp', good: 'tGood', neutral: 'tNeu', warn: 'tWarn', down: 'tDn' }) as Record<string, string>)[t] || 'tNeu';

	const vd = $derived(co.verdict);
	// 좌측 스파이더 — co.radar 6축(0~1)만, 결손 축 제외(0대체 금지). audit(3단)는 radar 에 애초 부재.
	const radarAxes = $derived(
		co.radar
			.filter((r) => r.s != null)
			.map((r) => ({ label: lang === 'en' ? r.en : r.kr, value: (r.s as number) * 100 }))
	);
	// 등급기준 섹션 그루핑 — 각 등급축 아래에 그 축의 백분위 지표(분포곡선) 동반. eff(효율성)는 등급축 부재라 별도 그룹.
	const pct = $derived(co.percentile);
	const hasPct = $derived(!!pct && pct.n >= 5);
	function axisMetrics(key: string) {
		return pct ? pct.metrics.filter((m) => m.axis === key) : [];
	}
	const effMetrics = $derived(pct ? pct.metrics.filter((m) => m.axis === 'eff') : []);

	$effect(() => {
		const onKey = (e: KeyboardEvent) => {
			if (e.key === 'Escape') onClose();
		};
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});
</script>

<div class="scrimWrap" role="presentation" onclick={onClose}>
	<div
		class="scrModal geModal"
		role="dialog"
		aria-modal="true"
		aria-label={lang === 'en' ? 'Why this scan grade' : '스캔 등급 근거'}
		onclick={(e) => e.stopPropagation()}
	>
		<div class="scrHead">
			<span class="scrTitle">{lang === 'en' ? 'SCAN GRADE — why this grade' : '스캔 등급 — 왜 이 등급인가'}</span>
			<span class={'geBand ' + tcls(vd.band.tone)}>{txc(vd.band, lang)} <b class="mono">{vd.composite}</b></span>
			<span class="geCredit"><i>{lang === 'en' ? 'credit' : '신용'}</i> <b class="tCredit mono">{co.credit.grade}</b></span>
			<button class="scrClose" onclick={onClose} aria-label="close">✕</button>
		</div>

		<div class="geBody">
			<!-- 좌: 스파이더(레이더) -->
			<div class="geRadar">
				{#if radarAxes.length >= 3}
					<RadarChart axes={radarAxes} size={208} />
				{:else}
					<div class="geRadarEmpty">{lang === 'en' ? 'not enough graded axes for a radar' : '레이더를 그릴 등급 축 부족'}</div>
				{/if}
				<div class="geRadarNote">
					{lang === 'en' ? 'audit risk shown at right (3-tier scale)' : '감사위험은 3단이라 우측 별도'}
				</div>
			</div>

			<!-- 우: 왜 이 등급(근거) — 신용 + 강점/우려. 백분위·분포곡선은 아래 등급기준의 각 축으로 이동. -->
			<div class="geWhy">
				<div class="geCred">
					<span class="geCredK">{lang === 'en' ? 'credit' : '신용'}</span>
					<b class="tCredit mono">{co.credit.grade}</b>
					<span class="geCredX">{lang === 'en' ? 'health' : '건전도'} <b class="mono">{co.credit.healthScore}/100</b></span>
					<span class="geCredX">PD <b class="mono">{co.credit.pd}</b></span>
				</div>
				{#if vd.strengths.length}
					<div class="geGroup">
						<span class="geGl tUp">{lang === 'en' ? 'Strengths' : '강점'}</span>
						{#each vd.strengths as s}<span class="geTag up">{txc(s, lang)}</span>{/each}
					</div>
				{/if}
				{#if vd.concerns.length}
					<div class="geGroup">
						<span class="geGl tDn">{lang === 'en' ? 'Concerns' : '우려'}</span>
						{#each vd.concerns as c}<span class="geTag dn">{txc(c, lang)}</span>{/each}
					</div>
				{/if}
			</div>
		</div>

		<!-- 아래: 등급 기준 — 각 축 아래에 그 축 지표의 업종 분포곡선 + 회사 위치. -->
		<div class="geCriteria">
			<div class="geCrHead">
				{lang === 'en' ? 'Grade criteria' : '등급 기준'}{#if hasPct && pct} · {lang === 'en' ? `vs ${pct.n} peers` : `업종 ${pct.n}개사 내 위치`}{#if co.eco.industryRank != null} ({co.eco.industryRank}{lang === 'en' ? '' : '위'}){/if}{/if}
			</div>
			<div class="geCrGrid">
				{#each co.grades as g (g.key)}
					{@const scale = GRADE_SCALE[g.key] || []}
					{@const guide = GRADE_GUIDE[g.key]}
					{@const ms = axisMetrics(g.key)}
					<div class="geCr">
						<span class="geCrLabel">{txc(g, lang)}</span>
						{#if ms.length}
							<div class="geMxRow">
								{#each ms as m}
									<div class="geMx">
										<div class="geMxTop">
											<span class="geMxName">{txc(m, lang)}</span>
											<span class="geMxVal mono">{fmtNum(m.v, m.unit)}</span>
											<span class="geMxRank mono">{lang === 'en' ? 'top ' : '상위 '}{Math.max(1, 100 - (m.p ?? 0))}%</span>
										</div>
										{#if m.band}<DistCurve band={m.band} value={m.v} p={m.p ?? 50} unit={m.unit} {lang} />{/if}
									</div>
								{/each}
							</div>
						{/if}
						{#if guide}<div class="geCrWhat">{lang === 'en' ? guide.en.what : guide.kr.what}</div>{/if}
						<div class="geLadder">
							{#each scale as step}<span class={'geStep' + (step === g.v ? ' on' : '')}>{step}</span>{/each}
						</div>
					</div>
				{/each}
				{#if effMetrics.length}
					<div class="geCr">
						<span class="geCrLabel">{lang === 'en' ? 'Efficiency' : '효율성'}</span>
						<div class="geMxRow">
							{#each effMetrics as m}
								<div class="geMx">
									<div class="geMxTop">
										<span class="geMxName">{txc(m, lang)}</span>
										<span class="geMxVal mono">{fmtNum(m.v, m.unit)}</span>
										<span class="geMxRank mono">{lang === 'en' ? 'top ' : '상위 '}{Math.max(1, 100 - (m.p ?? 0))}%</span>
									</div>
									{#if m.band}<DistCurve band={m.band} value={m.v} p={m.p ?? 50} unit={m.unit} {lang} />{/if}
								</div>
							{/each}
						</div>
						<div class="geCrWhat">{lang === 'en' ? 'Asset activity — turnover & cash cycle' : '자산 활동성 — 자산회전율·현금전환주기'}</div>
					</div>
				{/if}
			</div>
			<div class="geNote">
				{lang === 'en'
					? '※ "—" means that figure is absent from this company’s filings (not filled with 0). The composite verdict uses 5 bands plus a continuous 0–100 score (top). Audit risk (3 tiers) and credit dCR (14 bands) are separate scales. A grade is an assessment with criteria — not a buy/sell signal.'
					: '※ "—" 는 해당 수치가 이 회사 공시에 없다는 뜻(0으로 채우지 않음). 종합 판정은 5밴드 + 연속 0~100 점수(상단). 감사위험(3단)·신용 dCR(14단)은 별도 스케일. 등급은 기준에 따른 판정이며 매수/매도 신호가 아니다.'}
			</div>
		</div>
	</div>
</div>

<style>
	.geModal {
		width: min(840px, 96vw);
	}
	.geBand {
		font-size: 11px;
		font-weight: 700;
		letter-spacing: 0.02em;
	}
	.geBand b {
		margin-left: 4px;
		font-size: 12px;
	}
	.geCredit {
		font-size: 10px;
		color: var(--dl-ink-dim, #5b6473);
	}
	.geCredit i {
		font-style: normal;
		margin-right: 3px;
	}
	.geBody {
		display: flex;
		gap: 16px;
		padding: 14px 14px 6px;
		align-items: flex-start;
	}
	.geRadar {
		flex: 0 0 224px;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 6px;
	}
	.geRadarEmpty {
		width: 208px;
		height: 208px;
		display: flex;
		align-items: center;
		justify-content: center;
		text-align: center;
		font-size: 11px;
		color: var(--dl-ink-dim, #5b6473);
		border: 1px dashed var(--dl-line, #1b2130);
		border-radius: 6px;
	}
	.geRadarNote {
		font-size: 9.5px;
		color: var(--dl-ink-dim, #5b6473);
		text-align: center;
		line-height: 1.4;
	}
	.geWhy {
		flex: 1 1 auto;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 9px;
	}
	.geGroup {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 5px;
	}
	.geGl {
		font-size: 10px;
		font-weight: 700;
		margin-right: 2px;
	}
	.geTag {
		font-size: 11px;
		padding: 2px 7px;
		border-radius: 10px;
		border: 1px solid var(--dl-line, #1b2130);
		background: rgba(255, 255, 255, 0.02);
	}
	.geTag.up {
		border-color: rgba(52, 211, 153, 0.35);
	}
	.geTag.dn {
		border-color: rgba(234, 70, 71, 0.35);
	}
	.geCriteria {
		border-top: 1px solid var(--dl-line, #1b2130);
		padding: 10px 14px 14px;
		background: rgba(255, 255, 255, 0.012);
	}
	.geCrHead {
		font-size: 10px;
		font-weight: 700;
		letter-spacing: 0.04em;
		color: var(--dl-ink-dim, #5b6473);
		margin-bottom: 8px;
	}
	.geCrGrid {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.geCr {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.geCrLabel {
		font-size: 11px;
		font-weight: 700;
		letter-spacing: 0.02em;
	}
	.geCrWhat {
		font-size: 10px;
		color: var(--dl-ink-dim, #5b6473);
		line-height: 1.4;
	}
	.geLadder {
		display: flex;
		flex-wrap: wrap;
		gap: 3px;
		margin-top: 1px;
	}
	.geStep {
		font-size: 9px;
		padding: 1px 5px;
		border-radius: 7px;
		color: var(--dl-ink-dim, #5b6473);
		background: rgba(255, 255, 255, 0.03);
	}
	.geStep.on {
		color: var(--dl-bg-raised, #0e141f);
		background: var(--color-dl-primary, #ea4647);
		font-weight: 700;
	}
	.geNote {
		font-size: 9.5px;
		color: var(--dl-ink-dim, #5b6473);
		line-height: 1.5;
		margin-top: 10px;
	}
	/* 등급기준 — 각 축 지표 행(이름·값·상위% + 분포곡선) */
	/* 일관 격자 — 모든 지표 셀 동일 폭(152px) → 축 간 컬럼이 딱 맞아떨어짐 */
	.geMxRow {
		display: flex;
		flex-wrap: wrap;
		gap: 8px 12px;
	}
	.geMx {
		width: 152px;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.geMxTop {
		display: flex;
		align-items: baseline;
		gap: 4px;
	}
	.geMxName {
		font-size: 10px;
		font-weight: 600;
	}
	.geMxVal {
		font-size: 10px;
		color: var(--dl-ink, #c8cfdb);
		font-variant-numeric: tabular-nums;
	}
	.geMxRank {
		font-size: 9px;
		margin-left: auto;
		color: var(--dl-ink-dim, #5b6473);
		font-variant-numeric: tabular-nums;
	}
	.geCred {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 10.5px;
		padding-top: 2px;
		border-top: 1px dashed var(--dl-line, #1b2130);
	}
	.geCredK {
		font-size: 10px;
		color: var(--dl-ink-dim, #5b6473);
	}
	.geCredX {
		font-size: 10px;
		color: var(--dl-ink-dim, #5b6473);
		font-variant-numeric: tabular-nums;
	}
	.geCredX b {
		color: var(--dl-ink, #c8cfdb);
	}
</style>
