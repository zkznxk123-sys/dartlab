import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider, createRouter } from '@tanstack/react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { ThemeProvider } from '@/shell/ThemeProvider';
import { TooltipProvider } from '@/components/ui/tooltip';
import { routeTree } from './routeTree.gen';
import './styles/index.css';

const queryClient = new QueryClient({
	defaultOptions: {
		queries: {
			staleTime: 60_000,
			refetchOnWindowFocus: false,
		},
	},
});

const router = createRouter({
	routeTree,
	context: { queryClient },
	defaultPreload: 'intent',
});

declare module '@tanstack/react-router' {
	interface Register {
		router: typeof router;
	}
}

const rootEl = document.getElementById('root');
if (!rootEl) throw new Error('#root element missing in index.html');

createRoot(rootEl).render(
	<StrictMode>
		<ThemeProvider defaultTheme="system" storageKey="dartlab-ui-theme">
			<QueryClientProvider client={queryClient}>
				<TooltipProvider>
					<RouterProvider router={router} />
				</TooltipProvider>
			</QueryClientProvider>
		</ThemeProvider>
	</StrictMode>,
);
