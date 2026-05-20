// /dashboard/$code → /analysis/$code/ (허브) 호환 redirect.
// 기존 북마크·블로그 링크 호환용. 옛 financial 직접 redirect 는 종목 전환 시
// 무조건 financial 점프 회귀 (사용자가 viewer 보던 중에도) — 허브로 통일.
import { createFileRoute, redirect } from '@tanstack/react-router';

export const Route = createFileRoute('/dashboard/$code')({
	beforeLoad: ({ params }) => {
		throw redirect({
			to: '/analysis/$code',
			params: { code: params.code },
			search: { period: 'quarterly' },
			replace: true,
		});
	},
});
