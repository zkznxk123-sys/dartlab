<script lang="ts">
	// 주석 대시보드 — 정기보고서 주석에서 파싱한 찐정보를 시각적으로 한눈에. 단일 스크롤·탭 없음(7에이전트 UI/UX 설계).
	// 첫 슬라이스 = 비용 체질 HERO 카드(100% 적층바 + 항목 랭크). 정직: 못 파싱한 건 발췌 폴백·날조 0·종합점수/백분위 0.
	// 색·바·mono 전부 terminal.css 기존 토큰. scope(연결/별도)는 section 동적 도출(하드코딩 금지).
	import type { Company, Lang } from '../lib/types';
	import type { ReportNoteBlock } from '@dartlab/ui-contracts';
	import { fmtKRW } from '../lib/engine';
	import { viewerUrl, marketForCode } from '../../viewer/lib/dartUrl';

	interface Props {
		co: Company;
		lang: Lang;
		notes: ReportNoteBlock[];
		onClose: () => void;
	}
	let { co, lang, notes, onClose }: Props = $props();
	const T = (kr: string, en: string): string => (lang === 'en' ? en : kr);

	$effect(() => {
		const onKey = (e: KeyboardEvent) => {
			if (e.key === 'Escape') onClose();
		};
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});

	const cost = $derived(notes.find((n) => n.topic === 'costNature' && n.composition) ?? null);
	const scopeLabel = (section: string): string => (section.includes('연결') ? T('연결', 'CONS') : T('별도', 'SEP'));
	const costSrc = $derived(cost ? viewerUrl(marketForCode(co.code), cost.rceptNo) : null);

	// 세그먼트 색 = terminal.css 기존 토큰 순환(의미없는 카테고리 구분, 범례칩으로 해소). 신규 색 0.
	const SEG = ['var(--good)', 'var(--up)', 'var(--amber)', 'var(--warn)', 'var(--dim)'];
	const segColor = (i: number, last: boolean): string => (last ? 'var(--dimmer)' : SEG[i % SEG.length] ?? 'var(--dim)');
	// 긴 항목명 → 범례용 단축
	const shortName = (n: string): string => n.replace(/\s*및\s*/g, '·').replace(/(매입액|사용액|비용|비$)/g, '').trim().slice(0, 6);

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
						<span class="ndCardTitle">{T('비용 체질', 'COST CHASSIS')} <span class="dim">· {T('돈을 뭐에 쓰나', 'where the money goes')}</span></span>
						<span class="ndHdRight">
							<span class="ndScope">[{scopeLabel(cost.section)}]</span>
							{#if costSrc}<a class="factSrc" href={costSrc} target="_blank" rel="noopener" title={T('원문 공시', 'source filing')}>↗{T('원문', '')}</a>{/if}
						</span>
					</div>
					<div class="ndTotal">{T('합계', 'total')} <b class="mono">{fmtKRW(comp.total)}</b> = 100% · {comp.items.length}{T('개 항목', ' items')}</div>
					<!-- 100% 적층바 — 한 줄로 비용 체질 실루엣 -->
					<div class="ndStack">
						{#each comp.items as it, i (it.name)}
							<div class="ndSeg" style={`width:${it.pct}%;background:${segColor(i, i === comp.items.length - 1 && it.name.startsWith('기타'))}`} title={`${it.name} · ${it.pct.toFixed(1)}% · ${fmtKRW(it.amount)}`}></div>
						{/each}
					</div>
					<div class="ndLegend">
						{#each comp.items as it, i (it.name)}
							<span class="ndLeg"><i style={`background:${segColor(i, i === comp.items.length - 1 && it.name.startsWith('기타'))}`}></i>{it.name.startsWith('기타') ? T('기타', 'other') : shortName(it.name)} {it.pct.toFixed(0)}</span>
						{/each}
					</div>
					<!-- 항목 랭크 (금액 desc) -->
					<div class="ndRanks">
						{#each comp.items as it, i (it.name)}
							<div class="ndRank">
								<span class="ndRankName" title={it.name}>{it.name}</span>
								<span class="ndRankPct mono">{it.pct.toFixed(1)}%</span>
								<span class="ndRankBar"><i style={`width:${Math.max(1, it.pct)}%;background:${segColor(i, i === comp.items.length - 1 && it.name.startsWith('기타'))}`}></i></span>
								<span class="ndRankAmt mono">{fmtKRW(it.amount)}</span>
							</div>
						{/each}
					</div>
					{#if chassis}<div class="ndChassis">⟨{chassis}⟩ <span class="dim">{T('최대 항목 기준 · 판정 아님', 'largest item · not a verdict')}</span></div>{/if}
				</div>
			{:else}
				<div class="storyEmpty">{T('이 회사는 비용 성격별 주석 미공시 (또는 비정형 — 파싱 불가). 0 대체 안 함.', 'no cost-by-nature note disclosed (or non-standard).')}</div>
			{/if}
			<div class="ndFoot">{T('report · 정기보고서 주석 파싱 · 단일시점 · 못 뽑은 값은 원문 발췌(날조 0) · 종합점수·동종백분위 없음 · 숫자 ↗원문', 'parsed from periodic-report notes · single point-in-time · no composite score / peer percentile')}</div>
		</div>
	</div>
</div>
