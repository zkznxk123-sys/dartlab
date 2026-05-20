// /analysis/$code/financial — 재무제표분석.
// 자금조달 → 영업 선순환 → 현금·안정 3 narrative section. 사용자 명시 흐름
// (자산구조 → 부채상세 → 자본상세 → 손익구조) 한 viewport 진입, 그 다음 스크롤로
// 마진/수익성/현금/안정 분기. 카드 KPI tile 8 폐기.

import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { createFileRoute, getRouteApi } from '@tanstack/react-router';
import { Loader2 } from 'lucide-react';

import { CardShell } from '@/features/dashboard/cards/CardShell';
import { ChartMiniTable } from '@/features/dashboard/cards/ChartMiniTable';
import { VizChart } from '@/features/dashboard/charts/VizChart';
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from '@/components/ui/dialog';
import { useState } from 'react';
import {
	BentoGrid,
	BENTO_GAP_PX,
	BENTO_CARD_HEADER_PX,
	BENTO_CARD_PAD_PX,
} from '@/features/dashboard/layout/BentoGrid';
import {
	fetchCard,
	fetchCatalog,
	fetchTabLayout,
	type CatalogCard,
	type FinancialSubCategory,
	type PackedCard,
	type PeriodKind,
	type RechartsSpec,
} from '@/features/dashboard/api/client';
import { dashKeys } from '@/features/dashboard/api/queryKeys';
import { formatValue } from '@/lib/format';

type SubView = FinancialSubCategory;

// narrative section 정의 — cardKey → sectionIdx. backend layout 그대로 받되
// 컴포넌트에서 split 후 각 section 내 y 좌표 normalize (그룹 내 min y 빼기).
// 정통 분석 10 단계 매핑 — 5 section narrative.
const SECTIONS: { title: string; subtitle: string; keys: Set<string> }[] = [
	{
		title: '자본구조 · 자산구조',
		subtitle: '자산 = 부채+자본. 어떻게 자금조달해서 어떤 영업자산을 굴리는가 — CCC 까지.',
		keys: new Set([
			'assetComposition',
			'liabilityDetail',
			'equityDetail',
			'cashAssetsRatio',
			'incomeBreakdown',
			'workingCapitalDays',
		]),
	},
	{
		title: '영업 효율 · 자본 효율',
		subtitle: '마진·수익성·DuPont 5단·Penman·ROIC-WACC·세그먼트 — 본업이 진짜로 돈을 버는가.',
		keys: new Set([
			'marginTrend',
			'returnTrend',
			'dupont5Step',
			'penmanRoeDecomp',
			'roic',
			'roicWaccGap',
			'costStructureTrend',
			'turnoverTrend',
			'operatingLeverage',
			'taxWalk',
			'segmentRevenue',
			'effectiveTaxRate',
		]),
	},
	{
		title: '현금 일생 · 자본배분',
		subtitle: '현금흐름·FCF·자본배분·배당성향·이익품질·발생액·순차입금 — 번 돈은 어디로.',
		keys: new Set([
			'cashflowSigned',
			'fcfTrend',
			'capitalAllocation',
			'payoutRatio',
			'earningsQuality',
			'sloanAccruals',
			'netDebt',
		]),
	},
	{
		title: '재무 안정 · 부도 위험',
		subtitle: '안정성·유동성·Altman Z·5 모델 ensemble·이자보상·레버리지 — 망할 수 있는가.',
		keys: new Set(['stabilityRatio', 'liquidityTrend', 'leverageTrend', 'interestCoverage', 'altmanZ', 'distressEnsemble']),
	},
	{
		title: '성장의 질 · 이상신호',
		subtitle: '매출 YoY·자본 YoY·사업 집중도 — 성장이 진짜인가, 한 사업에 몰빵인가.',
		keys: new Set(['growthYoy', 'equityGrowth', 'segmentConcentration']),
	},
];
export const Route = createFileRoute('/analysis/$code/financial')({
	component: FinancialTab,
	validateSearch: (_search: Record<string, unknown>): { view: SubView | null } => {
		// v3-r6 — sub view 일시 폐기. URL ?view stale 도 무조건 null → OVERVIEW_KEYS curated 1 view.
		return { view: null };
	},
});

const parentRoute = getRouteApi('/analysis/$code');

function ChartLoading() {
	return (
		<div className="flex h-[220px] w-full items-center justify-center text-muted-foreground">
			<Loader2 className="size-5 animate-spin" />
		</div>
	);
}

// Snowflake 5-axis hero — Simply Wall St 패턴. 다른 5 섹션과 시각 일관 위해
// CardShell 로 감싸 동일 카드 단위. 운영자 명시 "음영·ring·hero 차등 강조 폐기"
// 의 후속 (CardShell.tsx 주석) — hero plain section 잔존이 일관성 파편이라 제거.
// spec 은 apiVizLayout bundle 에서 동행 (round-trip + prefetch 1 회 절약).
function SnowflakeHero({ spec }: { spec: RechartsSpec | undefined }) {
	if (!spec || spec.error) {
		return (
			<div className="px-3 pt-2">
				<CardShell title="" colSpan={12} rowSpan={3}>
					<div className="flex h-[180px] w-full items-center justify-center text-muted-foreground">
						<Loader2 className="size-5 animate-spin" />
					</div>
				</CardShell>
			</div>
		);
	}
	const scores = spec.series?.[0]?.data ?? [];
	const rawValues = (spec.options?.rawValues as (number | null)[] | undefined) ?? [];
	const rawUnits = (spec.options?.rawUnits as string[] | undefined) ?? [];
	const categories = spec.categories ?? [];
	const validScores = scores.filter((s): s is number => s != null);
	const avgScore = validScores.length > 0
		? validScores.reduce((sum, s) => sum + s, 0) / validScores.length
		: 0;
	// 절대 임계값 기반 verdict — peer 무관, 점수 그대로 5 구간.
	const verdict = (() => {
		if (avgScore >= 8.5) return { label: '매우 우수', tone: 'text-emerald-600 dark:text-emerald-400', dot: 'bg-emerald-500' };
		if (avgScore >= 7) return { label: '우수', tone: 'text-emerald-600 dark:text-emerald-400', dot: 'bg-emerald-500' };
		if (avgScore >= 5) return { label: '양호', tone: 'text-amber-600 dark:text-amber-400', dot: 'bg-amber-500' };
		if (avgScore >= 3) return { label: '주의', tone: 'text-orange-600 dark:text-orange-400', dot: 'bg-orange-500' };
		return { label: '위험', tone: 'text-rose-600 dark:text-rose-400', dot: 'bg-rose-500' };
	})();
	const strongest = validScores.length > 0
		? categories[scores.indexOf(Math.max(...validScores))]
		: null;
	const weakest = validScores.length > 0
		? categories[scores.indexOf(Math.min(...validScores))]
		: null;
	return (
		<div className="px-3 pt-2">
			<CardShell title={spec.title} colSpan={12} rowSpan={4}>
				<div className="grid grid-cols-12 gap-3">
					{/* 좌 — radar 크게 (5 축 한눈에) */}
					<div className="col-span-12 lg:col-span-5">
						<VizChart spec={spec} height={300} size={{ w: 5, h: 4 }} />
					</div>
					{/* 중 — 대형 평균 점수 + verdict + 최강/최약 한 줄 */}
					<div className="col-span-12 flex flex-col justify-center gap-1.5 lg:col-span-3">
						<div className="flex items-baseline gap-1.5">
							<span className="font-mono text-5xl font-bold tracking-tight tabular-nums text-foreground">
								{avgScore.toFixed(1)}
							</span>
							<span className="font-mono text-base text-muted-foreground">/ 10</span>
						</div>
						<div className="flex items-center gap-1.5">
							<span className={`size-1.5 rounded-full ${verdict.dot}`} />
							<span className={`text-[13px] font-semibold ${verdict.tone}`}>{verdict.label}</span>
							<span className="text-[10.5px] text-muted-foreground">· 5 축 평균</span>
						</div>
						{strongest && (
							<div className="mt-1 flex items-baseline gap-1.5 text-[10.5px]">
								<span className="font-mono uppercase tracking-wider text-muted-foreground/70">↑ 강점</span>
								<span className="truncate text-foreground" title={strongest}>{strongest}</span>
							</div>
						)}
						{weakest && weakest !== strongest && (
							<div className="flex items-baseline gap-1.5 text-[10.5px]">
								<span className="font-mono uppercase tracking-wider text-muted-foreground/70">↓ 약점</span>
								<span className="truncate text-foreground" title={weakest}>{weakest}</span>
							</div>
						)}
					</div>
					{/* 우 — 5 축 정렬 bar */}
					<div className="col-span-12 flex flex-col justify-center gap-2 lg:col-span-4">
						{categories.map((cat, i) => {
							const score = scores[i] ?? 0;
							const raw = rawValues[i];
							const unit = rawUnits[i] ?? '';
							const pct = Math.max(0, Math.min(100, (score / 10) * 100));
							const tone = score >= 7
								? 'bg-emerald-500'
								: score >= 5
									? 'bg-amber-500'
									: score >= 3
										? 'bg-orange-500'
										: 'bg-rose-500';
							return (
								<div key={cat} className="flex items-center gap-2">
									<div className="w-28 truncate text-[11px] text-muted-foreground" title={cat}>
										{cat}
									</div>
									<div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-muted/40">
										<div className={`h-full ${tone}`} style={{ width: `${pct}%` }} />
									</div>
									<div className="w-12 text-right font-mono text-[12px] font-semibold tabular-nums text-foreground">
										{score.toFixed(1)}
									</div>
									<div className="w-16 text-right font-mono text-[10px] text-muted-foreground tabular-nums">
										{raw != null ? `${raw.toFixed(unit === '배' ? 2 : 1)}${unit}` : '–'}
									</div>
								</div>
							);
						})}
					</div>
				</div>
			</CardShell>
		</div>
	);
}

// 카드 1 장 render — eager spec 은 prop 으로 주입. eager 외 카드는 *항상 mount* +
// bundled spec 없으면 즉시 lazy fetch. content-visibility / IntersectionObserver
// 게이트 폐기 (cell paint skip 이 lazy 트리거 막아 끝 카드 영영 spec 없음 회귀).
// backend _SPEC_CACHE TTL + viz._prefetchCompany dedup 이 30 카드 동시 lazy 호출
// race 차단. sparkline 만 폐기 (본 차트 데이터와 중복). footer (ChartMiniTable) +
// headerMetric (latestValue + YoY Δ) 는 유지 — 정보 가치 충분.
function CardRender({
	spec: bundledSpec,
	packed,
	meta,
	cardOuterH,
	computeHeaderMetric,
	stockCode,
	periodKind,
}: {
	spec: RechartsSpec | undefined;
	packed: PackedCard;
	meta: CatalogCard | undefined;
	cardOuterH: number;
	computeHeaderMetric: (spec: RechartsSpec | undefined) => React.ReactNode;
	stockCode: string;
	periodKind: PeriodKind;
}) {
	const needsLazy = !bundledSpec;
	const { data: lazySpec } = useQuery({
		queryKey: dashKeys.card(packed.cardKey, stockCode, periodKind),
		queryFn: () => fetchCard(packed.cardKey, stockCode, periodKind, 40),
		enabled: needsLazy,
		staleTime: 5 * 60_000,
		retry: 1,
	});
	const spec = bundledSpec ?? lazySpec;

	const title = meta?.title || spec?.title || packed.title;
	const help = meta?.help;
	const seriesCount = spec?.series?.length ?? 0;
	const isDualStack = spec?.options?.dualStack === true;
	const hasFooter = !!(spec && spec.kind === 'trend' && seriesCount > 0 && !isDualStack);
	const footer = hasFooter ? <ChartMiniTable spec={spec} /> : undefined;
	// footer 추정 — ChartMiniTable row 14px + thead 16px + wrapper(border-t + py-1) 9px.
	// 카드 outer 의 40% 상한 가드 — series 많은 카드도 chart body 가 최소 60% 확보.
	const footerHeight = hasFooter
		? Math.min(14 * Math.min(seriesCount, 12) + 25, cardOuterH * 0.4)
		: 0;
	const bodyHeight = Math.max(
		60,
		cardOuterH - BENTO_CARD_HEADER_PX - BENTO_CARD_PAD_PX - footerHeight,
	);
	const [open, setOpen] = useState(false);
	const kind = spec?.kind ?? packed.kind;
	const ready = !!spec && !spec.error;
	const headerMetric = ready ? computeHeaderMetric(spec) : undefined;
	return (
		<>
			<div
				onClick={() => ready && setOpen(true)}
				className={ready ? 'h-full cursor-pointer transition-opacity hover:opacity-95' : 'h-full'}
				role={ready ? 'button' : undefined}
				tabIndex={ready ? 0 : undefined}
				onKeyDown={(e) => {
					if (ready && (e.key === 'Enter' || e.key === ' ')) {
						e.preventDefault();
						setOpen(true);
					}
				}}
			>
				<CardShell
					title={title}
					help={help}
					colSpan={packed.w}
					rowSpan={packed.h}
					kind={kind}
					footer={ready ? footer : undefined}
					headerExtra={headerMetric}
				>
					{ready ? (
						<VizChart spec={spec} height={bodyHeight} size={{ w: packed.w, h: packed.h }} />
					) : (
						<ChartLoading />
					)}
				</CardShell>
			</div>
			{ready && (
				<Dialog open={open} onOpenChange={setOpen}>
					<DialogContent className="max-w-5xl">
						<DialogHeader>
							<DialogTitle className="flex items-baseline gap-3">
								<span>{title}</span>
								<span className="text-xs font-normal text-muted-foreground">
									{packed.cardKey}
								</span>
							</DialogTitle>
							{help && (
								<DialogDescription className="text-[12px] leading-relaxed">
									{help}
								</DialogDescription>
							)}
						</DialogHeader>
						<div className="space-y-4">
							<VizChart spec={spec} height={420} size={{ w: 12, h: 6 }} />
							{spec.kind === 'trend' && (spec.series?.length ?? 0) > 0 && !isDualStack && (
								<div className="border-t pt-3">
									<ChartMiniTable spec={spec} />
								</div>
							)}
						</div>
					</DialogContent>
				</Dialog>
			)}
		</>
	);
}

function FinancialTab() {
	const { code } = Route.useParams();
	const { period: periodKind } = parentRoute.useSearch();

	const { data: catalog } = useQuery({
		queryKey: dashKeys.catalog(),
		queryFn: fetchCatalog,
		staleTime: Infinity,
	});

	// v3-r6 — sub view 폐기. view 항상 null → backend OVERVIEW_KEYS curated.
	// bundle load — backend asyncio.gather 가 polars rawFinance 1 회 collect dedup +
	// 34 카드 동시 build. eagerN=40 (le=80) 으로 전체 eager 강제. 옛 eagerN=3 회귀:
	// 첫 3 카드만 즉시 paint, 나머지 31 카드 lazy fetch 가 직렬 4~5s 체감 →
	// 사용자 "초반 3 빨리 그 뒤 한참" 회귀. backend gather 34 동시 1.5~3s 가 lazy
	// 직렬보다 체감 짧음 (모든 카드 한꺼번에 paint).
	const apiView = null;
	const { data, isError, isLoading, isFetching, error } = useQuery({
		queryKey: dashKeys.tabLayout('financial', code, apiView, periodKind),
		queryFn: () => fetchTabLayout('financial', code, apiView, periodKind, 40, false, 40),
		placeholderData: keepPreviousData,
		staleTime: 5 * 60_000,
		retry: 1,
	});

	const cardMetaByKey: Record<string, CatalogCard | undefined> = Object.fromEntries(
		(catalog?.cards ?? []).map((c) => [c.cardKey, c]),
	);

	// Tremor 정통 — 헤더 우측 latest value + YoY Δ (% point or 비율 변화). primary 시리즈
	// (또는 첫 비-stack 시리즈) 의 마지막 유효값과 4 분기 전 값 비교. dual-stack / multi-axis
	// 카드는 모호하므로 표시 생략.
	function computeHeaderMetric(spec: RechartsSpec | undefined): React.ReactNode {
		if (!spec || spec.kind !== 'trend') return null;
		if (spec.options?.dualStack) return null;
		if (!spec.series?.length) return null;
		const primary =
			spec.series.find((s) => s.intent === 'primary') ??
			spec.series.find((s) => !s.stack && s.type === 'line') ??
			spec.series[0];
		const data = primary?.data ?? [];
		const lastIdx = data.length - 1;
		const last = lastIdx >= 0 ? data[lastIdx] : null;
		const lookback = periodKind === 'quarterly' ? 4 : 1;
		const prevIdx = lastIdx - lookback;
		const prev = prevIdx >= 0 ? data[prevIdx] : null;
		if (last == null || !Number.isFinite(last as number)) return null;
		const unit = primary?.unit ?? '';
		const lastStr = formatValue(last as number, unit);
		let deltaNode: React.ReactNode = null;
		if (prev != null && Number.isFinite(prev as number)) {
			const isPct = unit === '%' || unit === '배' || unit === '회';
			const delta = isPct
				? (last as number) - (prev as number)
				: (prev as number) !== 0
					? ((last as number) - (prev as number)) / Math.abs(prev as number) * 100
					: null;
			if (delta != null && Number.isFinite(delta)) {
				const sign = delta > 0 ? '+' : '';
				const suffix = isPct ? (unit === '%' ? '%p' : (unit === '회' ? '회' : '배')) : '%';
				const tone =
					Math.abs(delta) < 0.05
						? 'text-muted-foreground/80'
						: delta > 0
							? 'text-emerald-500 dark:text-emerald-400'
							: 'text-rose-500 dark:text-rose-400';
				deltaNode = (
					<span className={`text-[10.5px] font-medium ${tone}`}>
						{sign}
						{Math.abs(delta) >= 10 ? delta.toFixed(0) : delta.toFixed(1)}
						{suffix}
					</span>
				);
			}
		}
		return (
			<>
				<span className="text-[12px] font-mono font-semibold text-foreground">{lastStr}</span>
				{deltaNode}
			</>
		);
	}

	const renderCard = (p: PackedCard, cellSize: number) => {
		const meta = cardMetaByKey[p.cardKey];
		const spec = data?.cards?.[p.cardKey];
		const cardOuterH = p.h * cellSize + (p.h - 1) * BENTO_GAP_PX;
		return (
			<CardRender
				spec={spec}
				packed={p}
				meta={meta}
				cardOuterH={cardOuterH}
				computeHeaderMetric={computeHeaderMetric}
				stockCode={code}
				periodKind={periodKind}
			/>
		);
	};

	// placeholder layout 폐기 — frontend sequential pack 좌표가 backend packSkyline
	// 결과와 달라 첫 paint 시 카드 좌측 몰림 → 응답 도착 후 reorder layout shift
	// 회귀 ("초반 왼쪽에 카드가 몰림"). 진입 초기엔 SECTIONS 헤더만 + 섹션별
	// 단일 spinner 로 골격 표시, 좌표는 backend layout 도착 후 정확 1회 paint.
	const placed = data?.layout ?? [];

	const grouped = SECTIONS.map((section) => {
		const cards = placed.filter((p) => section.keys.has(p.cardKey));
		if (cards.length === 0) return null;
		const minY = Math.min(...cards.map((c) => c.y));
		const normalized = cards.map((c) => ({ ...c, y: c.y - minY }));
		return { section, cards: normalized };
	}).filter((g): g is { section: typeof SECTIONS[0]; cards: typeof placed } => g !== null);

	return (
		<>
			{isError && (
				<div className="border-b bg-destructive/10 px-4 py-2 text-xs text-destructive">
					백엔드 응답 오류: {String((error as Error)?.message || 'unknown')} — 서버 재시작 필요할 수 있음
				</div>
			)}

			{/* 종목 변경 / refetch 진행 중 — isFetching && data 있음 (keepPreviousData 옛
			    데이터 표시 중) 일 때 상단에 indeterminate progress bar. 사용자가 "갱신
			    중" 명확히 인지. 첫 cold (data 없음) 는 본 화면 spinner 가 담당. */}
			{isFetching && data && (
				<div className="sticky top-0 z-30 h-0.5 w-full overflow-hidden bg-transparent">
					<div className="h-full w-1/3 animate-[dl-progress_1.2s_ease-in-out_infinite] bg-primary/70" />
				</div>
			)}

			{placed.length === 0 ? (
				isLoading ? (
					// 진입 골격 — SECTIONS 5 헤더 + 섹션별 spinner. 좌표 placeholder 폐기
					// (좌측 몰림 layout shift 회귀 차단). backend layout 도착 후 정확
					// 1회 paint.
					<div className="flex flex-col">
						<div className="px-3 pt-2">
							<div className="flex h-[260px] items-center justify-center rounded-md border border-border/60 bg-card text-muted-foreground">
								<Loader2 className="size-5 animate-spin" />
							</div>
						</div>
						{SECTIONS.map((section, idx) => (
							<section key={section.title} className={idx === 0 ? 'mt-1' : 'mt-0.5'}>
								<header className="flex items-baseline gap-2 px-3 pt-2 pb-0">
									<span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground/70">
										{String(idx + 1).padStart(2, '0')}
									</span>
									<h2 className="text-[13px] font-semibold tracking-tight text-foreground">
										{section.title}
									</h2>
									<span className="text-[10.5px] text-muted-foreground">{section.subtitle}</span>
								</header>
								<div className="px-3 py-1.5">
									<div className="flex h-[180px] items-center justify-center rounded-md border border-border/40 bg-muted/20 text-muted-foreground">
										<Loader2 className="size-4 animate-spin" />
									</div>
								</div>
							</section>
						))}
					</div>
				) : (
					<div className="p-8 text-center text-sm text-muted-foreground">
						이 카테고리의 카드가 아직 없습니다.
					</div>
				)
			) : (
				<div className="flex flex-col">
					<SnowflakeHero spec={data?.cards?.snowflakeRadar} />
					{grouped.map(({ section, cards }, idx) => (
						<section key={section.title} className={idx === 0 ? 'mt-1' : 'mt-0.5'}>
							<header className="flex items-baseline justify-between gap-2 px-3 pt-2 pb-0">
								<div className="flex items-baseline gap-2">
									<span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground/70">
										{String(idx + 1).padStart(2, '0')}
									</span>
									<h2 className="text-[13px] font-semibold tracking-tight text-foreground">
										{section.title}
									</h2>
									<span className="text-[10.5px] text-muted-foreground">{section.subtitle}</span>
								</div>
								<div aria-hidden className="hidden flex-1 self-center border-t border-border/40 lg:block" />
							</header>
							<BentoGrid placed={cards} renderCard={renderCard} />
						</section>
					))}
				</div>
			)}
		</>
	);
}
