// 회사 헤더 — 종목명·코드·기간 토글 + 섹터·제품·블로그 태그 (C13).
// corpName 은 본 컴포넌트 own meta query 의 SSOT — 부모 layout 도 같은 queryKey 로
// dedup 되어 1 회 호출. fetchDashboard 회귀 차단 (P-DASH-V2).

import { useQuery } from '@tanstack/react-query';
import { BookOpen } from 'lucide-react';

import { Badge } from '@/components/ui/badge';

import { fetchCompanyMeta, type PeriodKind } from '../api/client';
import { dashKeys } from '../api/queryKeys';

interface Props {
	stockCode: string;
	corpName?: string | null;
	periodKind: PeriodKind;
	onPeriodKindChange: (p: PeriodKind) => void;
	hidePeriodToggle?: boolean;
}

export function CompanyHeader({ stockCode, corpName, periodKind, onPeriodKindChange, hidePeriodToggle }: Props) {
	const { data: meta } = useQuery({
		queryKey: dashKeys.companyMeta(stockCode),
		queryFn: () => fetchCompanyMeta(stockCode),
		staleTime: 10 * 60_000,
		retry: 1,
	});
	const displayName = corpName || meta?.corpName || '';

	return (
		<div className="flex items-center justify-between gap-3 px-4 py-3">
			<div className="flex min-w-0 flex-wrap items-baseline gap-2">
				{displayName ? (
					<>
						<h1 className="truncate text-base font-semibold">{displayName}</h1>
						<span className="font-mono text-xs text-muted-foreground">{stockCode}</span>
					</>
				) : (
					<h1 className="truncate font-mono text-base font-semibold">{stockCode}</h1>
				)}
				{meta?.sector && (
					<Badge variant="secondary" className="text-[10px] font-normal">
						{meta.sector}
					</Badge>
				)}
				{(meta?.products ?? []).slice(0, 5).map((p) => (
					<Badge key={p} variant="outline" className="text-[10px] font-normal">
						{p}
					</Badge>
				))}
				{(meta?.blogPosts ?? []).slice(0, 3).map((b) => (
					<a
						key={b.slug}
						href={b.url}
						target="_blank"
						rel="noreferrer noopener"
						className="inline-flex"
					>
						<Badge
							variant="outline"
							className="cursor-pointer gap-1 text-[10px] font-normal hover:bg-accent"
						>
							<BookOpen className="size-2.5" />
							{b.title}
						</Badge>
					</a>
				))}
			</div>
			{!hidePeriodToggle && (
				<div className="flex shrink-0 items-center gap-1 rounded-md border bg-muted/40 p-0.5">
					{(['annual', 'quarterly'] as PeriodKind[]).map((p) => (
						<button
							key={p}
							type="button"
							onClick={() => onPeriodKindChange(p)}
							className={`rounded-sm px-2 py-1 text-xs transition-colors ${
								periodKind === p ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
							}`}
						>
							{p === 'annual' ? '연간' : '분기'}
						</button>
					))}
				</div>
			)}
		</div>
	);
}
