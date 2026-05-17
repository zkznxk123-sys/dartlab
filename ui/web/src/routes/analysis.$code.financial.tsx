// /analysis/$code/financial — 재무 탭.
// 5 서브카테고리: growth · profitability · capitalStructure · cashflow · risk.
// catalog 의 subCategory 필드로 카드 자동 분류. URL ?view=<sub> 로 핀.

import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { createFileRoute, getRouteApi } from '@tanstack/react-router';
import { Loader2 } from 'lucide-react';

import { CardShell } from '@/features/dashboard/cards/CardShell';
import { ChartMiniTable } from '@/features/dashboard/cards/ChartMiniTable';
import { VizChart } from '@/features/dashboard/charts/VizChart';
import { CardGrid } from '@/features/dashboard/layout/CardGrid';
import { fetchCatalog, fetchDashboard, type CatalogCard, type FinancialSubCategory } from '@/features/dashboard/api/client';
import { dashKeys } from '@/features/dashboard/api/queryKeys';

type SubView = FinancialSubCategory | 'overview';

const VALID_VIEWS: SubView[] = [
	'overview',
	'growth',
	'profitability',
	'capitalStructure',
	'cashflow',
	'risk',
];

const SUB_TITLES: Record<SubView, string> = {
	overview: '전체',
	growth: '수익·성장',
	profitability: '수익성·효율성',
	capitalStructure: '재무건전성',
	cashflow: '현금·배분',
	risk: '리스크·신호',
};

export const Route = createFileRoute('/analysis/$code/financial')({
	component: FinancialTab,
	validateSearch: (search: Record<string, unknown>): { view: SubView } => {
		const raw = String(search.view ?? '');
		const view = (VALID_VIEWS as string[]).includes(raw) ? (raw as SubView) : 'overview';
		return { view };
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

function FinancialTab() {
	const { code } = Route.useParams();
	const { view } = Route.useSearch();
	const { period: periodKind } = parentRoute.useSearch();

	const { data: catalog } = useQuery({
		queryKey: dashKeys.catalog(),
		queryFn: fetchCatalog,
		staleTime: Infinity,
	});

	const { data, isError, error } = useQuery({
		queryKey: dashKeys.dashboard(code, periodKind),
		queryFn: () => fetchDashboard(code, periodKind, 40),
		placeholderData: keepPreviousData,
		staleTime: 5 * 60_000,
		retry: 1,
	});

	const cardMetaByKey: Record<string, CatalogCard | undefined> = Object.fromEntries(
		(catalog?.cards ?? []).map((c) => [c.cardKey, c]),
	);
	const orderedKeys: string[] = data?.order ?? catalog?.dashboardKeys ?? [];

	// overview = 전체 (catalog 순서 그대로), sub-view = 해당 subCategory 만.
	// bento grid 가 카드별 colSpan/rowSpan 으로 자동 packing — 별도 hero/triplet 하드코딩 폐기.
	const isOverview = view === 'overview';
	const viewKeys = orderedKeys.filter((k) => {
		const meta = cardMetaByKey[k];
		if (isOverview) return true;
		return meta?.tab === 'financial' && meta?.subCategory === view;
	});

	// 4 col grid + 150 px row 기준 default layout.
	const DEFAULT_LAYOUT: Record<string, { colSpan: 1 | 2 | 3 | 4; rowSpan: 1 | 2 | 3 | 4 | 5 | 6 }> = {
		kpiTile: { colSpan: 1, rowSpan: 1 },
		diffView: { colSpan: 1, rowSpan: 1 },
		gauge: { colSpan: 1, rowSpan: 2 },
		phaseIndicator: { colSpan: 2, rowSpan: 1 },
		topList: { colSpan: 1, rowSpan: 3 },
		comparisonTable: { colSpan: 2, rowSpan: 3 },
		radar: { colSpan: 2, rowSpan: 2 },
		scatter: { colSpan: 2, rowSpan: 2 },
		matrix: { colSpan: 2, rowSpan: 2 },
		trend: { colSpan: 2, rowSpan: 2 },
		sankey: { colSpan: 3, rowSpan: 3 },
		breakdown: { colSpan: 1, rowSpan: 2 },
		waterfall: { colSpan: 2, rowSpan: 2 },
	};

	const renderCard = (cardKey: string) => {
		const meta = cardMetaByKey[cardKey];
		const spec = data?.cards?.[cardKey];
		const title = meta?.title || spec?.title || cardKey;
		const help = meta?.help;
		const kind = spec?.kind ?? meta?.kind ?? 'trend';
		const fallback = DEFAULT_LAYOUT[kind] ?? { colSpan: (meta?.xlSpan ?? 1) as 1 | 2 | 3 | 4, rowSpan: 2 };
		const layout = {
			colSpan: spec?.layout?.colSpan ?? fallback.colSpan,
			rowSpan: spec?.layout?.rowSpan ?? fallback.rowSpan,
		};
		const seriesCount = spec?.series?.length ?? 0;
		const hasFooter = !!(spec && spec.kind === 'trend' && seriesCount > 0);
		const footer = hasFooter ? <ChartMiniTable spec={spec} /> : undefined;
		const footerHeight = hasFooter ? 28 + Math.min(seriesCount, 12) * 18 + 20 : 0;
		// rowSpan × 150 (auto-rows) − header − footer − padding.
		const total = layout.rowSpan * 150 + (layout.rowSpan - 1) * 12;
		const bodyHeight = Math.max(80, total - 44 - footerHeight - 12);
		return (
			<CardShell
				key={cardKey}
				title={title}
				help={help}
				colSpan={layout.colSpan}
				rowSpan={layout.rowSpan}
				footer={footer}
			>
				{spec && !spec.error ? <VizChart spec={spec} height={bodyHeight} /> : <ChartLoading />}
			</CardShell>
		);
	};

	return (
		<>
			{isError && (
				<div className="border-b bg-destructive/10 px-4 py-2 text-xs text-destructive">
					백엔드 응답 오류: {String((error as Error)?.message || 'unknown')} — 서버 재시작 필요할 수 있음
				</div>
			)}

			<div className="border-b bg-card/30 px-4 py-2 text-xs text-muted-foreground">
				재무제표 / <span className="font-medium text-foreground">{SUB_TITLES[view]}</span>
			</div>

			{viewKeys.length === 0 ? (
				<div className="p-8 text-center text-sm text-muted-foreground">
					이 카테고리의 카드가 아직 없습니다.
				</div>
			) : (
				<CardGrid>{viewKeys.map((k) => renderCard(k))}</CardGrid>
			)}
		</>
	);
}
