// /analysis/$code/valuation — 가치평가 탭.
import { createFileRoute, getRouteApi } from '@tanstack/react-router';

import { TabDashboard } from '@/features/dashboard/layout/TabDashboard';

export const Route = createFileRoute('/analysis/$code/valuation')({
	component: ValuationTab,
});

const parentRoute = getRouteApi('/analysis/$code');

function ValuationTab() {
	const { code } = Route.useParams();
	const { period: periodKind } = parentRoute.useSearch();
	return <TabDashboard tab="valuation" code={code} periodKind={periodKind} titlePrefix="가치평가" />;
}
