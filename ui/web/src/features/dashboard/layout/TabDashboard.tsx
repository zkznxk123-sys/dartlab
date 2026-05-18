// 탭 공용 대시보드 — backend Layout Engine 이 산출한 packed grid 좌표대로 렌더.
// P-DASH-V1 D17 — fetchTabLayout 로 통일 (BentoGrid).

import { keepPreviousData, useQuery } from '@tanstack/react-query';
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
	type AnalysisTab,
	type CatalogCard,
	type PackedCard,
	type PeriodKind,
} from '@/features/dashboard/api/client';
import { dashKeys } from '@/features/dashboard/api/queryKeys';

function ChartLoading() {
	return (
		<div className="flex h-full w-full items-center justify-center text-muted-foreground">
			<Loader2 className="size-5 animate-spin" />
		</div>
	);
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
		queryKey: dashKeys.tabLayout(tab, code, null, periodKind),
		queryFn: () => fetchTabLayout(tab, code, null, periodKind, 40),
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
		// v3-r5 §8.2 — footerH 단일 식. thead 20 + N rows × 20 + py 8 + border 1.
		const footerHeight = hasFooter ? 20 * Math.min(seriesCount, 12) + 20 + 8 + 1 : 0;
		// BentoGrid 동기 — gap=4 (이전 8 의 magic 폐기). header/pad 도 SSOT 상수.
		const cardOuterH = p.h * cellSize + (p.h - 1) * BENTO_GAP_PX;
		const h = Math.max(60, cardOuterH - BENTO_CARD_HEADER_PX - BENTO_CARD_PAD_PX - footerHeight);
		const kind = spec?.kind ?? p.kind;
		return (
			<CardShell title={title} help={help} colSpan={p.w} rowSpan={p.h} kind={kind} footer={footer}>
				{spec && !spec.error ? <VizChart spec={spec} height={h} size={{ w: p.w, h: p.h }} /> : <ChartLoading />}
			</CardShell>
		);
	};

	const placed = data?.layout ?? [];

	return (
		<div className="flex flex-1 flex-col">
			{titlePrefix && (
				<div className="border-b bg-card/30 px-4 py-2 text-xs text-muted-foreground">
					{titlePrefix}
				</div>
			)}
			{isError && (
				<div className="border-b bg-destructive/10 px-4 py-2 text-xs text-destructive">
					백엔드 응답 오류: {String((error as Error)?.message || 'unknown')}
				</div>
			)}
			{placed.length === 0 ? (
				<div className="m-4 rounded-md border border-dashed p-8 text-center text-sm text-muted-foreground">
					이 탭의 카드가 아직 없습니다.
				</div>
			) : (
				<BentoGrid placed={placed} renderCard={renderCard} />
			)}
		</div>
	);
}
