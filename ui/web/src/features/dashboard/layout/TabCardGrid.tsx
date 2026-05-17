// 8 탭 공용 카드 그리드 — fetchTabDashboard 결과를 받아 VizChart 로 일괄 렌더.
// financial 외 7 탭은 placeholder/proxy 카드라도 동일 layout 으로 통일.

import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';

import { CardShell } from '@/features/dashboard/cards/CardShell';
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
		<div className="flex h-[220px] w-full items-center justify-center text-muted-foreground">
			<Loader2 className="size-5 animate-spin" />
		</div>
	);
}

interface Props {
	tab: AnalysisTab;
	code: string;
	periodKind: PeriodKind;
}

export function TabCardGrid({ tab, code, periodKind }: Props) {
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
		const title = meta?.title || spec?.title || cardKey;
		const help = meta?.help;
		const xlSpan = meta?.xlSpan ?? 1;
		return (
			<CardShell key={cardKey} title={title} help={help} xlSpan={xlSpan}>
				{spec && !spec.error ? <VizChart spec={spec} height={220} /> : <ChartLoading />}
			</CardShell>
		);
	};

	return (
		<>
			{isError && (
				<div className="border-b bg-destructive/10 px-4 py-2 text-xs text-destructive">
					백엔드 응답 오류: {String((error as Error)?.message || 'unknown')}
				</div>
			)}
			{orderedKeys.length === 0 ? (
				<div className="p-8 text-center text-sm text-muted-foreground">
					이 탭의 카드가 아직 없습니다.
				</div>
			) : (
				<CardGrid>{orderedKeys.map((k) => renderCard(k))}</CardGrid>
			)}
		</>
	);
}
