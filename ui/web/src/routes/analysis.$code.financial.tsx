// /analysis/$code/financial — 재무제표분석.
// 자금조달 → 영업 선순환 → 현금·안정 3 narrative section. 사용자 명시 흐름
// (자산구조 → 부채상세 → 자본상세 → 손익구조) 한 viewport 진입, 그 다음 스크롤로
// 마진/수익성/현금/안정 분기. 카드 KPI tile 8 폐기.

import { useQuery } from '@tanstack/react-query';
import { createFileRoute } from '@tanstack/react-router';
import { Loader2 } from 'lucide-react';
import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { CardShell } from '@/features/dashboard/cards/CardShell';
import { useDashboardMode } from '@/features/dashboard/store/dashboardMode';
import { ChartMiniTable } from '@/features/dashboard/cards/ChartMiniTable';
import { VizChart } from '@/features/dashboard/charts/VizChart';
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from '@/components/ui/dialog';
import {
	BentoGrid,
	BENTO_GAP_PX,
	BENTO_CARD_HEADER_PX,
	BENTO_CARD_PAD_PX,
} from '@/features/dashboard/layout/BentoGrid';
import {
	fetchCatalog,
	type CatalogCard,
	type FinancialSubCategory,
	type PackedCard,
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
		subtitle: '자산 = 부채+자본. 어떻게 자금조달해서 어떤 영업자산을 굴리는가 — 안정성·유동성·레버리지 포함.',
		keys: new Set([
			'assetComposition',
			'liabilityDetail',
			'equityDetail',
			'incomeBreakdown',
			'workingCapitalDays',
			'stabilityRatio',
			'liquidityTrend',
			'leverageTrend',
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
			'roicWaccGap',
			'costStructureTrend',
			'turnoverTrend',
			'operatingLeverage',
			'taxWalk',
			'effectiveTaxRate',
			'segmentRevenue',
		]),
	},
	{
		title: '현금 일생 · 자본배분',
		subtitle: '현금흐름·FCF·자본배분·이익품질·발생액·순차입금·이자보상 — 번 돈은 어디로.',
		keys: new Set([
			'cashflowSigned',
			'fcfTrend',
			'capitalAllocation',
			'payoutRatio',
			'earningsQuality',
			'sloanAccruals',
			'netDebt',
			'interestCoverage',
		]),
	},
	{
		title: '성장의 질 · 이상신호',
		subtitle: '매출/영업/순이익/자본 YoY·사업 집중도 — 성장이 진짜인가, 한 사업에 몰빵인가.',
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

function ChartLoading() {
	return (
		<div className="flex h-[220px] w-full items-center justify-center text-muted-foreground">
			<Loader2 className="size-5 animate-spin" />
		</div>
	);
}

// 카드 1 장 render — streaming endpoint 가 도착하는 즉시 spec 채워줌. 아직 미도착
// 카드는 spinner 자리 유지. React.memo 로 spec/packed/meta 변경 없는 카드는 다른
// 카드 도착 시 re-render skip — 35 setState (도착 순) cascade 비용 차단.
const CardRender = memo(function CardRender({
	spec,
	packed,
	meta,
	cardOuterH,
	computeHeaderMetric,
}: {
	spec: RechartsSpec | undefined;
	packed: PackedCard;
	meta: CatalogCard | undefined;
	cardOuterH: number;
	computeHeaderMetric: (spec: RechartsSpec | undefined) => React.ReactNode;
}) {

	const title = meta?.title || spec?.title || packed.title;
	const help = meta?.help;
	const seriesCount = spec?.series?.length ?? 0;
	const isDualStack = spec?.options?.dualStack === true;
	const hasFooter = !!(spec && spec.kind === 'trend' && seriesCount > 0 && !isDualStack);
	const footer = hasFooter ? <ChartMiniTable spec={spec} /> : undefined;
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

	// IntersectionObserver gate — viewport 안 카드만 차트 mount. spec 은 이미 도착
	// (streaming 으로 모두 메모리에) — 옛 lazy-fetch 회귀 우려 무관. 30 차트 동시
	// mount 의 2~3s long task 가 첫 viewport (~6 카드) mount 만 = 0.3~0.5s.
	const cellRef = useRef<HTMLDivElement>(null);
	const [visible, setVisible] = useState(false);
	useEffect(() => {
		if (visible) return;
		const el = cellRef.current;
		if (!el) return;
		const io = new IntersectionObserver(
			(entries) => {
				if (entries.some((e) => e.isIntersecting)) {
					setVisible(true);
					io.disconnect();
				}
			},
			{ rootMargin: '400px 0px' },
		);
		io.observe(el);
		return () => io.disconnect();
	}, [visible]);

	return (
		<>
			<div
				ref={cellRef}
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
					footer={ready && visible ? footer : undefined}
					headerExtra={headerMetric}
				>
					{ready && visible ? (
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
});

type PeriodView = 'annual' | 'quarterlyRaw' | 'quarterlyTtm';

const PERIOD_VIEW_OPTIONS: { value: PeriodView; label: string; hint: string }[] = [
	{ value: 'annual', label: '연간', hint: '연간 — 사업보고서 (Jan~Dec). 1년 1점.' },
	{
		value: 'quarterlyRaw',
		label: '분기',
		hint: '분기 누적 (DART 원본 Jan~기말). 계절성 그대로.',
	},
	{
		value: 'quarterlyTtm',
		label: '분기 TTM',
		hint:
			'TTM = 최근 4분기 합산 (연환산). 계절성 제거 + 매분기 갱신. 손익·현금흐름만 적용, 자산·자본은 시점값 유지. V차트 (최준철) 방식.',
	},
];

function FinancialTab() {
	const { code } = Route.useParams();
	const setLastMode = useDashboardMode((s) => s.setLastMode);

	// periodView — 3-mode segmented (annual / quarterlyRaw / quarterlyTtm).
	// 기본 quarterlyTtm: 분기 단위 갱신 + seasonality 제거. parent 의 ?period
	// search param 은 다른 탭 의 정렬용 — financial 탭은 자기 토글 우선.
	const [periodView, setPeriodView] = useState<PeriodView>('quarterlyTtm');
	const periodKind: 'annual' | 'quarterly' = periodView === 'annual' ? 'annual' : 'quarterly';

	// 종목 전환 시 직전 모드 복원에 사용. 본 탭 마운트 = financial 모드 진입.
	useEffect(() => {
		setLastMode('financial');
	}, [setLastMode]);

	const { data: catalog } = useQuery({
		queryKey: dashKeys.catalog(),
		queryFn: fetchCatalog,
		staleTime: Infinity,
	});

	// NDJSON streaming consumer — layout 즉시 + 카드 도착 순으로 cards 채움.
	// StrictMode (dev) 가 useEffect 를 두 번 fire 함 → AbortController 패턴이 두 번째
	// fetch 까지 죽이는 race. cancelled flag + reader.cancel() 로 첫 mount stream 은
	// silent 하게 흘려보내고 두 번째 mount stream 만 state 반영. production 에선 1회.
	const [placed, setPlaced] = useState<PackedCard[]>([]);
	const [cards, setCards] = useState<Record<string, RechartsSpec>>({});
	const [streaming, setStreaming] = useState(false);
	const [streamError, setStreamError] = useState<string | null>(null);
	const [ttmAvail, setTtmAvail] = useState<{
		annualFyYears: number;
		quarterlyPeriods: number;
		ttmFullCount: number;
		ttmFallbackCount: number;
		sufficient: boolean;
	} | null>(null);

	useEffect(() => {
		let cancelled = false;
		let activeReader: ReadableStreamDefaultReader<Uint8Array> | null = null;
		setPlaced([]);
		setCards({});
		setStreamError(null);
		setStreaming(true);
		setTtmAvail(null);

		// rAF batch — 같은 frame 안에 도착한 카드들은 한 번에 setCards. 카드 간 도착
		// 간격이 frame (16ms) 보다 길면 자연스럽게 frame 단위 분산.
		let pendingCards: Record<string, RechartsSpec> = {};
		let drainHandle: number | null = null;
		const flushPending = () => {
			drainHandle = null;
			if (cancelled) return;
			const merged = pendingCards;
			pendingCards = {};
			if (Object.keys(merged).length === 0) return;
			setCards((prev) => ({ ...prev, ...merged }));
		};
		const enqueueCard = (k: string, spec: RechartsSpec) => {
			pendingCards[k] = spec;
			if (drainHandle == null) {
				drainHandle = requestAnimationFrame(flushPending);
			}
		};

		(async () => {
			const url = `/api/viz/layout-stream/financial/${code}?periodView=${periodView}&nPeriods=40`;
			try {
				const res = await fetch(url);
				if (cancelled) {
					await res.body?.cancel();
					return;
				}
				if (!res.ok || !res.body) {
					throw new Error(`HTTP ${res.status}`);
				}
				const reader = res.body.getReader();
				activeReader = reader;
				const decoder = new TextDecoder();
				let buf = '';
				while (true) {
					const { done, value } = await reader.read();
					if (done) break;
					if (cancelled) return;
					buf += decoder.decode(value, { stream: true });
					let nl = buf.indexOf('\n');
					while (nl >= 0) {
						const line = buf.slice(0, nl).trim();
						buf = buf.slice(nl + 1);
						nl = buf.indexOf('\n');
						if (!line) continue;
						let msg: {
								type: string;
								placed?: PackedCard[];
								cardKey?: string;
								spec?: RechartsSpec;
								ttmAvailability?: {
									annualFyYears: number;
									quarterlyPeriods: number;
									ttmFullCount: number;
									ttmFallbackCount: number;
									sufficient: boolean;
								};
							};
						try {
							msg = JSON.parse(line);
						} catch {
							continue;
						}
						if (cancelled) return;
						if (msg.type === 'layout' && Array.isArray(msg.placed)) {
							setPlaced(msg.placed);
							if (msg.ttmAvailability) setTtmAvail(msg.ttmAvailability);
						} else if (msg.type === 'card' && msg.cardKey && msg.spec) {
							enqueueCard(msg.cardKey, msg.spec);
						} else if (msg.type === 'done') {
							setStreaming(false);
						}
					}
				}
				// 마지막 큐는 drain frame chain 이 자연 종료. streaming flag 는 큐가 비고
				// done 메시지 도착 후 false 로 떨어짐 — UI 의 sticky progress bar 가 도착
				// 진행 중 정확히 표시.
				if (!cancelled) setStreaming(false);
			} catch (e) {
				if (cancelled) return;
				setStreamError(String((e as Error)?.message || e));
				setStreaming(false);
			}
		})();

		return () => {
			cancelled = true;
			if (drainHandle != null) cancelAnimationFrame(drainHandle);
			activeReader?.cancel().catch(() => undefined);
		};
	}, [code, periodView]);

	const cardMetaByKey: Record<string, CatalogCard | undefined> = useMemo(
		() => Object.fromEntries((catalog?.cards ?? []).map((c) => [c.cardKey, c])),
		[catalog],
	);

	// Tremor 정통 — 헤더 우측 latest value + YoY Δ (% point or 비율 변화). primary 시리즈
	// (또는 첫 비-stack 시리즈) 의 마지막 유효값과 4 분기 전 값 비교. dual-stack / multi-axis
	// 카드는 모호하므로 표시 생략. useCallback — memo CardRender 의 prop reference 안정.
	const computeHeaderMetric = useCallback(function computeHeaderMetric(spec: RechartsSpec | undefined): React.ReactNode {
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
	}, [periodKind]);

	// renderCard 가 cards/meta 바뀔 때마다 새 closure — 그래도 memo CardRender 가
	// spec reference 비교로 변경 없는 카드는 re-render skip. 35 카드 cascade 비용 차단.
	const renderCard = useCallback((p: PackedCard, cellSize: number) => {
		const meta = cardMetaByKey[p.cardKey];
		const spec = cards[p.cardKey];
		const cardOuterH = p.h * cellSize + (p.h - 1) * BENTO_GAP_PX;
		return (
			<CardRender
				spec={spec}
				packed={p}
				meta={meta}
				cardOuterH={cardOuterH}
				computeHeaderMetric={computeHeaderMetric}
			/>
		);
	}, [cards, cardMetaByKey, computeHeaderMetric]);

	// placeholder layout 폐기 — frontend sequential pack 좌표가 backend packSkyline
	// 결과와 달라 첫 paint 시 카드 좌측 몰림 → 응답 도착 후 reorder layout shift
	// 회귀. 진입 초기엔 SECTIONS 헤더만 + 섹션별 단일 spinner 로 골격 표시,
	// 좌표는 backend layout 도착 후 정확 1회 paint.

	const grouped = SECTIONS.map((section) => {
		const sectionCards = placed.filter((p) => section.keys.has(p.cardKey));
		if (sectionCards.length === 0) return null;
		const minY = Math.min(...sectionCards.map((c) => c.y));
		const normalized = sectionCards.map((c) => ({ ...c, y: c.y - minY }));
		return { section, cards: normalized };
	}).filter((g): g is { section: typeof SECTIONS[0]; cards: PackedCard[] } => g !== null);

	const isLoading = placed.length === 0 && streaming;
	const isError = !!streamError;

	return (
		<>
			{isError && (
				<div className="border-b bg-destructive/10 px-4 py-2 text-xs text-destructive">
					백엔드 응답 오류: {streamError} — 서버 재시작 필요할 수 있음
				</div>
			)}

			{/* sticky wrapper — 토글 + streaming progress bar 한 묶음. scroll container
			   top 에 stuck. backdrop-blur 로 카드 콘텐츠 위에 떠있을 때 reading-friendly. */}
			<div className="sticky top-0 z-20 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/75">
			<div className="flex items-center justify-between gap-3 border-b border-border/40 px-3 py-1.5">
				<span className="hidden text-[10.5px] text-muted-foreground sm:inline">
					{PERIOD_VIEW_OPTIONS.find((o) => o.value === periodView)?.hint}
				</span>
				<div className="ml-auto flex items-center gap-2">
					{/* TTM 가용성 — quarterlyTtm 모드 + 부족 시 노랑 badge. 4Q 미충족 = annualize fallback */}
					{periodView === 'quarterlyTtm' && ttmAvail && !ttmAvail.sufficient && (
						<span
							className="rounded-sm bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-medium text-amber-600 dark:text-amber-400"
							title={`TTM 가용 부족 — FY 데이터 ${ttmAvail.annualFyYears}년, fallback ${ttmAvail.ttmFallbackCount}개 분기는 단순 annualize (×12/N) 적용.`}
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
					<div className="inline-flex rounded-md border border-border/60 bg-muted/20 p-0.5 text-[11px]">
						{PERIOD_VIEW_OPTIONS.map((opt) => (
							<button
								key={opt.value}
								type="button"
								onClick={() => setPeriodView(opt.value)}
								className={
									'rounded-sm px-2.5 py-1 font-medium transition-colors ' +
									(periodView === opt.value
										? 'bg-background text-foreground shadow-sm'
										: 'text-muted-foreground hover:text-foreground')
								}
								title={opt.hint}
							>
								{opt.label}
							</button>
						))}
					</div>
				</div>
			</div>

			{/* streaming 진행 중 — 토글 wrapper 안 한 줄로. */}
			{streaming && placed.length > 0 && (
				<div className="h-0.5 w-full overflow-hidden bg-transparent">
					<div className="h-full w-1/3 animate-[dl-progress_1.2s_ease-in-out_infinite] bg-primary/70" />
				</div>
			)}
			</div>

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
					{grouped.map(({ section, cards: sectionCards }, idx) => (
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
							<BentoGrid placed={sectionCards} renderCard={renderCard} />
						</section>
					))}
				</div>
			)}
		</>
	);
}
