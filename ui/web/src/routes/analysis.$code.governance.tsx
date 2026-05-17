// /analysis/$code/governance — 거버넌스·리스크 탭.
import { createFileRoute, getRouteApi } from '@tanstack/react-router';

import { TabDashboard } from '@/features/dashboard/layout/TabDashboard';

export const Route = createFileRoute('/analysis/$code/governance')({
	component: GovernanceTab,
});

const parentRoute = getRouteApi('/analysis/$code');

function GovernanceTab() {
	const { code } = Route.useParams();
	const { period: periodKind } = parentRoute.useSearch();
	return <TabDashboard tab="governance" code={code} periodKind={periodKind} titlePrefix="거버넌스·리스크" />;
}
