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
import { useMemo, useState } from 'react';
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

type SubView = FinancialSubCategory;

// narrative section 정의 — cardKey → sectionIdx. backend layout 그대로 받되
// 컴포넌트에서 split 후 각 section 내 y 좌표 normalize (그룹 내 min y 빼기).
// 정통 분석 10 단계 매핑 — 5 section narrative.
// module-level 정의: placeholder layout 생성 useMemo 도 같은 SECTIONS 참조.
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
const SECTION_KEYS_FLAT = new Set<string>(SECTIONS.flatMap((s) => Array.from(s.keys)));

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
	const avgScore =
		scores.filter((s): s is number => s != null).length > 0
			? scores.reduce((sum: number, s) => sum + (s ?? 0), 0) /
				scores.filter((s) => s != null).length
			: 0;
	return (
		<div className="px-3 pt-2">
			<CardShell
				title={spec.title}
				colSpan={12}
				rowSpan={3}
				headerExtra={
					<span className="text-[10px] text-muted-foreground">
						평균 {avgScore.toFixed(1)} / 10 · 정통 절대 임계값
					</span>
				}
			>
				<div className="grid grid-cols-12 gap-2">
					<div className="col-span-12 md:col-span-7">
						<VizChart spec={spec} height={220} size={{ w: 7, h: 3 }} />
					</div>
					<div className="col-span-12 md:col-span-5 flex flex-col justify-center gap-1.5">
						{categories.map((cat, i) => {
							const score = scores[i] ?? 0;
							const raw = rawValues[i];
							const unit = rawUnits[i] ?? '';
							const pct = Math.max(0, Math.min(100, (score / 10) * 100));
							const tone =
								score >= 8
									? 'bg-emerald-500/70'
									: score >= 5
										? 'bg-amber-500/70'
										: 'bg-rose-500/70';
							return (
								<div key={cat} className="flex items-center gap-2">
									<div className="w-40 truncate text-[11px] text-muted-foreground" title={cat}>
										{cat}
									</div>
									<div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-muted/40">
										<div className={`h-full ${tone}`} style={{ width: `${pct}%` }} />
									</div>
									<div className="w-16 text-right font-mono text-[11px] tabular-nums">
										<span className="font-semibold text-foreground">{score.toFixed(1)}</span>
										<span className="ml-1 text-muted-foreground">/10</span>
									</div>
									<div className="w-20 text-right font-mono text-[10px] text-muted-foreground tabular-nums">
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
// race 차단. 카드 자체 chrome (sparkline·headerMetric·ChartMiniTable footer) 폐기 —
// 카드 경계 + 차트 본체만. 추가 정보는 클릭 → Dialog.
function CardRender({
	spec: bundledSpec,
	packed,
	meta,
	cardOuterH,
	stockCode,
	periodKind,
}: {
	spec: RechartsSpec | undefined;
	packed: PackedCard;
	meta: CatalogCard | undefined;
	cardOuterH: number;
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
	const isDualStack = spec?.options?.dualStack === true;
	// body = 카드 outer - 헤더 한 줄. footer 없음 (사용자 명시: 카드 경계만).
	const bodyHeight = Math.max(60, cardOuterH - BENTO_CARD_HEADER_PX - BENTO_CARD_PAD_PX);
	const [open, setOpen] = useState(false);
	const kind = spec?.kind ?? packed.kind;
	const ready = !!spec && !spec.error;
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
	// bundle load — backend asyncio.gather 가 progressive (35 round-trip) 보다 5x 빠름 (warm cache 0.36s vs 1.82s).
	// eagerN=3 — hero + 첫 3 카드만 동행. 4~6 번째는 IntersectionObserver lazy
	// (CardRender visible 진입 시 fetchCard). cold gather 6→3 카드 build → 0.5s
	// → 0.25s 절감. backend TTL 캐시 (viz._SPEC_CACHE) 가 lazy 호출 중복 build 0.
	const apiView = null;
	const { data, isError, isLoading, error } = useQuery({
		queryKey: dashKeys.tabLayout('financial', code, apiView, periodKind),
		queryFn: () => fetchTabLayout('financial', code, apiView, periodKind, 40, false, 3),
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
		const cardOuterH = p.h * cellSize + (p.h - 1) * BENTO_GAP_PX;
		return (
			<CardRender
				spec={spec}
				packed={p}
				meta={meta}
				cardOuterH={cardOuterH}
				stockCode={code}
				periodKind={periodKind}
			/>
		);
	};

	// placeholder layout — catalog 의 xlSpan + kind 로 sequential pack. backend layout
	// 응답 도착 전 5 섹션 골격 + 각 카드 spinner 즉시 paint. 인지 latency: cold ~700ms
	// 빈 화면 → 즉시 골격 + 카드별 spinner. catalog 는 staleTime: Infinity 라 첫 1회
	// 후 모든 진입에서 hit. 좌표는 정확하지 않으나 SECTIONS keys 매칭은 정확 →
	// layout 응답 도착 시 카드 ID 단위 reorder 만, 카드 mount 자체는 재사용 (key=cardKey).
	const placeholderPlaced = useMemo<PackedCard[]>(() => {
		if (!catalog) return [];
		const fin = (catalog.cards ?? []).filter((c) => SECTION_KEYS_FLAT.has(c.cardKey));
		let cursorX = 0;
		let cursorY = 0;
		let rowH = 0;
		const out: PackedCard[] = [];
		for (const c of fin) {
			const w = Math.min(12, c.xlSpan || 4);
			const h = c.kind === 'kpiTile' ? 2 : 3;
			if (cursorX + w > 12) {
				cursorY += rowH;
				cursorX = 0;
				rowH = 0;
			}
			out.push({ cardKey: c.cardKey, kind: c.kind, title: c.title, x: cursorX, y: cursorY, w, h });
			cursorX += w;
			rowH = Math.max(rowH, h);
		}
		return out;
	}, [catalog]);

	const placed = data?.layout ?? placeholderPlaced;

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
