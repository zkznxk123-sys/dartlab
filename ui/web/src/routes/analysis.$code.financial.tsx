// /analysis/$code/financial — 재무제표분석.
// 7 분석 방법론 sub view (story/dupont/value/growth/credit/quality/snowflake).
// 같은 회사를 그레이엄·린치·S&P·Sloan 등 다른 학파 시각으로 다르게 본다.
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

type SubView = FinancialSubCategory;

// 7 분석 방법론 view.
const VALID_VIEWS: SubView[] = [
	'story',
	'dupont',
	'value',
	'growth',
	'credit',
	'quality',
	'snowflake',
];

// 옛 sub view URL → 7 방법론 자동 redirect.
const LEGACY_REDIRECT: Record<string, SubView> = {
	overview: 'snowflake',
	performance: 'dupont',
	capitalStructure: 'credit',
	cashflow: 'quality',
	risk: 'credit',
	profitability: 'dupont',
	// growth 는 옛에도 새에도 있음 — 새 의미 (성장투자) 그대로.
};

const SUB_TITLES: Record<SubView, string> = {
	story: 'Story 서사 (6 막 인과)',
	dupont: 'DuPont 분해 (ROE 원천)',
	value: 'Value 가치투자 (Graham·Buffett·Damodaran)',
	growth: 'Growth 성장투자 (Lynch·Fisher)',
	credit: 'Credit 신용분석 (Altman·이자보상·만기)',
	quality: 'Quality 이익품질 (Beneish·Sloan·CF·NI)',
	snowflake: 'Snowflake 종합 (Simply Wall St 5 차원)',
	// legacy — validateSearch 가 redirect 하므로 노출 안 됨.
	performance: 'DuPont 분해 (ROE 원천)',
	capitalStructure: 'Credit 신용분석 (Altman·이자보상·만기)',
	cashflow: 'Quality 이익품질 (Beneish·Sloan·CF·NI)',
	risk: 'Credit 신용분석 (Altman·이자보상·만기)',
	profitability: 'DuPont 분해 (ROE 원천)',
};

export const Route = createFileRoute('/analysis/$code/financial')({
	component: FinancialTab,
	validateSearch: (search: Record<string, unknown>): { view: SubView } => {
		const raw = String(search.view ?? '');
		const redirected = LEGACY_REDIRECT[raw] ?? raw;
		const view = (VALID_VIEWS as string[]).includes(redirected)
			? (redirected as SubView)
			: 'snowflake';
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

	// 7 방법론 모두 sub 단위 query.
	const apiView = view;
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
		// cellHeight === cellWidth 라 카드 실제 px = w*cellSize + (w-1)*gap.
		// 헤더 24 + 푸터 + padding 빼고 차트 영역 채움.
		const footerHeight = hasFooter ? 24 + Math.min(seriesCount, 12) * 16 + 16 : 0;
		const total = p.h * cellSize + (p.h - 1) * 8;
		const bodyHeight = Math.max(60, total - 28 - footerHeight - 4);
		return (
			<CardShell
				title={title}
				help={help}
				colSpan={p.w}
				rowSpan={p.h}
				footer={footer}
			>
				{spec && !spec.error ? <VizChart spec={spec} height={bodyHeight} size={{ w: p.w, h: p.h }} /> : <ChartLoading />}
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
				재무제표분석 / <span className="font-medium text-foreground">{SUB_TITLES[view]}</span>
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
