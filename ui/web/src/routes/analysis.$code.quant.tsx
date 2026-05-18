// /analysis/$code/quant — 퀀트 대시보드.
// 5 section bento — gather 가격 raw + dartlab.quant 엔진 산출물 (signal · factor ·
// backtest · risk · forecast). financial.tsx 패턴 미러 — backend /api/viz/layout/
// quant/{code} 한 번 호출, frontend SECTIONS array 가 cardKey set 으로 5 분할.

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
	fetchCatalog,
	fetchTabLayout,
	type CatalogCard,
	type PackedCard,
} from '@/features/dashboard/api/client';
import { dashKeys } from '@/features/dashboard/api/queryKeys';

export const Route = createFileRoute('/analysis/$code/quant')({
	component: QuantTab,
	validateSearch: (_search: Record<string, unknown>): { view: null } => ({ view: null }),
});

const parentRoute = getRouteApi('/analysis/$code');

function ChartLoading() {
	return (
		<div className="flex h-[220px] w-full items-center justify-center text-muted-foreground">
			<Loader2 className="size-5 animate-spin" />
		</div>
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

	const { data, isError, isLoading, error } = useQuery({
		queryKey: dashKeys.tabLayout('quant', code, null, periodKind),
		queryFn: () => fetchTabLayout('quant', code, null, periodKind, 40),
		placeholderData: keepPreviousData,
		staleTime: 5 * 60_000,
		retry: 1,
	});

	const cardMetaByKey: Record<string, CatalogCard | undefined> = Object.fromEntries(
		(catalog?.cards ?? []).map((c) => [c.cardKey, c]),
	);

	const renderCard = (p: PackedCard, cellSize: number) => {
		const meta = cardMetaByKey[p.cardKey];
		const spec = data?.cards?.[p.cardKey];
		const title = meta?.title || spec?.title || p.title;
		const help = meta?.help;
		const seriesCount = spec?.series?.length ?? 0;
		const kind = spec?.kind ?? p.kind;
		// quant 탭은 mini-table footer 의미 0 — 가격 시계열 252 일 OHLC 표는 무의미.
		// candle / kpiTile / 가격 trend 모두 footer 제거. financial 탭과 다른 정체성.
		const hasFooter = false;
		const footer = undefined;
		const footerHeight = 0;
		// 위 변수들 사용 표시 (린트 회피용 — 향후 trend 차트 추가 시 살릴 자리).
		void seriesCount;
		void hasFooter;
		void footer;
		const cardOuterH = p.h * cellSize + (p.h - 1) * BENTO_GAP_PX;
		const bodyHeight = Math.max(60, cardOuterH - BENTO_CARD_HEADER_PX - BENTO_CARD_PAD_PX - footerHeight);
		return (
			<CardShell title={title} help={help} colSpan={p.w} rowSpan={p.h} kind={kind} footer={undefined}>
				{spec && !spec.error ? <VizChart spec={spec} height={bodyHeight} size={{ w: p.w, h: p.h }} /> : <ChartLoading />}
			</CardShell>
		);
	};

	const placed = data?.layout ?? [];

	// 5 section narrative — gather → signal → factor → backtest → risk → forecast.
	// cardKey 명시 set. backend QUANT_CARDS 와 1:1 매핑.
	const SECTIONS: { title: string; subtitle: string; keys: Set<string> }[] = [
		{
			title: '가격·기술 신호',
			subtitle: '최근 1년 종가 + SMA(20)/SMA(60) overlay + RSI·ADX·BB위치 종합 판정.',
			keys: new Set(['quantPriceTrend', 'quantVerdictKpi']),
		},
		{
			title: '모멘텀 (Jegadeesh-Titman 12-1m)',
			subtitle: '12-1개월 모멘텀 + 52주 신고가 비율 + crash risk — 추세의 지속성.',
			keys: new Set(['quantMomentumKpi']),
		},
		{
			title: '백테스트',
			subtitle: '8 style equity curve + Sharpe/Sortino/MaxDD — 본 종목 전략별 성과 (속편).',
			keys: new Set(['quantBacktestComingSoon']),
		},
		{
			title: '리스크 (변동성·베타)',
			subtitle: 'GARCH(1,1) 조건부 변동성 + 시장 베타 + CAPM 기대수익률 — 시장 민감도와 리스크.',
			keys: new Set(['quantVolatilityKpi', 'quantBetaKpi']),
		},
		{
			title: '예측 (Conformal)',
			subtitle: '5일 horizon 수익률 점예측 + 90% Conformal interval (Naive·AR·ETS·Theta).',
			keys: new Set(['quantForecastKpi']),
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
					백엔드 응답 오류: {String((error as Error)?.message || 'unknown')} — 서버 재시작 필요할 수 있음
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
