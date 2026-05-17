// 탭 공용 대시보드 — catalog 의 카드 entry 가 KPI/Sankey/Gauge 등 다양한 kind 로 미리 정의됨.
// 페이지는 단순히 catalog 순서로 xlSpan 존중하며 그리드 배치 — KPI 자동 추출 없음.

import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';

import { CardShell } from '@/features/dashboard/cards/CardShell';
import { ChartMiniTable } from '@/features/dashboard/cards/ChartMiniTable';
import { VizChart } from '@/features/dashboard/charts/VizChart';
import { CardGrid } from '@/features/dashboard/layout/CardGrid';
import {
	fetchCatalog,
	fetchTabDashboard,
	type AnalysisTab,
	type CatalogCard,
	type PeriodKind,
} from '@/features/dashboard/api/client';
import { dashKeys } from '@/features/dashboard/api/queryKeys';

function ChartLoading() {
	return (
		<div className="flex h-[180px] w-full items-center justify-center text-muted-foreground">
			<Loader2 className="size-5 animate-spin" />
		</div>
	);
}

// 카드 종류별 default colSpan/rowSpan — entry.layout 으로 override.
// 4 col grid + 110 px row 기준. (P-NEXT-2 표 참조.)
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

function resolveLayout(
	specLayout: { colSpan?: 1 | 2 | 3 | 4; rowSpan?: 1 | 2 | 3 | 4 | 5 | 6 } | undefined,
	kind: string | undefined,
	xlSpan: 1 | 2 | 3,
): { colSpan: 1 | 2 | 3 | 4; rowSpan: 1 | 2 | 3 | 4 | 5 | 6 } {
	const fallback = DEFAULT_LAYOUT[kind ?? 'trend'] ?? { colSpan: xlSpan as 1 | 2 | 3 | 4, rowSpan: 2 };
	return {
		colSpan: specLayout?.colSpan ?? fallback.colSpan,
		rowSpan: specLayout?.rowSpan ?? fallback.rowSpan,
	};
}

interface Props {
	tab: AnalysisTab;
	code: string;
	periodKind: PeriodKind;
	titlePrefix?: string;
}

export function TabDashboard({ tab, code, periodKind, titlePrefix }: Props) {
	const { data: catalog } = useQuery({
		queryKey: dashKeys.catalog(),
		queryFn: fetchCatalog,
		staleTime: Infinity,
	});

	const { data, isError, error } = useQuery({
		queryKey: dashKeys.tabDashboard(tab, code, periodKind),
		queryFn: () => fetchTabDashboard(tab, code, periodKind, 40),
		placeholderData: keepPreviousData,
		staleTime: 5 * 60_000,
		retry: 1,
	});

	const cardMetaByKey: Record<string, CatalogCard | undefined> = Object.fromEntries(
		(catalog?.cards ?? []).map((c) => [c.cardKey, c]),
	);
	const orderedKeys: string[] = data?.order ?? [];

	const renderCard = (cardKey: string) => {
		const meta = cardMetaByKey[cardKey];
		const spec = data?.cards?.[cardKey];
		const title = meta?.title ?? spec?.title ?? cardKey;
		const help = meta?.help;
		const xlSpan = meta?.xlSpan ?? 1;
		const kind = spec?.kind ?? meta?.kind;
		const layout = resolveLayout(spec?.layout, kind, xlSpan);
		// trend 모든 카드는 mini-table footer 표시 — 차트 ↔ 표 단위·라벨·색 매칭.
		const seriesCount = spec?.series?.length ?? 0;
		const hasFooter = !!(spec && spec.kind === 'trend' && seriesCount > 0);
		const footer = hasFooter ? <ChartMiniTable spec={spec} /> : undefined;
		// footer 높이 ≈ header(28) + row(18) × seriesCount + padding(20).
		const footerHeight = hasFooter ? 28 + Math.min(seriesCount, 12) * 18 + 20 : 0;
		const total = layout.rowSpan * 150 + (layout.rowSpan - 1) * 12;
		const h = Math.max(80, total - 44 - footerHeight - 12);
		return (
			<CardShell
				key={cardKey}
				title={title}
				help={help}
				colSpan={layout.colSpan}
				rowSpan={layout.rowSpan}
				footer={footer}
			>
				{spec && !spec.error ? <VizChart spec={spec} height={h} /> : <ChartLoading />}
			</CardShell>
		);
	};

	return (
		<div className="flex flex-1 flex-col gap-3 p-3">
			{titlePrefix && (
				<div className="border-b bg-card/30 px-2 py-1.5 text-xs text-muted-foreground">
					{titlePrefix}
				</div>
			)}
			{isError && (
				<div className="rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">
					백엔드 응답 오류: {String((error as Error)?.message || 'unknown')}
				</div>
			)}
			{orderedKeys.length === 0 ? (
				<div className="rounded-md border border-dashed p-8 text-center text-sm text-muted-foreground">
					이 탭의 카드가 아직 없습니다.
				</div>
			) : (
				<CardGrid>{orderedKeys.map((k) => renderCard(k))}</CardGrid>
			)}
		</div>
	);
}
