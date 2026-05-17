// /analysis/$code/portfolio — 사업포트폴리오 탭.
import { createFileRoute, getRouteApi } from '@tanstack/react-router';

import { TabDashboard } from '@/features/dashboard/layout/TabDashboard';

export const Route = createFileRoute('/analysis/$code/portfolio')({
	component: PortfolioTab,
});

const parentRoute = getRouteApi('/analysis/$code');

function PortfolioTab() {
	const { code } = Route.useParams();
	const { period: periodKind } = parentRoute.useSearch();
	return <TabDashboard tab="portfolio" code={code} periodKind={periodKind} titlePrefix="사업포트폴리오" />;
}
