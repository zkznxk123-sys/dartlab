<script lang="ts">
	// 스캔 등급 설명 다이얼로그 — "왜 이 등급인가". 좌 스파이더 / 우 근거 / 아래 기준.
	// ★신규 능력 0: 데이터(co.radar·co.verdict·co.analysis.tracks·co.credit·co.grades)는 전부 엔진 산물(공동배선
	//   = 퍼블릭·로컬 동일). 모달 크롬은 전역 .scrimWrap/.scrModal/.scrHead/.scrClose 재사용. 레이더는 map RadarChart 재사용.
	// 정직: 매수/매도 신호·목표주가·인과 금지. 결손 축은 채우지 않고 뺀다(0대체 금지). 등급 = 판정(근거+기준 동반).
	import type { Company, Lang } from '../lib/types';
	import { GRADE_SCALE } from '../lib/engine';
	import { GRADE_GUIDE } from '../lib/gradeGuide';
	import { tx, txc } from '../ui/helpers';
	import RadarChart from '../../map/components/RadarChart.svelte';

	interface Props {
		co: Company;
		lang: Lang;
		onClose: () => void;
	}
	let { co, lang, onClose }: Props = $props();

	const tcls = (t: string) =>
		(({ up: 'tUp', good: 'tGood', neutral: 'tNeu', warn: 'tWarn', down: 'tDn' }) as Record<string, string>)[t] || 'tNeu';

	const vd = $derived(co.verdict);
	// 좌측 스파이더 — co.radar 6축(0~1)만, 결손 축 제외(0대체 금지). audit(3단)는 radar 에 애초 부재.
	const radarAxes = $derived(
		co.radar
			.filter((r) => r.s != null)
			.map((r) => ({ label: lang === 'en' ? r.en : r.kr, value: (r.s as number) * 100 }))
	);

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

			<!-- 우: 왜 이 등급(근거) -->
			<div class="geWhy">
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
				<div class="geCells">
					{#each co.analysis.tracks as t}
						<div class="geCell">
							<span class={'geCk ' + tcls(t.tone)}>{txc(t, lang)}</span>
							<b>{tx(t.verdict, lang)}</b>
						</div>
					{/each}
				</div>
			</div>
		</div>

		<!-- 아래: 등급 기준(주석) -->
		<div class="geCriteria">
			<div class="geCrHead">{lang === 'en' ? 'Grade criteria' : '등급 기준'}</div>
			<div class="geCrGrid">
				{#each co.grades as g (g.key)}
					{@const scale = GRADE_SCALE[g.key] || []}
					{@const guide = GRADE_GUIDE[g.key]}
					<div class="geCr">
						<div class="geCrTop">
							<span class="geCrLabel">{txc(g, lang)}</span>
							<span class={'geCrCur ' + tcls(g.tone)}>{g.v}</span>
						</div>
						{#if guide}<div class="geCrWhat">{lang === 'en' ? guide.en.what : guide.kr.what}</div>{/if}
						<div class="geLadder">
							{#each scale as step}<span class={'geStep' + (step === g.v ? ' on' : '')}>{step}</span>{/each}
						</div>
					</div>
				{/each}
			</div>
			<div class="geNote">
				{lang === 'en'
					? '※ The composite verdict uses 5 bands plus a continuous 0–100 score (top). Audit risk (3 tiers) and credit dCR (14 bands) are separate scales. A grade is an assessment with criteria — not a buy/sell signal.'
					: '※ 종합 판정은 5밴드 + 연속 0~100 점수(상단). 감사위험(3단)·신용 dCR(14단)은 별도 스케일. 등급은 기준에 따른 판정이며 매수/매도 신호가 아니다.'}
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
	.geCells {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 6px 14px;
		margin-top: 2px;
	}
	.geCell {
		display: flex;
		flex-direction: column;
		gap: 1px;
		border-left: 2px solid var(--dl-line, #1b2130);
		padding-left: 8px;
	}
	.geCk {
		font-size: 10px;
		font-weight: 600;
	}
	.geCell b {
		font-size: 11px;
		font-weight: 500;
		color: var(--dl-ink, #c8cfdb);
		font-variant-numeric: tabular-nums;
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
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(178px, 1fr));
		gap: 8px 14px;
	}
	.geCr {
		display: flex;
		flex-direction: column;
		gap: 3px;
	}
	.geCrTop {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 6px;
	}
	.geCrLabel {
		font-size: 11px;
		font-weight: 600;
	}
	.geCrCur {
		font-size: 11px;
		font-weight: 700;
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
</style>
