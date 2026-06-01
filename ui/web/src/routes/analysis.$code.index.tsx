// /analysis/$code/ — 종목 선택 직후 진입하는 허브 화면.
//
// 모델: 사이드바에서 종목을 누르면 사이드바가 바로 financial 카드 로딩을
// 시작하지 않고 본 허브로 navigate. 허브는 중앙에 아바타 + 회사명 + 2 큰
// 버튼 (재무제표분석 / 공시뷰어). 사용자가 명시적으로 어디로 갈지 선택할
// 때까지 카드 로딩 폭주 X.
//
// 마운트 시점에 두 모드 데이터를 idle queue 로 background prefetch:
//   - direct: companyMeta (즉시, 표시 필요).
//   - idle queue: financial tabLayout + viewer init. 우선순위는
//     useDashboardMode.lastMode (직전에 본 모드 먼저).
// 사용자가 버튼 누를 시점엔 캐시 hit → 즉시 표시.

import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { FileText, Telescope } from 'lucide-react';

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { fetchCompanyMeta } from '@/features/dashboard/api/client';
import { dashKeys } from '@/features/dashboard/api/queryKeys';
import { usePrefetchCompany } from '@/features/dashboard/hooks/usePrefetchCompany';
import { useDashboardMode } from '@/features/dashboard/store/dashboardMode';

export const Route = createFileRoute('/analysis/$code/')({
	component: AnalysisHub,
	validateSearch: (s: Record<string, unknown>) => ({
		period: s.period === 'annual' ? ('annual' as const) : ('quarterly' as const),
	}),
});

function AnalysisHub() {
	const { code } = Route.useParams();
	const { period } = Route.useSearch();
	const navigate = useNavigate();
	const prefetch = usePrefetchCompany();
	const lastMode = useDashboardMode((s) => s.lastMode);

	const { data: meta } = useQuery({
		queryKey: dashKeys.companyMeta(code),
		queryFn: () => fetchCompanyMeta(code),
		staleTime: 10 * 60_000,
	});

	// 마운트 시 두 모드 background prefetch — 직전 모드 먼저.
	useEffect(() => {
		prefetch(code, { periodKind: period, full: true });
	}, [code, period, prefetch]);

	// 자동 진입 폐기 — 사용자 명시 룰 ("허브는 매번 거치는 화면").
	// lastMode 가 있어도 버튼을 사용자가 직접 누른다.

	const corpName = meta?.corpName ?? '';
	const recommendKey = lastMode ?? 'financial';

	return (
		<div className="flex min-h-0 flex-1 items-center justify-center px-6 py-12">
			<div className="flex w-full max-w-2xl flex-col items-center gap-8">
				<Avatar className="size-24 rounded-2xl shadow-md">
					<AvatarImage src="/avatar.png" alt="DartLab" />
					<AvatarFallback className="rounded-2xl text-2xl">DL</AvatarFallback>
				</Avatar>

				<div className="flex flex-col items-center gap-2 text-center">
					{corpName ? (
						<h1 className="text-2xl font-semibold tracking-tight">{corpName}</h1>
					) : (
						<h1 className="font-mono text-2xl font-semibold tracking-tight">{code}</h1>
					)}
					<div className="flex items-baseline gap-2 text-sm text-muted-foreground">
						<span className="font-mono">{code}</span>
						{meta?.market && <span>· {meta.market}</span>}
						{meta?.sector && <span>· {meta.sector}</span>}
					</div>
					{(meta?.products ?? []).length > 0 && (
						<div className="mt-1 flex flex-wrap justify-center gap-1.5">
							{(meta?.products ?? []).slice(0, 6).map((p) => (
								<Badge key={p} variant="outline" className="text-[10px] font-normal">
									{p}
								</Badge>
							))}
						</div>
					)}
					<p className="mt-3 max-w-md text-sm text-muted-foreground">
						어느 시각으로 분석할지 선택.
					</p>
				</div>

				<div className="grid w-full grid-cols-1 gap-3 sm:grid-cols-2">
					<HubButton
						icon={<FileText className="size-6" />}
						title="재무제표분석"
						subtitle="5 섹션 narrative · Snowflake · 30+ 카드"
						recommended={recommendKey === 'financial'}
						onClick={() =>
							navigate({
								to: '/analysis/$code/financial',
								params: { code },
								search: { period, view: null },
							})
						}
					/>
					<HubButton
						icon={<Telescope className="size-6" />}
						title="공시뷰어"
						subtitle="공시 본문 N 시점 동시 비교"
						recommended={recommendKey === 'viewer'}
						onClick={() =>
							navigate({
								to: '/analysis/$code/viewer',
								params: { code },
								search: { period, section: undefined, windowEnd: undefined },
							})
						}
					/>
				</div>
			</div>
		</div>
	);
}

interface HubButtonProps {
	icon: React.ReactNode;
	title: string;
	subtitle: string;
	recommended: boolean;
	onClick: () => void;
}

function HubButton({ icon, title, subtitle, recommended, onClick }: HubButtonProps) {
	return (
		<button
			type="button"
			onClick={onClick}
			className="group relative flex flex-col items-start gap-2 rounded-lg border bg-card p-5 text-left transition-colors hover:border-primary/60 hover:bg-accent/40 focus:outline-none focus:ring-2 focus:ring-ring"
		>
			{recommended && (
				<Badge className="absolute right-3 top-3 px-1.5 py-0 text-[9px] font-normal" variant="secondary">
					직전 모드
				</Badge>
			)}
			<div className="text-foreground/80 transition-colors group-hover:text-primary">{icon}</div>
			<div className="flex flex-col gap-0.5">
				<span className="text-base font-semibold tracking-tight">{title}</span>
				<span className="text-xs text-muted-foreground">{subtitle}</span>
			</div>
		</button>
	);
}

