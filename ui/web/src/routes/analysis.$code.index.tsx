import { useEffect } from 'react';
import { createFileRoute } from '@tanstack/react-router';

import { LandingTerminalSurface } from '@/features/terminalSvelte/LandingTerminalSurface';
import { useDashboardMode } from '@/features/dashboard/store/dashboardMode';

export const Route = createFileRoute('/analysis/$code/')({
	component: AnalysisTerminalIndex,
	validateSearch: (s: Record<string, unknown>) => ({
		period: s.period === 'annual' ? ('annual' as const) : ('quarterly' as const),
	}),
});

function AnalysisTerminalIndex() {
	const { code } = Route.useParams();
	const setLastMode = useDashboardMode((s) => s.setLastMode);

	useEffect(() => {
		setLastMode('terminal');
	}, [setLastMode]);

	return <LandingTerminalSurface code={code} />;
}
