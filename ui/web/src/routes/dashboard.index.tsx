// /dashboard 의 기본 화면 = 재무제표 (placeholder).
import { createFileRoute } from '@tanstack/react-router';
import { Card, CardDescription, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

export const Route = createFileRoute('/dashboard/')({
	component: FinancialPage,
});

function FinancialPage() {
	return (
		<div className="flex flex-1 flex-col gap-4 p-4 pt-4">
			<Card>
				<CardHeader>
					<CardTitle>재무제표</CardTitle>
					<CardDescription>DART · EDGAR 기반 손익 · 재무상태표 · 현금흐름</CardDescription>
				</CardHeader>
				<CardContent className="min-h-[400px]" />
			</Card>
		</div>
	);
}
