// /dashboard/$code → /analysis/$code/financial 호환 redirect.
// 기존 북마크·블로그 링크 호환용. 이름이 "dashboard" 였던 자산은 모두 "analysis" 트리로 이전됨.
import { createFileRoute, redirect } from '@tanstack/react-router';

export const Route = createFileRoute('/dashboard/$code')({
	beforeLoad: ({ params }) => {
		throw redirect({
			to: '/analysis/$code/financial',
			params: { code: params.code },
			search: { period: 'quarterly', view: 'snowflake' },
			replace: true,
		});
	},
});
