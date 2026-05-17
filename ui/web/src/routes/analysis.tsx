// /analysis 부모 라우트 — Outlet 만 (UI 는 자식 layout 이 담당).
import { createFileRoute, Outlet } from '@tanstack/react-router';

export const Route = createFileRoute('/analysis')({
	component: () => <Outlet />,
});
