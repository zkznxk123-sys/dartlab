// /analysis/$code 부모 layout — CompanyHeader + 8 탭 nav + Outlet.
// periodKind 는 URL search param (?period=annual|quarterly), 기본 quarterly.
// financial 탭은 3-mode periodView (?periodView=annual|quarterlyRaw|quarterlyTtm).
// CompanyHeader 가 financial 탭일 때 3-mode 토글 노출, 다른 탭은 2-mode 유지.

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Outlet, createFileRoute, useLocation, useNavigate } from '@tanstack/react-router';

import { CompanyHeader } from '@/features/dashboard/layout/CompanyHeader';
import { fetchCompanyMeta, type PeriodKind } from '@/features/dashboard/api/client';
import { dashKeys } from '@/features/dashboard/api/queryKeys';
import { useRecentCompanies } from '@/features/dashboard/hooks/useRecentCompanies';
import { useFinancialView, type PeriodView } from '@/features/dashboard/store/financialView';

interface SearchParams {
	period: PeriodKind;
	periodView?: PeriodView;
}

const _PERIOD_VIEW_VALID = new Set<string>(['annual', 'quarterlyRaw', 'quarterlyTtm']);

export const Route = createFileRoute('/analysis/$code')({
	validateSearch: (search: Record<string, unknown>): SearchParams => {
		const pv = typeof search.periodView === 'string' && _PERIOD_VIEW_VALID.has(search.periodView) ? (search.periodView as PeriodView) : undefined;
		return {
			period: search.period === 'annual' ? 'annual' : 'quarterly',
			...(pv ? { periodView: pv } : {}),
		};
	},
	component: AnalysisLayout,
});

function AnalysisLayout() {
	const { code } = Route.useParams();
	const search = Route.useSearch();
	const navigate = useNavigate();
	const location = useLocation();
	const { push } = useRecentCompanies();
	const [periodKind, setPeriodKind] = useState<PeriodKind>(search.period);
	const [periodView, setPeriodView] = useState<PeriodView>(search.periodView ?? 'quarterlyTtm');
	const ttmAvail = useFinancialView((s) => s.ttmAvail);
	const setTtmAvail = useFinancialView((s) => s.setTtmAvail);
	const isViewerTab = location.pathname.endsWith('/viewer');
	const isTerminalTab = location.pathname.endsWith('/terminal');
	const isFinancialTab = location.pathname.endsWith('/financial');
	const isTerminalSurface = location.pathname === `/analysis/${code}` || location.pathname === `/analysis/${code}/` || isTerminalTab;
	const isEmbeddedViewer =
		isViewerTab && typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('terminalEmbed') === '1';

	// URL 과 state 동기화 — financial 탭에서 periodView 도 URL 에 동기 (bookmark).
	useEffect(() => {
		const needSync = isFinancialTab
			? search.periodView !== periodView || search.period !== periodKind
			: search.period !== periodKind;
		if (needSync) {
			navigate({
				to: '.',
				search: () => (isFinancialTab ? { period: periodKind, periodView } : { period: periodKind }),
				replace: true,
			});
		}
	}, [periodKind, periodView, search.period, search.periodView, isFinancialTab, navigate]);

	// 탭 전환 시 ttmAvail reset — financial 외 탭에선 의미 없음.
	useEffect(() => {
		if (!isFinancialTab) setTtmAvail(null);
	}, [isFinancialTab, setTtmAvail]);

	// 회사명 — kindlist parquet 단일 룩업 (0~5ms). CompanyHeader 도 같은 queryKey
	// 라 React Query 가 자동 dedup → 회사 진입 시 meta 호출 1 회. 이전엔 dashboard
	// 전체 (FINANCE_DASHBOARD_KEYS × nPeriods=40) 빌드해서 corpName 한 글자만
	// 뽑던 회귀 (P-DASH-V2).
	const { data: meta } = useQuery({
		queryKey: dashKeys.companyMeta(code),
		queryFn: () => fetchCompanyMeta(code),
		staleTime: 10 * 60_000,
	});
	const corpName = meta?.corpName;

	useEffect(() => {
		if (corpName && code) push(code, corpName);
	}, [code, corpName, push]);

	// sticky CompanyHeader + 자식 scroll area. 부모 flex-1 이지만 min-h-0 박아야
	// 자식 overflow 가 동작. 헤더는 sticky top-0 + bg/blur 로 카드 위에 떠 있음.
	if (isTerminalSurface || isEmbeddedViewer) return <Outlet />;

	return (
		<div className="flex min-h-0 flex-1 flex-col">
			<div className="sticky top-0 z-20 border-b border-border/60 bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/65">
				<CompanyHeader
					stockCode={code}
					corpName={corpName}
					periodKind={periodKind}
					onPeriodKindChange={setPeriodKind}
					periodView={periodView}
					onPeriodViewChange={setPeriodView}
					showPeriodView={isFinancialTab}
					ttmAvail={isFinancialTab ? ttmAvail : null}
					hidePeriodToggle={isViewerTab || isTerminalTab}
				/>
			</div>
			{/* viewer/terminal 탭은 own scroll container — 부모는
			   overflow-hidden 으로 outer scroll 흡수 차단. 그 외 탭 (financial/quant/index) 은
			   기존 outer scroll 유지. */}
			<div className={isViewerTab || isTerminalTab ? 'min-h-0 flex-1 overflow-hidden' : 'min-h-0 flex-1 overflow-y-auto tiny-scroll'}>
				<Outlet />
			</div>
		</div>
	);
}
