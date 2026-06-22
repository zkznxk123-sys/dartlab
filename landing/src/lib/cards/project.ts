// ReportModel → CarouselDeck 순수 투영 — 굽지 않음·런타임 비의존(fixture 로 단위테스트 가능).
// 핵심 정직장치: projectBlock 이 ReportBlock 8 변종을 *명시* 매핑하고 default 에서 assertNever 로
// 컴파일/런타임 fail-loud → 새 ReportBlock 추가 시 "여기 매핑 안 하면 의도적 비-캐러셀"을 강제 선언.
// silent drop 금지. pending/skip 은 broken img 가 아니라 정직 empty 카드로.
import type { ReportBlock, ReportModel, ReportResult, OverviewModel } from '$lib/report/model';
import { isSkipped } from '$lib/report/model';
import { clean, splitTitle, isTimeSeries } from '$lib/report/render';
import type { CarouselCard, CarouselDeck } from './model';

interface HeadCtx {
	heading?: string;
	sub?: string;
	engine?: ReportModel['sections'][number]['sourceEngine'];
}

function assertNever(x: never): never {
	throw new Error(`projectBlock: 미매핑 ReportBlock 변종 — ${JSON.stringify(x)}`);
}

/** ReportBlock 1개 → 슬라이드 카드 또는 null(명시 skip). 모든 변종을 다뤄야 컴파일됨(exhaustive). */
export function projectBlock(block: ReportBlock, head: HeadCtx): CarouselCard | null {
	switch (block.type) {
		case 'heading':
			return null; // 헤딩은 다음 카드의 head 로 접힘 — 독립 슬라이드 아님(명시 skip)
		case 'text': {
			const t = clean(block.text).trim();
			return t.length >= 24 ? { ...head, kind: 'narrative', text: t } : null; // 너무 짧은 텍스트 skip
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
			const cols = block.data.length ? Object.keys(block.data[0]) : [];
			// 시계열 표만 캐러셀(스파크라인) — 비시계열 dense 표는 슬라이드에 안 맞아 명시 skip.
			return isTimeSeries(cols) ? { ...head, kind: 'table', cols, data: block.data, unit: block.unit } : null;
		}
		default:
			return assertNever(block);
	}
}

/** 관점 보고서 → 슬라이드 덱. cover → KPIs → finChart 백본 → 섹션 블록 → closing. */
export function projectReport(model: ReportModel, opts: { heroUrl?: string } = {}): CarouselDeck {
	const base = {
		stockCode: model.stockCode,
		corpName: model.corpName,
		perspectiveKey: model.perspectiveKey,
		perspectiveLabel: model.perspectiveLabel,
		asOf: model.asOf,
		heroUrl: opts.heroUrl
	};
	const cards: CarouselCard[] = [
		{
			kind: 'cover',
			corpName: model.corpName,
			stockCode: model.stockCode,
			perspectiveLabel: model.perspectiveLabel,
			conclusion: clean(model.conclusion),
			dataBasis: model.dataBasis,
			heroUrl: opts.heroUrl
		}
	];

	// 미구현 관점 → 정직 빈 카드(broken img 아님).
	if (model.pending) {
		cards.push({ kind: 'empty', reason: `${model.perspectiveLabel} 관점은 다음 사이클에 추가됩니다.` });
		return { ...base, cards };
	}

	if (model.headlineKpis.length) cards.push({ kind: 'kpis', heading: '핵심 지표', metrics: model.headlineKpis });
	cards.push({ kind: 'finChart', heading: '재무 추이', stockCode: model.stockCode });

	for (const sec of model.sections) {
		const { head, sub } = splitTitle(sec.title);
		const headCtx: HeadCtx = { heading: head, sub, engine: sec.sourceEngine };
		for (const block of sec.blocks) {
			const card = projectBlock(block, headCtx);
			if (card) cards.push(card);
		}
	}

	const thesis = clean(model.closing.map((c) => c.line).filter(Boolean).join(' ').trim() || model.conclusion);
	if (thesis) cards.push({ kind: 'closing', heading: '종합', thesis });

	return { ...base, cards };
}

/** buildReport 결과(또는 skip) → 덱. skip 도 정직 카드로 렌더(빈 화면 금지). */
export function projectResult(
	result: ReportResult,
	perspectiveLabel: string,
	opts: { heroUrl?: string } = {}
): CarouselDeck {
	if (isSkipped(result)) {
		return {
			stockCode: result.stockCode,
			corpName: result.stockCode,
			perspectiveKey: '',
			perspectiveLabel,
			asOf: '',
			heroUrl: opts.heroUrl,
			cards: [{ kind: 'empty', reason: result.reason }]
		};
	}
	return projectReport(result, opts);
}

/** 5관점 통합 thesis → 덱 머리에 붙일 closing 카드(있으면). LLM·신규합성 0(overview.thesis 그대로). */
export function overviewClosingCard(overview: OverviewModel | null): CarouselCard | null {
	const t = clean(overview?.thesis ?? '').trim();
	return t ? { kind: 'closing', heading: '5관점 통합', thesis: t } : null;
}
