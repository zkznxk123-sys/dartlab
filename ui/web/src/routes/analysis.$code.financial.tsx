// /analysis/$code/financial — 재무제표분석.
// 자금조달 → 영업 선순환 → 현금·안정 3 narrative section. 사용자 명시 흐름
// (자산구조 → 부채상세 → 자본상세 → 손익구조) 한 viewport 진입, 그 다음 스크롤로
// 마진/수익성/현금/안정 분기. 카드 KPI tile 8 폐기.

import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { createFileRoute, getRouteApi } from '@tanstack/react-router';
import { Loader2 } from 'lucide-react';

import { CardShell } from '@/features/dashboard/cards/CardShell';
import { ChartMiniTable } from '@/features/dashboard/cards/ChartMiniTable';
import { VizChart } from '@/features/dashboard/charts/VizChart';
import {
	BentoGrid,
	BENTO_GAP_PX,
	BENTO_CARD_HEADER_PX,
	BENTO_CARD_PAD_PX,
} from '@/features/dashboard/layout/BentoGrid';
import {
	fetchCard,
	fetchCatalog,
	fetchTabLayout,
	type CatalogCard,
	type FinancialSubCategory,
	type PackedCard,
	type PeriodKind,
	type RechartsSpec,
} from '@/features/dashboard/api/client';
import { dashKeys } from '@/features/dashboard/api/queryKeys';
import { formatValue } from '@/lib/format';

type SubView = FinancialSubCategory;

export const Route = createFileRoute('/analysis/$code/financial')({
	component: FinancialTab,
	validateSearch: (_search: Record<string, unknown>): { view: SubView | null } => {
		// v3-r6 — sub view 일시 폐기. URL ?view stale 도 무조건 null → OVERVIEW_KEYS curated 1 view.
		return { view: null };
	},
});

const parentRoute = getRouteApi('/analysis/$code');

function ChartLoading() {
	return (
		<div className="flex h-[220px] w-full items-center justify-center text-muted-foreground">
			<Loader2 className="size-5 animate-spin" />
		</div>
	);
}

// 카드 1 장당 useQuery 1 개 — mount 시 즉시 fetch, 가장 빠른 카드부터 paint.
// 이전: layout API 가 34 카드 spec 다 들고와서 가장 느린 카드가 전체 막음.
function CardWithQuery({
	stockCode,
	periodKind,
	packed,
	meta,
	cardOuterH,
	computeHeaderMetric,
}: {
	stockCode: string;
	periodKind: PeriodKind;
	packed: PackedCard;
	meta: CatalogCard | undefined;
	cardOuterH: number;
	computeHeaderMetric: (spec: RechartsSpec | undefined) => React.ReactNode;
}) {
	const { data: spec, isError } = useQuery({
		queryKey: dashKeys.card(packed.cardKey, stockCode, periodKind),
		queryFn: () => fetchCard(packed.cardKey, stockCode, periodKind, 40),
		placeholderData: keepPreviousData,
		staleTime: 5 * 60_000,
		retry: 1,
	});
	const title = meta?.title || spec?.title || packed.title;
	const help = meta?.help;
	const seriesCount = spec?.series?.length ?? 0;
	const isDualStack = spec?.options?.dualStack === true;
	const hasFooter = !!(spec && spec.kind === 'trend' && seriesCount > 0 && !isDualStack);
	const footer = hasFooter ? <ChartMiniTable spec={spec} /> : undefined;
	const footerHeight = hasFooter ? 20 * Math.min(seriesCount, 12) + 20 + 8 + 1 : 0;
	const bodyHeight = Math.max(
		60,
		cardOuterH - BENTO_CARD_HEADER_PX - BENTO_CARD_PAD_PX - footerHeight,
	);
	const kind = spec?.kind ?? packed.kind;
	const headerMetric = computeHeaderMetric(spec);
	const ready = !!spec && !spec.error && !isError;
	return (
		<CardShell
			title={title}
			help={help}
			colSpan={packed.w}
			rowSpan={packed.h}
			kind={kind}
			footer={ready ? footer : undefined}
			headerExtra={ready ? headerMetric : undefined}
		>
			{ready ? (
				<VizChart spec={spec} height={bodyHeight} size={{ w: packed.w, h: packed.h }} />
			) : (
				<ChartLoading />
			)}
		</CardShell>
	);
}

function FinancialTab() {
	const { code } = Route.useParams();
	const { period: periodKind } = parentRoute.useSearch();

	const { data: catalog } = useQuery({
		queryKey: dashKeys.catalog(),
		queryFn: fetchCatalog,
		staleTime: Infinity,
	});

	// v3-r6 — sub view 폐기. view 항상 null → backend OVERVIEW_KEYS curated.
	// progressive load — layout 만 먼저 받고 (수 ms), 카드 spec 은 CardWithQuery 가 카드별 fetch.
	const apiView = null;
	const { data, isError, isLoading, error } = useQuery({
		queryKey: dashKeys.tabLayout('financial', code, apiView, periodKind),
		queryFn: () => fetchTabLayout('financial', code, apiView, periodKind, 40, true),
		placeholderData: keepPreviousData,
		staleTime: 5 * 60_000,
		retry: 1,
	});

	const cardMetaByKey: Record<string, CatalogCard | undefined> = Object.fromEntries(
		(catalog?.cards ?? []).map((c) => [c.cardKey, c]),
	);

	// Tremor 정통 — 헤더 우측 latest value + YoY Δ (% point or 비율 변화). primary 시리즈
	// (또는 첫 비-stack 시리즈) 의 마지막 유효값과 4 분기 전 값 비교. dual-stack / multi-axis
	// 카드는 모호하므로 표시 생략.
	function computeHeaderMetric(spec: RechartsSpec | undefined): React.ReactNode {
		if (!spec || spec.kind !== 'trend') return null;
		if (spec.options?.dualStack) return null;
		if (!spec.series?.length) return null;
		// primary series 선택 우선순위: intent='primary' → 첫 비-stack line → series[0].
		const primary =
			spec.series.find((s) => s.intent === 'primary') ??
			spec.series.find((s) => !s.stack && s.type === 'line') ??
			spec.series[0];
		const data = primary?.data ?? [];
		const lastIdx = data.length - 1;
		const last = lastIdx >= 0 ? data[lastIdx] : null;
		// 비교 기간 — periodKind 가 quarterly 면 4 step 전 (YoY), annual 이면 1 step 전.
		const lookback = periodKind === 'quarterly' ? 4 : 1;
		const prevIdx = lastIdx - lookback;
		const prev = prevIdx >= 0 ? data[prevIdx] : null;
		if (last == null || !Number.isFinite(last as number)) return null;
		const unit = primary?.unit ?? '';
		const lastStr = formatValue(last as number, unit);
		let deltaNode: React.ReactNode = null;
		if (prev != null && Number.isFinite(prev as number)) {
			// % 단위는 절대값 차이 (%p), 외 단위는 비율 변화 (%).
			const isPct = unit === '%' || unit === '배' || unit === '회';
			const delta = isPct
				? (last as number) - (prev as number)
				: (prev as number) !== 0
					? ((last as number) - (prev as number)) / Math.abs(prev as number) * 100
					: null;
			if (delta != null && Number.isFinite(delta)) {
				const sign = delta > 0 ? '+' : '';
				const suffix = isPct ? (unit === '%' ? '%p' : (unit === '회' ? '회' : '배')) : '%';
				const tone =
					Math.abs(delta) < 0.05
						? 'text-muted-foreground/80'
						: delta > 0
							? 'text-emerald-500 dark:text-emerald-400'
							: 'text-rose-500 dark:text-rose-400';
				deltaNode = (
					<span className={`text-[10.5px] font-medium ${tone}`}>
						{sign}
						{Math.abs(delta) >= 10 ? delta.toFixed(0) : delta.toFixed(1)}
						{suffix}
					</span>
				);
			}
		}
		return (
			<>
				<span className="text-[12px] font-mono font-semibold text-foreground">{lastStr}</span>
				{deltaNode}
			</>
		);
	}

	const renderCard = (p: PackedCard, cellSize: number) => {
		const meta = cardMetaByKey[p.cardKey];
		const cardOuterH = p.h * cellSize + (p.h - 1) * BENTO_GAP_PX;
		return (
			<CardWithQuery
				stockCode={code}
				periodKind={periodKind}
				packed={p}
				meta={meta}
				cardOuterH={cardOuterH}
				computeHeaderMetric={computeHeaderMetric}
			/>
		);
	};

	const placed = data?.layout ?? [];

	// narrative section 정의 — cardKey → sectionIdx. backend layout 그대로 받되
	// 여기서 split 후 각 section 내 y 좌표 normalize (그룹 내 min y 빼기).
	// 정통 분석 10 단계 매핑 — 5 section narrative.
	const SECTIONS: { title: string; subtitle: string; keys: Set<string> }[] = [
		{
			title: '자본구조 · 자산구조',
			subtitle: '자산 = 부채+자본. 어떻게 자금조달해서 어떤 영업자산을 굴리는가 — CCC 까지.',
			keys: new Set([
				'assetComposition',
				'liabilityDetail',
				'equityDetail',
				'cashAssetsRatio',
				'incomeBreakdown',
				'workingCapitalDays',
			]),
		},
		{
			title: '영업 효율 · 자본 효율',
			subtitle: '마진·수익성·DuPont 5단·Penman·ROIC-WACC·세그먼트 — 본업이 진짜로 돈을 버는가.',
			keys: new Set([
				'marginTrend',
				'returnTrend',
				'dupont5Step',
				'penmanRoeDecomp',
				'roic',
				'roicWaccGap',
				'costStructureTrend',
				'turnoverTrend',
				'operatingLeverage',
				'taxWalk',
				'segmentRevenue',
				'effectiveTaxRate',
			]),
		},
		{
			title: '현금 일생 · 자본배분',
			subtitle: '현금흐름·FCF·자본배분·배당성향·이익품질·발생액·순차입금 — 번 돈은 어디로.',
			keys: new Set([
				'cashflowSigned',
				'fcfTrend',
				'capitalAllocation',
				'payoutRatio',
				'earningsQuality',
				'sloanAccruals',
				'netDebt',
			]),
		},
		{
			title: '재무 안정 · 부도 위험',
			subtitle: '안정성·유동성·Altman Z·5 모델 ensemble·이자보상·레버리지 — 망할 수 있는가.',
			keys: new Set([
				'stabilityRatio',
				'liquidityTrend',
				'leverageTrend',
				'interestCoverage',
				'altmanZ',
				'distressEnsemble',
			]),
		},
		{
			title: '성장의 질 · 이상신호',
			subtitle: '매출 YoY·자본 YoY·사업 집중도 — 성장이 진짜인가, 한 사업에 몰빵인가.',
			keys: new Set([
				'growthYoy',
				'equityGrowth',
				'segmentConcentration',
			]),
		},
	];

	const grouped = SECTIONS.map((section) => {
		const cards = placed.filter((p) => section.keys.has(p.cardKey));
		if (cards.length === 0) return null;
		const minY = Math.min(...cards.map((c) => c.y));
		const normalized = cards.map((c) => ({ ...c, y: c.y - minY }));
		return { section, cards: normalized };
	}).filter((g): g is { section: typeof SECTIONS[0]; cards: typeof placed } => g !== null);

	return (
		<>
			{isError && (
				<div className="border-b bg-destructive/10 px-4 py-2 text-xs text-destructive">
					백엔드 응답 오류: {String((error as Error)?.message || 'unknown')} — 서버 재시작 필요할 수 있음
				</div>
			)}

			{placed.length === 0 ? (
				isLoading ? (
					<div className="flex items-center justify-center p-16 text-muted-foreground">
						<Loader2 className="size-6 animate-spin" />
					</div>
				) : (
					<div className="p-8 text-center text-sm text-muted-foreground">
						이 카테고리의 카드가 아직 없습니다.
					</div>
				)
			) : (
				<div className="flex flex-col">
					{grouped.map(({ section, cards }, idx) => (
						<section key={section.title} className={idx === 0 ? '' : 'mt-2'}>
							<header className="flex items-baseline justify-between gap-3 px-6 pt-4 pb-1">
								<div className="flex items-baseline gap-3">
									<span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground/70">
										{String(idx + 1).padStart(2, '0')}
									</span>
									<h2 className="text-[15px] font-semibold tracking-tight text-foreground">
										{section.title}
									</h2>
									<span className="text-[11px] text-muted-foreground">{section.subtitle}</span>
								</div>
								<div aria-hidden className="hidden flex-1 self-center border-t border-border/40 lg:block" />
							</header>
							<BentoGrid placed={cards} renderCard={renderCard} />
						</section>
					))}
				</div>
			)}
		</>
	);
}
