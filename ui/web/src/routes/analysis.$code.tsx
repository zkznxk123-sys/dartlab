// /analysis/$code 부모 layout — CompanyHeader + 8 탭 nav + Outlet.
// periodKind 는 URL search param (?period=annual|quarterly), 기본 quarterly.
// 자식 라우트는 Route.useSearch() 또는 outlet context 로 받음.

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Outlet, createFileRoute, useNavigate } from '@tanstack/react-router';

import { CompanyHeader } from '@/features/dashboard/layout/CompanyHeader';
import { fetchDashboard, type PeriodKind } from '@/features/dashboard/api/client';
import { dashKeys } from '@/features/dashboard/api/queryKeys';
import { useRecentCompanies } from '@/features/dashboard/hooks/useRecentCompanies';

interface SearchParams {
	period: PeriodKind;
}

export const Route = createFileRoute('/analysis/$code')({
	validateSearch: (search: Record<string, unknown>): SearchParams => ({
		period: search.period === 'annual' ? 'annual' : 'quarterly',
	}),
	component: AnalysisLayout,
});

function AnalysisLayout() {
	const { code } = Route.useParams();
	const search = Route.useSearch();
	const navigate = useNavigate();
	const { push } = useRecentCompanies();
	const [periodKind, setPeriodKind] = useState<PeriodKind>(search.period);

	// URL 과 state 동기화
	useEffect(() => {
		if (search.period !== periodKind) {
			navigate({
				to: '.',
				search: () => ({ period: periodKind }),
				replace: true,
			});
		}
	}, [periodKind, search.period, navigate]);

	// 회사명 가져오기 — financial 탭 데이터에서 meta.corpName 추출 (가벼운 한 번 호출)
	const { data: dash } = useQuery({
		queryKey: dashKeys.dashboard(code, periodKind),
		queryFn: () => fetchDashboard(code, periodKind, 40),
		staleTime: 5 * 60_000,
	});
	const corpName = (dash?.cards?.[dash?.order?.[0] || '']?.meta as { corpName?: string } | undefined)?.corpName;

	useEffect(() => {
		if (corpName && code) push(code, corpName);
	}, [code, corpName, push]);

	return (
		<div className="flex flex-1 flex-col">
			<CompanyHeader
				stockCode={code}
				corpName={corpName}
				periodKind={periodKind}
				onPeriodKindChange={setPeriodKind}
			/>
			<Outlet />
		</div>
	);
}
