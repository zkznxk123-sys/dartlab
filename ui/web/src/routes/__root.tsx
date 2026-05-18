// 모든 라우트 공통 — SidebarProvider + AppSidebar + SidebarInset(헤더 + Outlet).
import { createRootRouteWithContext, Outlet } from '@tanstack/react-router';
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
