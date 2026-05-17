// /analysis/$code/macro — 거시·섹터 탭.
import { createFileRoute, getRouteApi } from '@tanstack/react-router';

import { TabDashboard } from '@/features/dashboard/layout/TabDashboard';

export const Route = createFileRoute('/analysis/$code/macro')({
	component: MacroTab,
});

const parentRoute = getRouteApi('/analysis/$code');

function MacroTab() {
	const { code } = Route.useParams();
	const { period: periodKind } = parentRoute.useSearch();
	return <TabDashboard tab="macro" code={code} periodKind={periodKind} titlePrefix="거시·섹터" />;
}
