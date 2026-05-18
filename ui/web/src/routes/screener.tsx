// /screener — 종목 필터·랭킹 도구 placeholder.
// 기업분석과 형제 카테고리 (단일 종목 분석이 아닌, 여러 종목 추리는 도구).
// 실제 로직은 후속 PR — 본 페이지는 안내 카드만.

import { createFileRoute, Link } from '@tanstack/react-router';
import { Filter, Search } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export const Route = createFileRoute('/screener')({
	component: ScreenerPlaceholder,
});

function ScreenerPlaceholder() {
	return (
		<div className="flex flex-1 items-center justify-center p-6">
			<Card className="w-full max-w-lg">
				<CardHeader className="flex flex-row items-center gap-3 pb-3">
					<Filter className="size-6 text-muted-foreground" />
					<CardTitle className="text-lg">스크리너 (준비 중)</CardTitle>
				</CardHeader>
				<CardContent className="space-y-4 text-sm text-muted-foreground">
					<p>
						재무·시장·이벤트 필터로 종목 추리는 도구. 분석 방법론 7 종 (Value /
						Growth / Credit / Quality / Snowflake 등) 별 프리셋 + 사용자 정의
						조건 + 동종 비교 + 랭킹.
					</p>
					<p>지금은 기업분석 (단일 종목 심층) 만 지원. 곧 추가됩니다.</p>
					<Link
						to="/analysis"
						className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs text-foreground hover:bg-accent"
					>
						<Search className="size-3.5" /> 기업분석 — 종목 검색
					</Link>
				</CardContent>
			</Card>
		</div>
	);
}
