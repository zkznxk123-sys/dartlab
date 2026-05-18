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
import {
	BentoGrid,
	BENTO_GAP_PX,
	BENTO_CARD_HEADER_PX,
	BENTO_CARD_PAD_PX,
} from '@/features/dashboard/layout/BentoGrid';
import {
	fetchCatalog,
	fetchTabLayout,
	type CatalogCard,
	type FinancialSubCategory,
	type PackedCard,
} from '@/features/dashboard/api/client';
import { dashKeys } from '@/features/dashboard/api/queryKeys';

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

function FinancialTab() {
	const { code } = Route.useParams();
	const { period: periodKind } = parentRoute.useSearch();

	const { data: catalog } = useQuery({
		queryKey: dashKeys.catalog(),
		queryFn: fetchCatalog,
		staleTime: Infinity,
	});

	// v3-r6 — sub view 폐기. view 항상 null → backend OVERVIEW_KEYS curated.
	const apiView = null;
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
		// 자산구조 dual-stack 은 9 series 박혀있어 mini-table 의미 0 + 운영자 명시 (2026-05-18) 제거.
		const isDualStack = spec?.options?.dualStack === true;
		const hasFooter = !!(spec && spec.kind === 'trend' && seriesCount > 0 && !isDualStack);
		const footer = hasFooter ? <ChartMiniTable spec={spec} /> : undefined;
		// v3-r6 — TabDashboard 와 동일 산출식 (BentoGrid 상수 SSOT).
		// footerH = thead 20 + N rows × 20 + py 8 + border 1.
		const footerHeight = hasFooter ? 20 * Math.min(seriesCount, 12) + 20 + 8 + 1 : 0;
		const cardOuterH = p.h * cellSize + (p.h - 1) * BENTO_GAP_PX;
		const bodyHeight = Math.max(60, cardOuterH - BENTO_CARD_HEADER_PX - BENTO_CARD_PAD_PX - footerHeight);
		const kind = spec?.kind ?? p.kind;
		return (
			<CardShell
				title={title}
				help={help}
				colSpan={p.w}
				rowSpan={p.h}
				kind={kind}
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
				재무제표분석 / <span className="font-medium text-foreground">재무분석 (자산구조·부채상세·자본상세·손익구조)</span>
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
