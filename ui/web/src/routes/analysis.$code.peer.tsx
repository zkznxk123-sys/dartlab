// /analysis/$code/peer — 동종비교 탭.
import { createFileRoute, getRouteApi } from '@tanstack/react-router';

import { TabDashboard } from '@/features/dashboard/layout/TabDashboard';

export const Route = createFileRoute('/analysis/$code/peer')({
	component: PeerTab,
});

const parentRoute = getRouteApi('/analysis/$code');

function PeerTab() {
	const { code } = Route.useParams();
	const { period: periodKind } = parentRoute.useSearch();
	return <TabDashboard tab="peer" code={code} periodKind={periodKind} titlePrefix="동종비교" />;
}
