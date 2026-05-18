// /analysis/$code/ → /analysis/$code/financial?view=snowflake (종합 첫 진입).
import { createFileRoute, redirect } from '@tanstack/react-router';

export const Route = createFileRoute('/analysis/$code/')({
	beforeLoad: ({ params }) => {
		throw redirect({
			to: '/analysis/$code/financial',
			params: { code: params.code },
			search: { period: 'quarterly', view: 'snowflake' },
			replace: true,
		});
	},
});
