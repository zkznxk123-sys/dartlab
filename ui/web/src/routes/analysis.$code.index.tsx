// /analysis/$code/ → /analysis/$code/financial (자동 리다이렉트).
import { createFileRoute, redirect } from '@tanstack/react-router';

export const Route = createFileRoute('/analysis/$code/')({
	beforeLoad: ({ params }) => {
		throw redirect({
			to: '/analysis/$code/financial',
			params: { code: params.code },
			search: { period: 'quarterly', view: 'overview' },
			replace: true,
		});
	},
});
