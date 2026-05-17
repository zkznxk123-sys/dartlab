// /analysis/$code/financial — 재무 탭.
// 5 서브카테고리: growth · profitability · capitalStructure · cashflow · risk.
// catalog 의 subCategory 필드로 카드 자동 분류. URL ?view=<sub> 로 핀.

import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { createFileRoute, getRouteApi } from '@tanstack/react-router';
import { Loader2 } from 'lucide-react';

import { CardShell } from '@/features/dashboard/cards/CardShell';
import { ChartMiniTable } from '@/features/dashboard/cards/ChartMiniTable';
import { VizChart } from '@/features/dashboard/charts/VizChart';
import { BentoGrid } from '@/features/dashboard/layout/BentoGrid';
import {
	fetchCatalog,
	fetchTabLayout,
	type CatalogCard,
	type FinancialSubCategory,
	type PackedCard,
} from '@/features/dashboard/api/client';
import { dashKeys } from '@/features/dashboard/api/queryKeys';

type SubView = FinancialSubCategory | 'overview';

// P-DASH-V1 D7: 4 sub + overview. growth/profitability → performance 통합.
const VALID_VIEWS: SubView[] = [
	'overview',
	'performance',
	'capitalStructure',
	'cashflow',
	'risk',
];

// legacy growth/profitability → performance 자동 redirect (URL 호환).
const LEGACY_REDIRECT: Record<string, SubView> = {
	growth: 'performance',
	profitability: 'performance',
};

const SUB_TITLES: Record<SubView, string> = {
	overview: '전체',
	performance: '성과 (수익성·성장)',
	capitalStructure: '재무건전성',
	cashflow: '현금·배분',
	risk: '리스크·신호',
	// legacy 호환 — validateSearch 가 redirect 하므로 실제 노출은 없음.
	growth: '성과 (수익성·성장)',
	profitability: '성과 (수익성·성장)',
};

export const Route = createFileRoute('/analysis/$code/financial')({
	component: FinancialTab,
	validateSearch: (search: Record<string, unknown>): { view: SubView } => {
		const raw = String(search.view ?? '');
		const redirected = LEGACY_REDIRECT[raw] ?? raw;
		const view = (VALID_VIEWS as string[]).includes(redirected)
			? (redirected as SubView)
			: 'overview';
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

	// view='overview' 는 sub 무관 전체 → null 전달. 외 sub 만 layout query.
	const apiView = view === 'overview' ? null : view;
	const { data, isError, error } = useQuery({
		queryKey: dashKeys.tabLayout('financial', code, apiView, periodKind),
		queryFn: () => fetchTabLayout('financial', code, apiView, periodKind, 40),
		placeholderData: keepPreviousData,
		staleTime: 5 * 60_000,
		retry: 1,
	});

	const cardMetaByKey: Record<string, CatalogCard | undefined> = Object.fromEntries(
		(catalog?.cards ?? []).map((c) => [c.cardKey, c]),
	);

	const renderCard = (p: PackedCard, cellSize: number) => {
		const meta = cardMetaByKey[p.cardKey];
		const spec = data?.cards?.[p.cardKey];
		const title = meta?.title || spec?.title || p.title;
		const help = meta?.help;
		const seriesCount = spec?.series?.length ?? 0;
		const hasFooter = !!(spec && spec.kind === 'trend' && seriesCount > 0);
		const footer = hasFooter ? <ChartMiniTable spec={spec} /> : undefined;
		const footerHeight = hasFooter ? 28 + Math.min(seriesCount, 12) * 18 + 20 : 0;
		const total = p.h * cellSize + (p.h - 1) * 12;
		const bodyHeight = Math.max(80, total - 44 - footerHeight - 12);
		return (
			<CardShell
				title={title}
				help={help}
				colSpan={p.w as 1 | 2 | 3 | 4}
				rowSpan={p.h as 1 | 2 | 3 | 4 | 5 | 6}
				footer={footer}
				className="h-full"
			>
				{spec && !spec.error ? <VizChart spec={spec} height={bodyHeight} /> : <ChartLoading />}
			</CardShell>
		);
	};

	const placed = data?.layout ?? [];

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

			{placed.length === 0 ? (
				<div className="p-8 text-center text-sm text-muted-foreground">
					이 카테고리의 카드가 아직 없습니다.
				</div>
			) : (
				<BentoGrid placed={placed} renderCard={renderCard} />
			)}
		</>
	);
}
