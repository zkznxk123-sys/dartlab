// ReportModel → CarouselDeck 순수 투영 — 굽지 않음·런타임 비의존(fixture 로 단위테스트 가능).
// 핵심 정직장치: projectBlock 이 ReportBlock 8 변종을 *명시* 매핑하고 default 에서 assertNever 로
// 컴파일/런타임 fail-loud → 새 ReportBlock 추가 시 "여기 매핑 안 하면 의도적 비-캐러셀"을 강제 선언.
// silent drop 금지. pending/skip 은 broken img 가 아니라 정직 empty 카드로.
import type { ReportBlock, ReportModel, ReportResult, OverviewModel } from '$lib/report/model';
import { isSkipped } from '$lib/report/model';
import { clean, splitTitle, isTimeSeries } from '$lib/report/render';
import type { CarouselCard, CarouselDeck, CarouselSpec } from './model';

interface HeadCtx {
	heading?: string;
	sub?: string;
	engine?: ReportModel['sections'][number]['sourceEngine'];
}

function assertNever(x: never): never {
	throw new Error(`projectBlock: 미매핑 ReportBlock 변종 — ${JSON.stringify(x)}`);
}

/** 카드용 초단문 — 첫 문장(마침표까지)만, 길면 자른다. 캐러셀은 리포트가 아니라 한 줄 후킹(기존 SNS 카피 톤). */
function hook(text: string, max = 80): string {
	const t = clean(text).trim();
	const dot = t.search(/[.!?]\s|다\.\s|입니다\.\s/);
	let s = dot > 0 && dot < max + 12 ? t.slice(0, t.indexOf('. ', dot - 1) + 1 || dot + 1) : t;
	if (s.length > max) s = s.slice(0, max).trim() + '…';
	return s.trim();
}

/** ReportBlock 1개 → 슬라이드 카드 또는 null(명시 skip). 모든 변종을 다뤄야 컴파일됨(exhaustive). */
export function projectBlock(block: ReportBlock, head: HeadCtx): CarouselCard | null {
	switch (block.type) {
		case 'heading':
			return null; // 헤딩은 다음 카드의 head 로 접힘 — 독립 슬라이드 아님(명시 skip)
		case 'text': {
			const t = clean(block.text).trim();
			return t.length >= 24 ? { ...head, kind: 'narrative', text: hook(t, 130) } : null; // 첫 문장만(벽 금지)
		}
		case 'metrics':
			return block.metrics.length ? { ...head, kind: 'kpis', metrics: block.metrics } : null;
		case 'flags':
			return block.flags.length ? { ...head, kind: 'flags', tone: block.kind, items: block.flags } : null;
		case 'bars':
			return block.rows.length ? { ...head, kind: 'bars', rows: block.rows } : null;
		case 'line':
			return block.series.filter((n) => Number.isFinite(n)).length >= 2
				? { ...head, kind: 'line', series: block.series, xLabels: block.xLabels, markers: block.markers, valueFmt: block.valueFmt }
				: null;
		case 'share':
			return block.rows.length ? { ...head, kind: 'share', rows: block.rows, legend: block.legend } : null;
		case 'table': {
			const raw = block.data.length ? Object.keys(block.data[0]) : [];
			// 시계열 표만 캐러셀(스파크라인) — 비시계열 dense 표는 슬라이드에 안 맞아 명시 skip.
			if (!isTimeSeries(raw)) return null;
			// 4:5 카드는 좁다 → 라벨(기간 아닌 첫 열) + 최근 6기간만. 라벨이 끝열인 표(연간추세=
			// [2020..2025, '연간 지표'])도 맨 앞으로 정규화해 열 어긋남 방지, 요약열(YoY/TTM)은 드롭
			// (추이 스파크라인이 흐름 전달). 9~10열을 8열 이하로 줄여 헤더 절단('24…')도 해소.
			const isPd = (c: string) => /^\d{4}$/.test(c) || /^\d{2}Q[1-4]$/.test(c);
			const periods = raw.filter(isPd);
			const label = raw.find((c) => !isPd(c)) ?? raw[0];
			const cols = [label, ...periods.slice(-6)];
			return { ...head, kind: 'table', cols, data: block.data, unit: block.unit };
		}
		default:
			return assertNever(block);
	}
}

/** 관점 보고서 → 슬라이드 덱. cover → KPIs → finChart 백본 → 섹션 블록 → closing.
 *  hero 사진 전부를 슬라이드 배경으로 순환 배정(인스타 에디토리얼). opts.spec(blog frontmatter
 *  `carousel:`)이 있으면 큐레이션 오버레이 — order 로 섹션 필터/재정렬, notes[key] 로 손글 caption. */
export function projectReport(
	model: ReportModel,
	opts: { heroUrls?: string[]; spec?: CarouselSpec; lead?: CarouselCard[] } = {}
): CarouselDeck {
	const spec = opts.spec;
	const heroUrls = opts.heroUrls ?? [];
	const lead = opts.lead ?? [];
	const base = {
		stockCode: model.stockCode,
		corpName: model.corpName,
		perspectiveKey: model.perspectiveKey,
		perspectiveLabel: model.perspectiveLabel,
		asOf: model.asOf,
		heroUrls
	};
	// lead(편집 계약 슬라이드)가 있으면 그것이 표지·서사 — 자동 cover 생략. 없으면 자동 cover.
	const cards: CarouselCard[] = lead.length
		? [...lead]
		: [
				{
					kind: 'cover',
					corpName: model.corpName,
					stockCode: model.stockCode,
					perspectiveLabel: model.perspectiveLabel,
					conclusion: hook(model.conclusion, 70), // 표지는 한 줄 후킹(리포트 결론 문단 전체 금지)
					dataBasis: model.dataBasis
				}
			];

	// 미구현 관점 → 정직 빈 카드(broken img 아님). lead 가 있으면 편집 슬라이드는 보존.
	if (model.pending) {
		if (!lead.length) cards.push({ kind: 'empty', reason: `${model.perspectiveLabel} 관점은 다음 사이클에 추가됩니다.` });
		assignHeroes(cards, heroUrls);
		return { ...base, cards };
	}

	if (model.headlineKpis.length) cards.push({ kind: 'kpis', heading: '핵심 지표', metrics: model.headlineKpis });
	cards.push({ kind: 'finChart', heading: '재무 추이', stockCode: model.stockCode });

	// 큐레이션 order: 섹션 key 화이트리스트로 필터/재정렬(없으면 원순서). 미지정 key 는 무시(누락 surface 는 audit).
	let sections = model.sections;
	if (spec?.order?.length) {
		const rank = new Map(spec.order.map((k, i) => [k, i]));
		sections = model.sections.filter((s) => rank.has(s.key)).sort((a, b) => rank.get(a.key)! - rank.get(b.key)!);
	}

	for (const sec of sections) {
		const { head, sub } = splitTitle(sec.title);
		const headCtx: HeadCtx = { heading: head, sub, engine: sec.sourceEngine };
		const card = pickSectionCard(sec.blocks, headCtx); // 섹션당 1장(시각 우선) — 텍스트 도배·과다 슬라이드 방지
		if (card) {
			const note = spec?.notes?.[sec.key];
			if (note) card.note = note;
			cards.push(card);
		}
	}

	// 종합(closing)·자동 산문 제거 — 자동은 표·그래프만. 종합/서사는 수기 editorial 슬라이드(carousel: 블록)로.

	assignHeroes(cards, heroUrls);
	return { ...base, cards };
}

// 자동 섹션 슬라이드 = **시각(표·그래프)만**. 산문(narrative)·신호(flags)·지표(kpis) 자동 생성 금지
// (자동 텍스트는 엉망 — 종합/서사는 수기 editorial 슬라이드로). 섹션당 1장(시각 우선·과다 슬라이드 방지).
const AUTO_VISUAL = new Set(['line', 'bars', 'share', 'table']);
const KIND_RANK: Record<string, number> = { line: 0, bars: 0, share: 1, table: 2 };
function pickSectionCard(blocks: ReportBlock[], head: HeadCtx): CarouselCard | null {
	const cards = blocks
		.map((b) => projectBlock(b, head))
		.filter((c): c is CarouselCard => c !== null && AUTO_VISUAL.has(c.kind));
	if (!cards.length) return null;
	return cards.sort((a, b) => (KIND_RANK[a.kind] ?? 9) - (KIND_RANK[b.kind] ?? 9))[0];
}

/** hero 사진 전부를 슬라이드에 순환 배정 — 한 장도 안 빠지게. 이미 bg 있는 카드(편집 계약 image)는 보존. */
function assignHeroes(cards: CarouselCard[], heroUrls: string[]): void {
	if (!heroUrls.length) return;
	cards.forEach((c, i) => {
		if (c.kind !== 'empty' && !c.bg) c.bg = heroUrls[i % heroUrls.length];
	});
}

/** buildReport 결과(또는 skip) → 덱. skip 도 정직 카드로 렌더(빈 화면 금지). */
export function projectResult(
	result: ReportResult,
	perspectiveLabel: string,
	opts: { heroUrls?: string[]; spec?: CarouselSpec; lead?: CarouselCard[] } = {}
): CarouselDeck {
	if (isSkipped(result)) {
		// 데이터 skip 이어도 편집 계약 슬라이드(lead)는 그대로 보여준다(굽지 않은 손글). 없으면 정직 빈 카드.
		const cards = opts.lead?.length ? [...opts.lead] : [{ kind: 'empty' as const, reason: result.reason }];
		return {
			stockCode: result.stockCode,
			corpName: result.stockCode,
			perspectiveKey: '',
			perspectiveLabel,
			asOf: '',
			heroUrls: opts.heroUrls ?? [],
			cards
		};
	}
	return projectReport(result, opts);
}

/** 5관점 통합 thesis → 덱 머리에 붙일 closing 카드(있으면). LLM·신규합성 0(overview.thesis 그대로). */
export function overviewClosingCard(overview: OverviewModel | null): CarouselCard | null {
	const t = clean(overview?.thesis ?? '').trim();
	return t ? { kind: 'closing', heading: '5관점 통합', thesis: t } : null;
}
