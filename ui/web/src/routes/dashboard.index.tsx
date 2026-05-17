// /dashboard → /analysis 호환 redirect. picker 는 analysis.index 로 통일.
import { createFileRoute, redirect } from '@tanstack/react-router';

export const Route = createFileRoute('/dashboard/')({
	beforeLoad: () => {
		throw redirect({ to: '/analysis', replace: true });
	},
});
