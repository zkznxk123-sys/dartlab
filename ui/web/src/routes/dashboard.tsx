// Dashboard 라우트 — layout, 자식 outlet.
import { createFileRoute, Outlet } from '@tanstack/react-router';

export const Route = createFileRoute('/dashboard')({
	component: () => <Outlet />,
});
