import { useEffect } from 'react';
import { createFileRoute } from '@tanstack/react-router';

import { LandingTerminalSurface } from '@/features/terminalSvelte/LandingTerminalSurface';
import { useDashboardMode } from '@/features/dashboard/store/dashboardMode';

export const Route = createFileRoute('/analysis/$code/terminal')({
	component: TerminalRoute,
	validateSearch: (search: Record<string, unknown>) => ({
		period: search.period === 'annual' ? ('annual' as const) : ('quarterly' as const),
	}),
});

function TerminalRoute() {
	const { code } = Route.useParams();
	const setLastMode = useDashboardMode((s) => s.setLastMode);

	useEffect(() => {
		setLastMode('terminal');
	}, [setLastMode]);

	return <LandingTerminalSurface code={code} />;
}
