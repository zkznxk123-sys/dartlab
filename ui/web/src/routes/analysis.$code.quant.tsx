// /analysis/$code/quant — 퀀트 대시보드 v3 (progressive load).
//
// Phase 1: layout-only fetch (cards 빈 dict) — backend 100ms 반환, grid 즉시 배치
// Phase 2: 각 카드별 useQuery(fetchCard) — 빠른 카드부터 점진 표시 (waterfall)
//
// 5~30s 대기 → 첫 카드 1~2s 도착 (가격 prefetch 안착 후 카드 직렬 build 각 0.1~1s).

import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { createFileRoute, getRouteApi } from '@tanstack/react-router';
import { Loader2 } from 'lucide-react';

import { CardShell } from '@/features/dashboard/cards/CardShell';
import { VizChart } from '@/features/dashboard/charts/VizChart';
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
	type PackedCard,
	type PeriodKind,
} from '@/features/dashboard/api/client';
import { dashKeys } from '@/features/dashboard/api/queryKeys';

export const Route = createFileRoute('/analysis/$code/quant')({
	component: QuantTab,
	validateSearch: (_search: Record<string, unknown>): { view: null } => ({ view: null }),
});

const parentRoute = getRouteApi('/analysis/$code');

function ChartLoading() {
	return (
		<div className="flex h-full w-full items-center justify-center text-muted-foreground">
			<Loader2 className="size-5 animate-spin" />
		</div>
	);
}

interface CardCellProps {
	p: PackedCard;
	cellSize: number;
	code: string;
	periodKind: PeriodKind;
	meta?: CatalogCard;
}

// CardCell — 카드 1 개 = 1 query. hooks rules 강행으로 renderCard 안 useQuery 불가 →
// 컴포넌트 분리. backend `/api/viz/spec/{cardKey}/{code}` lazy 호출.
function CardCell({ p, cellSize, code, periodKind, meta }: CardCellProps) {
	const { data: spec, isError, error } = useQuery({
		queryKey: dashKeys.card(p.cardKey, code, periodKind),
		queryFn: () => fetchCard(p.cardKey, code, periodKind, 40),
		staleTime: 5 * 60_000,
		retry: 1,
		// 카드별 fetch — backend 측 quant 순차 build 룰 그대로 (각 spec endpoint 가
		// 단일 thread 안 build). 가격 prefetch 후엔 sub-second.
	});
	const title = meta?.title || spec?.title || p.title;
	const help = meta?.help;
	const kind = spec?.kind ?? p.kind;
	const cardOuterH = p.h * cellSize + (p.h - 1) * BENTO_GAP_PX;
	const bodyHeight = Math.max(60, cardOuterH - BENTO_CARD_HEADER_PX - BENTO_CARD_PAD_PX);
	const errMsg = isError ? String((error as Error)?.message || 'fetch 실패') : spec?.error;
	return (
		<CardShell
			cardKey={p.cardKey}
			title={title}
			help={help}
			colSpan={p.w}
			rowSpan={p.h}
			kind={kind}
		>
			{spec && !spec.error ? (
				<VizChart spec={spec} height={bodyHeight} size={{ w: p.w, h: p.h }} />
			) : errMsg ? (
				<div className="flex h-full flex-col items-center justify-center gap-1 p-3 text-center text-xs text-muted-foreground">
					<div className="font-medium text-foreground/80">{title}</div>
					<div className="line-clamp-3 opacity-80">{errMsg}</div>
				</div>
			) : (
				<ChartLoading />
			)}
		</CardShell>
	);
}

function QuantTab() {
	const { code } = Route.useParams();
	const { period: periodKind } = parentRoute.useSearch();

	const { data: catalog } = useQuery({
		queryKey: dashKeys.catalog(),
		queryFn: fetchCatalog,
		staleTime: Infinity,
	});

	// Phase 1 — layout 만 fetch (layoutOnly=true). 100ms 안 grid 배치 시작.
	const { data, isError, isLoading, error } = useQuery({
		queryKey: dashKeys.tabLayout('quant', code, null, periodKind),
		queryFn: () => fetchTabLayout('quant', code, null, periodKind, 40, true),
		placeholderData: keepPreviousData,
		staleTime: 5 * 60_000,
		retry: 1,
	});

	const cardMetaByKey: Record<string, CatalogCard | undefined> = Object.fromEntries(
		(catalog?.cards ?? []).map((c) => [c.cardKey, c]),
	);

	const renderCard = (p: PackedCard, cellSize: number) => (
		<CardCell p={p} cellSize={cellSize} code={code} periodKind={periodKind} meta={cardMetaByKey[p.cardKey]} />
	);

	const placed = data?.layout ?? [];

	// 5 section narrative — gather → signal → factor → backtest → risk → forecast.
	// cardKey 명시 set. backend QUANT_CARDS 와 1:1 매핑.
	const SECTIONS: { title: string; subtitle: string; keys: Set<string> }[] = [
		{
			title: '가격·기술 신호',
			subtitle: '최근 1년 OHLC 캔들 + 매수/매도 marker + SMA(20)/SMA(60) overlay · RSI(14) · MACD sub-pane + 종합 판정.',
			keys: new Set(['quantPriceTrend', 'quantRsiTrend', 'quantMacdTrend', 'quantVerdictKpi']),
		},
		{
			title: '모멘텀 (Jegadeesh-Titman 12-1m)',
			subtitle: '12-1개월 모멘텀 + 52주 신고가 비율 + crash risk — 추세의 지속성.',
			keys: new Set(['quantMomentumKpi']),
		},
		{
			title: '백테스트 (8 style)',
			subtitle: 'trendFollow · meanReversion · breakout · dipBuy · eventDriven · flowFollow · lowVolDefensive · seasonalKR 8 정통 룰 — Sharpe 1위 style 자동 도출.',
			keys: new Set([
				'quantEquityCurve',
				'quantDrawdownChart',
				'quantMonthlyHeatmap',
				'quantStyleMatrix',
				'quantRollingSharpe',
				'quantAnnualReturns',
			]),
		},
		{
			title: '리스크 (β·변동성·Snowflake)',
			subtitle: 'Bloomberg BETA 산점도 + OLS β/α/R² · 5d/20d/60d/120d 변동성 term · drawdown 깊이 분포 · SWS 5 axis snowflake.',
			keys: new Set([
				'quantBetaScatter',
				'quantVolatilityTerm',
				'quantDrawdownDistribution',
				'quantSnowflakeRadar',
			]),
		},
		{
			title: '예측 (Conformal + Monte Carlo + HMM)',
			subtitle: '20일 horizon point + 90% CI fan · GBM 200 path Monte Carlo + VaR/CVaR · Hamilton HMM bull/bear regime.',
			keys: new Set(['quantForecastFan', 'quantMonteCarloPaths', 'quantRegimePhase']),
		},
	];

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
					레이아웃 응답 오류: {String((error as Error)?.message || 'unknown')} — 서버 재시작 필요할 수 있음
				</div>
			)}

			{placed.length === 0 ? (
				isLoading ? (
					<div className="flex items-center justify-center p-16 text-muted-foreground">
						<Loader2 className="size-6 animate-spin" />
					</div>
				) : (
					<div className="p-8 text-center text-sm text-muted-foreground">
						이 카테고리의 카드가 아직 없습니다.
					</div>
				)
			) : (
				<div className="flex flex-col">
					{grouped.map(({ section, cards }, idx) => (
						<section key={section.title} className={idx === 0 ? '' : 'mt-2'}>
							<header className="flex items-baseline justify-between gap-3 px-6 pt-4 pb-1">
								<div className="flex items-baseline gap-3">
									<span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground/70">
										{String(idx + 1).padStart(2, '0')}
									</span>
									<h2 className="text-[15px] font-semibold tracking-tight text-foreground">
										{section.title}
									</h2>
									<span className="text-[11px] text-muted-foreground">{section.subtitle}</span>
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
