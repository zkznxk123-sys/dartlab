// /analysis/$code/viewer — 공시 뷰어 (시간축 윈도우 모델).
//
// 모델:
//   - 좌 TOC: chapter > leaf topic (기존 유지)
//   - 헤더: 토픽 전체 시간축 (변경된 period 마커) + 현재 윈도우 3 period + 좌우 이동
//   - 본문: sections 의 id 별 row, 3 period column. 각 cell 이 그 시점의 latest.body.
//   - 각 column 헤더에 그 period 의 DART 원본 링크 (per-period rcpNo).
//
// dartlab 차별점 = *동시 비교*. DART 는 한 시점 한 보고서만, 우리는 N 시점 나란히.
//
// fetch:
//   - phase 1: /viewer/{topic}?compact=true&limit=60 (latest) — td.periods 와 sections 받음
//   - phase 2: /viewer/{topic}?period=X&compact=true 3 개 parallel (windowEnd 의 3 period)
//   - URL ?windowEnd=2026Q1 으로 윈도우 핀, 없으면 latest

import { useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { ChevronLeft, ChevronRight, ExternalLink, FileText, Loader2 } from 'lucide-react';
import { useEffect, useMemo } from 'react';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface TocTopic {
	topic: string;
	label?: string;
	topicLabel?: string;
	textCount?: number;
	tableCount?: number;
	hasChanges?: boolean;
}
interface TocChapter {
	chapter: string;
	topics: TocTopic[];
}
interface TocResponse {
	stockCode: string;
	corpName: string;
	chapters: TocChapter[];
}

interface PeriodRef {
	label?: string;
	year?: number;
	quarter?: number | null;
	kind?: string;
	sortKey?: number;
}

interface ViewerHeading {
	block: number;
	text: string;
	period?: PeriodRef | null;
	level?: number;
}

interface ViewerTextView {
	period?: PeriodRef | null;
	prevPeriod?: PeriodRef | null;
	body?: string;
	status?: string;
}

interface ViewerSection {
	id: string;
	order?: string | number;
	headingPath: ViewerHeading[];
	latest?: ViewerTextView | null;
	latestPeriod?: PeriodRef | string | null;
	firstPeriod?: PeriodRef | string | null;
	periodCount?: number;
	status?: string;
	latestChange?: string;
	preview?: string;
	timeline?: Array<{ period?: PeriodRef | null; status?: string }>;
}

interface ViewerResponse {
	stockCode: string;
	corpName: string;
	topic: string;
	topicLabel?: string;
	compact?: boolean;
	period?: string | null;
	dartUrl?: string | null;
	textDocument?: {
		topic?: string;
		mode?: string;
		periods?: PeriodRef[];
		latestPeriod?: PeriodRef | string;
		firstPeriod?: PeriodRef | string;
		totalSectionCount?: number;
		truncated?: boolean;
		sectionCount?: number;
		updatedCount?: number;
		newCount?: number;
		staleCount?: number;
		stableCount?: number;
		sections?: ViewerSection[];
	};
}

interface ViewerSearch {
	topic?: string;
	windowEnd?: string;
}

interface InitResponse {
	stockCode: string;
	corpName: string;
	toc: TocResponse;
	firstTopic: string | null;
	firstChapter: string | null;
	viewer: ViewerResponse | null;
}

export const Route = createFileRoute('/analysis/$code/viewer')({
	component: ViewerTab,
	validateSearch: (s: Record<string, unknown>): ViewerSearch => ({
		topic: typeof s.topic === 'string' ? s.topic : undefined,
		windowEnd: typeof s.windowEnd === 'string' && s.windowEnd ? s.windowEnd : undefined,
	}),
});

const WINDOW_SIZE = 3;

async function fetchJson<T>(url: string): Promise<T> {
	const r = await fetch(url);
	if (!r.ok) throw new Error(`HTTP ${r.status} on ${url}`);
	return (await r.json()) as T;
}

function _periodLabel(p: unknown): string {
	if (p == null) return '';
	if (typeof p === 'string' || typeof p === 'number') return String(p);
	if (typeof p === 'object') {
		const obj = p as Record<string, unknown>;
		const label = obj.label;
		if (typeof label === 'string') return label;
		const period = obj.period;
		if (typeof period === 'string' || typeof period === 'number') return String(period);
		const year = obj.year;
		const quarter = obj.quarter;
		if (year != null) return quarter != null ? `${year}Q${quarter}` : String(year);
	}
	return '';
}

// DART 표준 leaf root — backend topic cross-contamination 차단용.
const KNOWN_LEAF_ROOTS: ReadonlySet<string> = new Set([
	'회사의 개요', '회사의 연혁', '자본금 변동사항',
	'주식의 총수 등', '정관에 관한 사항', '배당에 관한 사항',
	'사업의 개요', '주요 제품 및 서비스', '원재료 및 생산설비',
	'매출 및 수주상황', '위험관리 및 파생거래', '주요계약 및 연구개발활동',
	'기타 참고사항',
	'재무비율', '요약재무정보', '연결재무제표', '연결재무제표 주석',
	'재무제표', '재무제표 주석', '재무상태표', '손익계산서',
	'포괄손익계산서', '현금흐름표', '자본변동표',
]);

function _stripNumbering(s: string): string {
	if (!s) return '';
	return s.replace(/^(?:\d+|[IVXivx]+|[가-하])\.\s*/, '').trim();
}

// 순차 state machine — backend topic API 가 이미 자기 topic 만 슬라이스한 case 가 기본.
// 단, companyOverview 처럼 cross-contamination 이 박혀 있는 topic 도 있어 다른 KNOWN_LEAF_ROOT
// heading 이 path 에 등장하면 그 시점부터 false 로 플립. 끝까지 매칭 root 만 또는 비어있으면
// 모두 KEEP (기본 신뢰). 빈 headingPath 만 가진 정상 본문이 드롭되는 회귀 차단.
function _filterToOwnLeaf(allSections: ViewerSection[], ownLeafCore: string): ViewerSection[] {
	if (!ownLeafCore) return allSections;
	const kept: ViewerSection[] = [];
	let activeOwn = true;
	for (const s of allSections) {
		const path = s.headingPath ?? [];
		let foundRoot: string | null = null;
		for (const h of path) {
			const t = typeof h === 'string' ? (h as string) : (h?.text || '');
			const core = _stripNumbering(t);
			if (core && KNOWN_LEAF_ROOTS.has(core)) foundRoot = core;
		}
		if (foundRoot !== null) activeOwn = foundRoot === ownLeafCore;
		if (activeOwn) kept.push(s);
	}
	return kept;
}

function _bodyParagraphs(body: string | undefined | null): string[] {
	if (!body || !body.trim()) return [];
	const blocks = body.replace(/\r\n?/g, '\n').split(/\n\s*\n+/);
	if (blocks.length > 1) {
		return blocks.map((b) => b.replace(/\s+/g, ' ').trim()).filter(Boolean);
	}
	return body
		.split('\n')
		.map((line) => line.replace(/\s+/g, ' ').trim())
		.filter(Boolean);
}

function _sectionTitle(section: ViewerSection): { text: string; level: number } | null {
	const path = section.headingPath ?? [];
	for (let i = path.length - 1; i >= 0; i--) {
		const h = path[i];
		const text = typeof h === 'string' ? (h as string) : (h?.text ?? '');
		if (typeof text === 'string' && text.trim().length > 0) {
			const level = typeof h === 'object' && typeof h?.level === 'number' ? h.level : 0;
			return { text: text.trim(), level };
		}
	}
	return null;
}

function _headingStyle(level: number, minLevel: number): { tag: 'h2' | 'h3' | 'h4'; cls: string } {
	const rel = Math.max(1, level - minLevel + 1);
	if (rel <= 1) return { tag: 'h2', cls: 'text-lg font-semibold tracking-tight' };
	if (rel === 2) return { tag: 'h3', cls: 'text-base font-semibold' };
	return { tag: 'h4', cls: 'text-sm font-semibold text-muted-foreground' };
}

function ViewerTab() {
	const { code } = Route.useParams();
	const { topic, windowEnd } = Route.useSearch();
	const navigate = useNavigate();
	const queryClient = useQueryClient();

	// cold load — /init 한 번에 toc + firstTopic + viewer.
	const { data: initBundle, isLoading: initLoading } = useQuery({
		queryKey: ['viewer', 'init', code],
		queryFn: () => fetchJson<InitResponse>(`/api/company/${code}/init?compact=true&limit=60`),
		staleTime: 5 * 60_000,
		enabled: !topic,
	});

	useEffect(() => {
		if (!initBundle) return;
		queryClient.setQueryData(['viewer', 'toc', code], initBundle.toc);
		if (initBundle.firstTopic && initBundle.viewer) {
			queryClient.setQueryData(
				['viewer', 'period', code, initBundle.firstTopic, null],
				initBundle.viewer,
			);
		}
	}, [initBundle, code, queryClient]);

	const { data: tocOnly, isLoading: tocOnlyLoading } = useQuery({
		queryKey: ['viewer', 'toc', code],
		queryFn: () => fetchJson<TocResponse>(`/api/company/${code}/toc`),
		staleTime: 5 * 60_000,
		enabled: !!topic,
	});

	const toc = initBundle?.toc ?? tocOnly;
	const tocLoading = topic ? tocOnlyLoading : initLoading;

	const firstTopic = useMemo(
		() => initBundle?.firstTopic ?? toc?.chapters?.[0]?.topics?.[0]?.topic,
		[initBundle?.firstTopic, toc],
	);
	const activeTopic = topic ?? firstTopic;

	useEffect(() => {
		if (!topic && firstTopic) {
			navigate({
				to: '/analysis/$code/viewer',
				params: { code },
				search: (prev) => ({
					period: prev?.period ?? 'quarterly',
					topic: firstTopic,
					windowEnd: prev?.windowEnd,
				}),
				replace: true,
			});
		}
	}, [topic, firstTopic, code, navigate]);

	// Phase 1 — latest fetch (period 없이) → td.periods + sections.
	const latestSeed =
		!topic && initBundle?.viewer && initBundle.firstTopic === activeTopic
			? initBundle.viewer
			: undefined;
	const { data: latestFetched } = useQuery({
		queryKey: ['viewer', 'period', code, activeTopic, null],
		queryFn: () =>
			fetchJson<ViewerResponse>(`/api/company/${code}/viewer/${activeTopic}?compact=true&limit=60`),
		enabled: !!activeTopic && !latestSeed,
		staleTime: 60_000,
	});
	const latestViewer = latestFetched ?? latestSeed;

	// 토픽의 모든 period (latest → first 내림차순).
	const allPeriods = useMemo<string[]>(() => {
		const ps = latestViewer?.textDocument?.periods ?? [];
		const labels = ps.map((p) => _periodLabel(p)).filter(Boolean);
		// 응답이 보통 desc 정렬되어 있지만 안전망.
		labels.sort((a, b) => b.localeCompare(a));
		return labels;
	}, [latestViewer]);

	// 현재 windowEnd — URL state 또는 latest.
	const effectiveWindowEnd = windowEnd && allPeriods.includes(windowEnd) ? windowEnd : allPeriods[0];
	const windowEndIdx = effectiveWindowEnd ? allPeriods.indexOf(effectiveWindowEnd) : -1;
	const windowPeriods = useMemo<string[]>(() => {
		if (windowEndIdx < 0) return [];
		return allPeriods.slice(windowEndIdx, windowEndIdx + WINDOW_SIZE);
	}, [allPeriods, windowEndIdx]);

	// Phase 2 — windowPeriods 의 viewer parallel.
	const windowQueries = useQueries({
		queries: windowPeriods.map((p) => ({
			queryKey: ['viewer', 'period', code, activeTopic, p],
			queryFn: () =>
				fetchJson<ViewerResponse>(
					`/api/company/${code}/viewer/${activeTopic}?compact=true&limit=60&period=${encodeURIComponent(p)}`,
				),
			enabled: !!activeTopic && !!p,
			staleTime: 60_000,
		})),
	});

	const windowViewers: Array<ViewerResponse | undefined> = windowQueries.map((q) => q.data);
	const windowLoading = windowQueries.some((q) => q.isLoading);

	const setWindowEnd = (next: string | undefined) => {
		navigate({
			to: '/analysis/$code/viewer',
			params: { code },
			search: (prev) => ({
				period: prev?.period ?? 'quarterly',
				topic: activeTopic,
				windowEnd: next,
			}),
			replace: false,
		});
	};

	// 좌우 이동 — index 1 증가 = 더 과거, 감소 = 더 미래.
	const moveOlder = () => {
		if (windowEndIdx < 0 || windowEndIdx + 1 >= allPeriods.length) return;
		setWindowEnd(allPeriods[windowEndIdx + 1]);
	};
	const moveNewer = () => {
		if (windowEndIdx <= 0) return;
		setWindowEnd(windowEndIdx === 1 ? undefined : allPeriods[windowEndIdx - 1]);
	};
	const canOlder = windowEndIdx >= 0 && windowEndIdx + 1 < allPeriods.length;
	const canNewer = windowEndIdx > 0;

	// 본문 sections — latest fetch 의 sections (heading 깊이 계산용).
	const ownLeafCore = _stripNumbering(latestViewer?.topicLabel || '');
	const allSections = latestViewer?.textDocument?.sections ?? [];
	const sectionsOwn = _filterToOwnLeaf(allSections, ownLeafCore);

	// period → dartUrl.
	const dartUrlByPeriod = useMemo(() => {
		const m: Record<string, string | null> = {};
		for (let i = 0; i < windowPeriods.length; i++) {
			const p = windowPeriods[i];
			const v = windowViewers[i];
			if (p) m[p] = v?.dartUrl ?? null;
		}
		return m;
	}, [windowPeriods, windowViewers]);

	const minLevel = useMemo(() => {
		let m = Number.POSITIVE_INFINITY;
		for (const s of sectionsOwn) {
			for (const h of s.headingPath ?? []) {
				const lvl = typeof h?.level === 'number' ? h.level : 0;
				if (lvl > 0 && lvl < m) m = lvl;
			}
		}
		return Number.isFinite(m) ? m : 1;
	}, [sectionsOwn]);

	// 헤더 시간축 — 전체 periods 의 update 상태 마커. timeline 데이터에서 status 계산.
	// 단순화 — sections 의 timeline 합쳐 각 period 의 변경 카운트.
	const changedSet = useMemo(() => {
		const s = new Set<string>();
		for (const sec of sectionsOwn) {
			for (const t of sec.timeline ?? []) {
				if (!t || !t.period) continue;
				const label = _periodLabel(t.period);
				if (label && (t.status === 'updated' || t.status === 'new' || t.status === 'stale')) {
					s.add(label);
				}
			}
		}
		return s;
	}, [sectionsOwn]);

	return (
		<div className="flex h-full overflow-hidden">
			{/* 좌 TOC */}
			<aside className="w-60 shrink-0 overflow-y-auto border-r bg-card/30 p-2 tiny-scroll">
				{tocLoading ? (
					<div className="flex items-center gap-2 p-3 text-xs text-muted-foreground">
						<Loader2 className="size-3 animate-spin" /> 목차 로드 중…
					</div>
				) : (
					<nav className="space-y-2">
						{toc?.chapters?.map((ch) => (
							<div key={ch.chapter}>
								<div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
									{ch.chapter}
								</div>
								<div className="space-y-0.5">
									{ch.topics?.map((t) => {
										const isActive = t.topic === activeTopic;
										return (
											<button
												key={t.topic}
												type="button"
												onClick={() =>
													navigate({
														to: '/analysis/$code/viewer',
														params: { code },
														search: (prev) => ({
															period: prev?.period ?? 'quarterly',
															topic: t.topic,
															windowEnd: undefined,
														}),
													})
												}
												className={cn(
													'flex w-full items-center gap-1.5 rounded px-2 py-1 text-left text-xs transition-colors',
													isActive
														? 'bg-accent text-accent-foreground'
														: 'text-muted-foreground hover:bg-accent/50',
												)}
											>
												<ChevronRight className="size-3 shrink-0 opacity-50" />
												<span className="truncate">{t.label || t.topicLabel || t.topic}</span>
											</button>
										);
									})}
								</div>
							</div>
						))}
					</nav>
				)}
			</aside>

			{/* 중앙 본문 */}
			<main className="min-w-0 flex-1 overflow-y-auto overflow-x-hidden">
				{!activeTopic ? (
					<div className="flex h-full items-center justify-center text-sm text-muted-foreground">
						왼쪽에서 항목을 선택하세요.
					</div>
				) : !latestViewer ? (
					<div className="flex h-full items-center justify-center gap-2 text-muted-foreground">
						<Loader2 className="size-5 animate-spin" /> 본문 로드 중…
					</div>
				) : (
					<div className="w-full px-2 py-4">
						<header className="mb-6 border-b pb-4">
							<div className="flex items-baseline justify-between gap-3">
								<div>
									<div className="text-xs text-muted-foreground">
										{latestViewer?.corpName} · {code}
									</div>
									<h1 className="mt-1 flex items-center gap-2 text-xl font-semibold tracking-tight">
										<FileText className="size-4 text-muted-foreground" />
										{latestViewer?.topicLabel || latestViewer?.topic || activeTopic}
									</h1>
								</div>
								<div className="text-[11px] text-muted-foreground">
									섹션 {sectionsOwn.length} · 전체 기간 {allPeriods.length}
								</div>
							</div>

							{/* 시간축 — 역순 라벨 리스트 + 윈도우 박스 오버레이 + 좌우 화살표.
							    왼쪽 화살표 = 더 최신 (리스트의 좌측), 오른쪽 화살표 = 더 과거 (리스트의 우측).
							    리스트가 newer→older 역순이라 화살표 방향과 이동 방향이 자연스럽게 일치. */}
							<TimelineRibbon
								periods={allPeriods}
								changedSet={changedSet}
								windowPeriods={windowPeriods}
								onPick={(p) => setWindowEnd(p === allPeriods[0] ? undefined : p)}
								onNewer={moveNewer}
								onOlder={moveOlder}
								canNewer={canNewer}
								canOlder={canOlder}
							/>
						</header>

						{/* 3-column header — period + DART link */}
						<div
							className="sticky top-0 z-10 mb-3 grid gap-3 border-b bg-background/95 py-2 backdrop-blur"
							style={{ gridTemplateColumns: `repeat(${WINDOW_SIZE}, minmax(0, 1fr))` }}
						>
							{windowPeriods.map((p) => {
								const url = dartUrlByPeriod[p];
								return (
									<div key={p} className="flex items-center justify-between gap-2 px-2">
										<div>
											<div className="font-mono text-xs font-semibold">{p}</div>
											<div className="text-[10px] text-muted-foreground">
												{changedSet.has(p) ? '변경 포함' : '동일'}
											</div>
										</div>
										{url && (
											<a
												href={url}
												target="_blank"
												rel="noreferrer noopener"
												title={`${p} 시점 DART 원본`}
												className="inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] text-muted-foreground hover:bg-accent"
											>
												<ExternalLink className="size-2.5" /> 원본
											</a>
										)}
									</div>
								);
							})}
						</div>

						{windowLoading && (
							<div className="my-3 flex items-center gap-2 text-xs text-muted-foreground">
								<Loader2 className="size-3 animate-spin" /> 윈도우 본문 로드 중…
							</div>
						)}

						{/* 본문 — 각 column 이 그 period 의 실제 보고서 sections 만 위아래로 독립 렌더.
						    row 정렬 폐기 — 2026Q1 이 "기재하지 않습니다" 1 줄이면 그 컬럼만 1 줄. */}
						<div
							className="grid gap-3"
							style={{ gridTemplateColumns: `repeat(${WINDOW_SIZE}, minmax(0, 1fr))` }}
						>
							{windowPeriods.map((p, i) => {
								const v = windowViewers[i];
								const periodSecs = (v?.textDocument?.sections ?? []).filter((s) => {
									if (!(s.timeline ?? []).some((t) => _periodLabel(t?.period) === p)) return false;
									// own-leaf 필터도 적용 — companyOverview 류 cross-contamination 차단.
									if (!ownLeafCore) return true;
									const path = s.headingPath ?? [];
									let foundRoot: string | null = null;
									for (const h of path) {
										const txt = typeof h === 'string' ? (h as string) : (h?.text || '');
										const core = _stripNumbering(txt);
										if (core && KNOWN_LEAF_ROOTS.has(core)) foundRoot = core;
									}
									return foundRoot === null || foundRoot === ownLeafCore;
								});
								return (
									<div key={p} className="min-w-0 space-y-5">
										{periodSecs.length === 0 ? (
											<p className="italic text-muted-foreground/50 text-[13px]">[본문 없음]</p>
										) : (
											periodSecs.map((s) => (
												<PeriodSection key={s.id} section={s} minLevel={minLevel} />
											))
										)}
									</div>
								);
							})}
						</div>
					</div>
				)}
			</main>
		</div>
	);
}

interface TimelineRibbonProps {
	periods: string[];
	changedSet: Set<string>;
	windowPeriods: string[];
	onPick: (p: string) => void;
	onNewer: () => void;
	onOlder: () => void;
	canNewer: boolean;
	canOlder: boolean;
}

function TimelineRibbon({
	periods,
	changedSet,
	windowPeriods,
	onPick,
	onNewer,
	onOlder,
	canNewer,
	canOlder,
}: TimelineRibbonProps) {
	if (periods.length === 0) return null;
	const winSet = new Set(windowPeriods);
	const windowStart = windowPeriods[0];
	const windowEnd = windowPeriods[windowPeriods.length - 1];
	return (
		<div className="mt-3 flex items-center gap-2">
			<button
				type="button"
				onClick={onNewer}
				disabled={!canNewer}
				title="더 최신으로"
				className={cn(
					'inline-flex size-7 shrink-0 items-center justify-center rounded border bg-card text-muted-foreground',
					canNewer ? 'hover:bg-accent' : 'opacity-30',
				)}
			>
				<ChevronLeft className="size-4" />
			</button>
			<div className="flex-1 overflow-x-auto tiny-scroll">
				<div className="flex items-stretch gap-px">
					{periods.map((p) => {
						const inWindow = winSet.has(p);
						const isStart = p === windowStart;
						const isEnd = p === windowEnd;
						const changed = changedSet.has(p);
						return (
							<button
								key={p}
								type="button"
								onClick={() => onPick(p)}
								title={`${p}${changed ? ' · 변경 포함' : ''}`}
								className={cn(
									'shrink-0 px-2 py-1 font-mono text-[10px] transition-colors border-y',
									inWindow
										? 'bg-accent text-accent-foreground border-accent-foreground/40'
										: 'border-transparent text-muted-foreground/60 hover:bg-accent/30',
									isStart && 'rounded-l border-l',
									isEnd && 'rounded-r border-r',
									changed && !inWindow && 'text-[var(--chart-2)]',
									changed && inWindow && 'font-semibold',
								)}
							>
								{p}
							</button>
						);
					})}
				</div>
			</div>
			<button
				type="button"
				onClick={onOlder}
				disabled={!canOlder}
				title="더 과거로"
				className={cn(
					'inline-flex size-7 shrink-0 items-center justify-center rounded border bg-card text-muted-foreground',
					canOlder ? 'hover:bg-accent' : 'opacity-30',
				)}
			>
				<ChevronRight className="size-4" />
			</button>
		</div>
	);
}

interface PeriodSectionProps {
	section: ViewerSection;
	minLevel: number;
}

function PeriodSection({ section, minLevel }: PeriodSectionProps) {
	const title = _sectionTitle(section);
	const { tag: HeadingTag, cls: headingCls } = title
		? _headingStyle(title.level || minLevel, minLevel)
		: { tag: 'h3' as const, cls: '' };
	const body = section.latest?.body ?? '';
	const paragraphs = _bodyParagraphs(body);
	return (
		<section className="min-w-0 scroll-mt-6" id={`sec-${section.id}`}>
			{title && <HeadingTag className={cn(headingCls, 'mb-1.5')}>{title.text}</HeadingTag>}
			<div className="text-[13px] leading-6 break-words">
				{paragraphs.length > 0 ? (
					<div className="space-y-2 text-foreground/90">
						{paragraphs.map((para, i) => (
							<p key={i} className="whitespace-pre-wrap">
								{para}
							</p>
						))}
					</div>
				) : (
					<p className="italic text-muted-foreground/50">[본문 기재 없음]</p>
				)}
			</div>
		</section>
	);
}

// Badge import 호환 — 다른 모듈에서 가져옴 (옛 코드 일부 잔존 케이스 차단).
export { Badge };
