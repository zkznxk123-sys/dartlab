// 회사 헤더 — 종목명·코드·기간 토글 + 섹터·제품·블로그 태그 (C13).
// corpName 은 본 컴포넌트 own meta query 의 SSOT — 부모 layout 도 같은 queryKey 로
// dedup 되어 1 회 호출. fetchDashboard 회귀 차단 (P-DASH-V2).
//
// 토글 분기:
//   - showPeriodView=true (financial 탭) → 3-mode [연간 / 분기 / 분기 TTM] + ttmAvail badge
//   - 아니면 2-mode [연간 / 분기]
//   - hidePeriodToggle (viewer 등) → 둘 다 hide

import { useQuery } from '@tanstack/react-query';
import { BookOpen } from 'lucide-react';

import { Badge } from '@/components/ui/badge';

import { fetchCompanyMeta, type PeriodKind } from '../api/client';
import { dashKeys } from '../api/queryKeys';

export type PeriodView = 'annual' | 'quarterlyRaw' | 'quarterlyTtm';

export interface TtmAvailability {
	annualFyYears: number;
	quarterlyPeriods: number;
	ttmFullCount: number;
	ttmFallbackCount: number;
	sufficient: boolean;
}

const PERIOD_VIEW_OPTIONS: { value: PeriodView; label: string }[] = [
	{ value: 'annual', label: '연간' },
	{ value: 'quarterlyRaw', label: '분기' },
	{ value: 'quarterlyTtm', label: '분기 TTM' },
];

interface Props {
	stockCode: string;
	corpName?: string | null;
	periodKind: PeriodKind;
	onPeriodKindChange: (p: PeriodKind) => void;
	periodView?: PeriodView;
	onPeriodViewChange?: (v: PeriodView) => void;
	showPeriodView?: boolean;
	ttmAvail?: TtmAvailability | null;
	hidePeriodToggle?: boolean;
}

export function CompanyHeader({
	stockCode,
	corpName,
	periodKind,
	onPeriodKindChange,
	periodView,
	onPeriodViewChange,
	showPeriodView,
	ttmAvail,
	hidePeriodToggle,
}: Props) {
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
				<div className="flex shrink-0 items-center gap-2">
					{showPeriodView && periodView && onPeriodViewChange ? (
						<>
							{/* TTM 가용성 badge — 분기 TTM 모드일 때만 + 부족 / 일부 fallback 일 때. */}
							{periodView === 'quarterlyTtm' && ttmAvail && !ttmAvail.sufficient && (
								<span
									className="rounded-sm bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-medium text-amber-600 dark:text-amber-400"
									title={`TTM 가용 부족 — FY ${ttmAvail.annualFyYears}년, fallback ${ttmAvail.ttmFallbackCount}분기.`}
								>
									TTM 부족
								</span>
							)}
							{periodView === 'quarterlyTtm' && ttmAvail && ttmAvail.sufficient && ttmAvail.ttmFallbackCount > 0 && (
								<span
									className="rounded-sm bg-sky-500/15 px-1.5 py-0.5 text-[10px] font-medium text-sky-600 dark:text-sky-400"
									title={`TTM 일부 annualize — full ${ttmAvail.ttmFullCount}분기 + fallback ${ttmAvail.ttmFallbackCount}분기.`}
								>
									일부 annualize
								</span>
							)}
							<div className="inline-flex items-center gap-1 rounded-md border bg-muted/40 p-0.5">
								{PERIOD_VIEW_OPTIONS.map((opt) => (
									<button
										key={opt.value}
										type="button"
										onClick={() => onPeriodViewChange(opt.value)}
										className={`rounded-sm px-2 py-1 text-xs transition-colors ${
											periodView === opt.value
												? 'bg-background text-foreground shadow-sm'
												: 'text-muted-foreground hover:text-foreground'
										}`}
									>
										{opt.label}
									</button>
								))}
							</div>
						</>
					) : (
						<div className="inline-flex items-center gap-1 rounded-md border bg-muted/40 p-0.5">
							{(['annual', 'quarterly'] as PeriodKind[]).map((p) => (
								<button
									key={p}
									type="button"
									onClick={() => onPeriodKindChange(p)}
									className={`rounded-sm px-2 py-1 text-xs transition-colors ${
										periodKind === p
											? 'bg-background text-foreground shadow-sm'
											: 'text-muted-foreground hover:text-foreground'
									}`}
								>
									{p === 'annual' ? '연간' : '분기'}
								</button>
							))}
						</div>
					)}
				</div>
			)}
		</div>
	);
}
