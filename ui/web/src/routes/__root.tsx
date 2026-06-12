// 모든 라우트 공통 — SidebarProvider + AppSidebar + SidebarInset(헤더 + Outlet).
import { createRootRouteWithContext, Outlet, useLocation } from '@tanstack/react-router';
import type { QueryClient } from '@tanstack/react-query';

import { AppSidebar } from '@/shell/AppSidebar';
import { SiteHeader } from '@/shell/SiteHeader';
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar';

interface RouterContext {
	queryClient: QueryClient;
}

export const Route = createRootRouteWithContext<RouterContext>()({
	component: RootLayout,
});

function RootLayout() {
	const location = useLocation();
	const search = location.search as Record<string, unknown>;
	const terminalSurface = /^\/analysis\/[^/]+\/?$/.test(location.pathname) || /^\/analysis\/[^/]+\/terminal\/?$/.test(location.pathname);
	const embeddedViewer = /^\/analysis\/[^/]+\/viewer\/?$/.test(location.pathname) && search.terminalEmbed === '1';

	if (terminalSurface || embeddedViewer) return <Outlet />;

	return (
		<SidebarProvider>
			<AppSidebar />
			<SidebarInset className="h-svh">
				<SiteHeader />
				<Outlet />
			</SidebarInset>
		</SidebarProvider>
	);
}
