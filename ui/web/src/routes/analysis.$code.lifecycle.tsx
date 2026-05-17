// /analysis/$code/lifecycle — 생애주기·시나리오 탭.
import { createFileRoute, getRouteApi } from '@tanstack/react-router';

import { TabDashboard } from '@/features/dashboard/layout/TabDashboard';

export const Route = createFileRoute('/analysis/$code/lifecycle')({
	component: LifecycleTab,
});

const parentRoute = getRouteApi('/analysis/$code');

function LifecycleTab() {
	const { code } = Route.useParams();
	const { period: periodKind } = parentRoute.useSearch();
	return <TabDashboard tab="lifecycle" code={code} periodKind={periodKind} titlePrefix="생애주기·시나리오" />;
}
