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
import DOMPurify from 'dompurify';
import { ChevronLeft, ChevronRight, ExternalLink, FileText, Loader2, Maximize2, Minimize2 } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { useDashboardMode } from '@/features/dashboard/store/dashboardMode';
import { cn } from '@/lib/utils';

interface TocTopic {
	topic: string;
	label?: string;
	topicLabel?: string;
	textCount?: number;
	tableCount?: number;
	hasChanges?: boolean;
	children?: TocTopic[];
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

interface ViewerRow {
	blockOrder: number;
	blockType: string;
	textNodeType?: string | null;
	textLevel?: number | null;
	textPath?: string | null;
	segmentKey?: string;
	cells: Record<string, string>;
}

interface ViewerResponse {
	stockCode: string;
	corpName: string;
	topic: string;
	topicLabel?: string;
	compact?: boolean;
	period?: string | null;
	dartUrl?: string | null;
	rows?: ViewerRow[];
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
		entries?: Array<{
			kind: 'section' | 'block_ref';
			order?: number;
			sectionId?: string | null;
			blockRef?: number;
			blockKind?: string;
			headingPath?: ViewerHeading[];
		}>;
		tables?: Record<number, Record<string, string>>;
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

// 직전 active section 의 leaf 를 따라가며 1. 회사의 개요 / 2. 회사의 연혁 처럼
// 같은 chapter 안 여러 leaf 가 한 topic 응답에 섞여 오는 경우 (companyOverview)
// 사용자가 클릭한 leaf 의 sections 만 통과. headingPath 가 비어도 직전 state 유지.
const _NUMBERED_LEAF_RE = /^\s*(\d+)\.\s*([^\n]+?)\s*$/;
function _leafKey(text: string): string | null {
	const m = _NUMBERED_LEAF_RE.exec(text || '');
	if (!m) return null;
	return `${m[1]}.${m[2].trim()}`;
}
function _filterToOwnLeaf(allSections: ViewerSection[], ownLeafKey: string): ViewerSection[] {
	if (!ownLeafKey) return allSections;
	// 각 section 의 heading 안 numbered leaf 가 있으면 그 leaf 와 ownLeafKey 비교.
	// 매칭 ≠ 우리 = 그 *한 section* 만 drop. state 전파 안 함 — 가/나/다 sub-heading
	// section 들은 numbered heading 안 가지고 있어 자동으로 KEEP.
	return allSections.filter((s) => {
		const path = s.headingPath ?? [];
		for (const h of path) {
			const t = typeof h === 'string' ? (h as string) : (h?.text || '');
			const k = _leafKey(t);
			if (k && k !== ownLeafKey) return false;
		}
		return true;
	});
}

// (legacy _subOrder / _parseMarkdownTable / _bodyParagraphs / _sectionTitle / _headingStyle 제거 — SSOT rows[] 사용)

interface TocTopicNodeProps {
	node: TocTopic;
	activeTopic: string | undefined;
	code: string;
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	navigate: any;
	depth?: number;
}
function TocTopicNode({ node, activeTopic, code, navigate, depth = 0 }: TocTopicNodeProps) {
	const isActive = node.topic === activeTopic;
	const hasChildren = !!node.children && node.children.length > 0;
	const childActive = hasChildren && node.children!.some((c) => c.topic === activeTopic);
	const goTo = (t: string) =>
		navigate({
			to: '/analysis/$code/viewer',
			params: { code },
			search: (prev: { period?: string }) => ({
				period: prev?.period ?? 'quarterly',
				topic: t,
				windowEnd: undefined,
			}),
		});
	return (
		<div>
			<button
				type="button"
				onClick={() => goTo(node.topic)}
				className={cn(
					'flex w-full items-center gap-1.5 rounded px-2 py-1 text-left text-xs transition-colors',
					depth > 0 && 'pl-4',
					isActive
						? 'bg-accent text-accent-foreground'
						: childActive
							? 'text-foreground'
							: 'text-muted-foreground hover:bg-accent/50',
					hasChildren && 'font-semibold',
				)}
			>
				<ChevronRight className={cn('size-3 shrink-0 opacity-50', hasChildren && 'rotate-90')} />
				<span className="truncate">{node.label || node.topicLabel || node.topic}</span>
			</button>
			{hasChildren && (
				<div className="ml-2 mt-0.5 space-y-0.5 border-l border-border/40 pl-1">
					{node.children!.map((c) => (
						<TocTopicNode
							key={c.topic}
							node={c}
							activeTopic={activeTopic}
							code={code}
							navigate={navigate}
							depth={depth + 1}
						/>
					))}
				</div>
			)}
		</div>
	);
}

function ViewerTab() {
	const { code } = Route.useParams();
	const { topic, windowEnd } = Route.useSearch();
	const navigate = useNavigate();
	const queryClient = useQueryClient();
	const setLastMode = useDashboardMode((s) => s.setLastMode);

	// 종목 전환 시 직전 모드 복원에 사용. 본 탭 마운트 = viewer 모드 진입.
	useEffect(() => {
		setLastMode('viewer');
	}, [setLastMode]);

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

	// 토픽의 모든 period (latest → first 내림차순). is/bs 와 동일 — annual 은 Q4
	// 뒤로 (year, quarter=5) sort key 로 정렬. lexicographic localeCompare 는
	// '2025Q3' > '2025' 로 보아 사업보고서를 Q3 보고서 뒤에 두는 회귀 (사업보고서가
	// 가장 최신인데도 잘못된 위치에 박힘) → 명시 sort key 강제.
	const allPeriods = useMemo<string[]>(() => {
		const ps = latestViewer?.textDocument?.periods ?? [];
		const labels = ps.map((p) => _periodLabel(p)).filter(Boolean);
		const sortKey = (p: string): number => {
			const m = /^(\d{4})(Q([1-4]))?$/.exec(p);
			if (!m) return -1;
			const year = parseInt(m[1], 10);
			const q = m[3] ? parseInt(m[3], 10) : 5; // 연간 = Q4 뒤
			return year * 10 + q;
		};
		labels.sort((a, b) => sortKey(b) - sortKey(a));
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

	// 본문 sections — companyOverview 처럼 backend topic 이 chapter 전체 (1~6 leaf) 를
	// 한 응답에 묶어 보내는 경우가 있다. 사용자가 클릭한 leaf 의 sections 만 통과.
	// ownLeafKey = "1.회사의 개요" 같은 (번호.레이블) 키. TOC label 사용 (backend 의
	// viewer.topicLabel 은 번호 prefix 없어서 못 씀).
	const ownLeafKey = useMemo(() => {
		if (!toc || !activeTopic) return '';
		for (const ch of toc.chapters ?? []) {
			for (const t of ch.topics ?? []) {
				if (t.topic === activeTopic) {
					return _leafKey(t.label || t.topicLabel || '') || '';
				}
				for (const c of t.children ?? []) {
					if (c.topic === activeTopic) {
						return _leafKey(c.label || c.topicLabel || '') || '';
					}
				}
			}
		}
		return '';
	}, [toc, activeTopic]);
	const allSections = latestViewer?.textDocument?.sections ?? [];
	const sectionsOwn = useMemo(() => {
		const filtered = _filterToOwnLeaf(allSections, ownLeafKey);
		// dedupe by body 만 — backend sections frame 가 같은 stub 본문을 hp 있는 section +
		// hp 빈 section 2 개로 박는다. 같은 body 면 첫 번째만 keep (보통 hp 있는 게 먼저).
		// 빈 body 는 dedupe 안 함 (각자 독립 row 로 노출).
		const seen = new Set<string>();
		const out: ViewerSection[] = [];
		for (const s of filtered) {
			const body = (s.latest?.body || '').trim();
			if (!body) {
				out.push(s);
				continue;
			}
			if (seen.has(body)) continue;
			seen.add(body);
			out.push(s);
		}
		return out;
	}, [allSections, ownLeafKey]);
	// (legacy `sections` useMemo + bodyByIdByPeriod / ownIds / rows / tablesByBlock 모두 제거 — SSOT rows[] 사용)

	const dartUrlByPeriod = useMemo(() => {
		const m: Record<string, string | null> = {};
		for (let i = 0; i < windowPeriods.length; i++) {
			const p = windowPeriods[i];
			const v = windowViewers[i];
			if (p) m[p] = v?.dartUrl ?? null;
		}
		return m;
	}, [windowPeriods, windowViewers]);

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

	// 전체보기 토글 — TOC + 앱 chrome 숨김, 본문 viewport 100%.
	// fixed inset-0 z-50 로 외부 레이아웃 덮음 (부모 레이아웃 손대지 않음). ESC 로 복귀.
	const [isFullscreen, setIsFullscreen] = useState(false);
	useEffect(() => {
		if (!isFullscreen) return;
		const onKey = (e: KeyboardEvent) => {
			if (e.key === 'Escape') setIsFullscreen(false);
		};
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	}, [isFullscreen]);

	return (
		<div
			className={cn(
				'flex h-full min-h-0 overflow-hidden',
				isFullscreen && 'fixed inset-0 z-50 bg-background',
			)}
		>
			{/* 좌 TOC — 전체보기에서도 유지 (사용자 요청 — fullscreen 시 인덱스 같이 확장).
			   너비는 동일 (240px) 유지하되 fullscreen 모드 background 보강.
			   본문 (main) 만 scroll — sticky timeline 상단 고정. */}
			<aside
				className={cn(
					'w-60 shrink-0 overflow-y-auto border-r bg-card/30 p-2 tiny-scroll',
					isFullscreen && 'bg-card',
				)}
			>
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
									{ch.topics?.map((t) => (
										<TocTopicNode
											key={t.topic}
											node={t}
											activeTopic={activeTopic}
											code={code}
											navigate={navigate}
										/>
									))}
								</div>
							</div>
						))}
					</nav>
				)}
			</aside>

			{/* 중앙 본문 — main 자체는 overflow 없음. 본문 박스 안 ScrollArea 가 단일 vertical
			   scroll source. 이중스크롤 회피 — sticky timeline + 본문 ScrollArea 만 vertical. */}
			<main className="min-h-0 min-w-0 flex-1 overflow-x-hidden flex flex-col">
				{!activeTopic ? (
					<div className="flex h-full items-center justify-center text-sm text-muted-foreground">
						왼쪽에서 항목을 선택하세요.
					</div>
				) : !latestViewer ? (
					<div className="flex h-full items-center justify-center gap-2 text-muted-foreground">
						<Loader2 className="size-5 animate-spin" /> 본문 로드 중…
					</div>
				) : (
					<>
						{/* main 직속 자식 — wrapper div 없음. 상위 타임라인 + 토픽 제목 → 본문
						    스크롤 div. 옛 wrapper 의 pt-3 / overflow-hidden 이 본문 스크롤바를
						    우측 edge 에서 inset 시키던 박스 여백 회귀 fix. */}
						<div className="shrink-0 border-b bg-background px-3">
						<header className="pb-0 pt-2">
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
								<div className="flex items-center gap-3">
									<div className="text-[11px] text-muted-foreground">
										섹션 {sectionsOwn.length} · 전체 기간 {allPeriods.length}
									</div>
									<button
										type="button"
										onClick={() => setIsFullscreen((v) => !v)}
										title={isFullscreen ? '전체보기 해제 (Esc)' : '전체보기'}
										className="inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[11px] text-muted-foreground hover:bg-accent"
									>
										{isFullscreen ? <Minimize2 className="size-3" /> : <Maximize2 className="size-3" />}
										{isFullscreen ? '복귀' : '전체'}
									</button>
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

						</div>

						{windowLoading && (
							<div className="my-3 flex items-center gap-2 text-xs text-muted-foreground">
								<Loader2 className="size-3 animate-spin" /> 윈도우 본문 로드 중…
							</div>
						)}

						{/* 본문 영역 — 단순 overflow-y-auto + tiny-scroll. 박스/wrapper 없음.
						    스크롤바가 main 우측 끝에 위치 (px padding 본문 안쪽에). period header
						    는 본문 영역 안 sticky top-0 → 스크롤 시 column 라벨 + 원본 링크 상단 고정. */}
						<div className="min-h-0 flex-1 overflow-y-auto tiny-scroll">
							<div
								className="sticky top-0 z-10 grid gap-3 border-b bg-background px-3 py-2"
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
							{/* 본문 — sections SSOT rows (period × content) 직접 dumb render */}
							<div className="px-3 py-3">
								<SsotRowsView rows={latestViewer?.rows ?? []} windowPeriods={windowPeriods} />
							</div>
						</div>
					</>
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
			<div className="min-w-0 flex-1 overflow-x-auto tiny-scroll">
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

/**
 * sections SSOT row view — backend `rows: ViewerRow[]` (period × content) 직접 dumb render.
 *
 * operation.sectionsRefactor §12:
 * - 원본 보존: textPath / textLevel / blockOrder 원본 그대로
 * - 같은 의미 같은 row: 1 row × N period cells (path-anchored)
 * - dumb 소비: cells[period] 값 그대로 — paragraph re-split / heading 합성 0.
 *   blockType=table 인 cell 만 markdown table syntax → HTML table 변환 (시각 표시 용도).
 */

// DART HTML → 마크다운 평탄화 결과는 흔히 한 셀 안에 여러 sub-table 이 연결돼 있고,
// "(단위 : 백만원)" 같은 메타 텍스트 · "당기"/"전기"/"당분기"/"전분기"/"3개월"/"누적" 같은
// period label 이 데이터 cell 로 흡수돼 있다. 본 파서는 그것을 다음 단계로 정리한다.
//
//   1) `splitTableBlocks` — `| --- |` 구분선이 *데이터행 뒤에 또 등장* 하면 새 sub-table.
//   2) `extractUnit` — sub-table 첫 행들에서 `(단위`/`단위:` 패턴 발견 시 캡션으로 추출.
//   3) `extractPeriodLabel` — 첫 데이터 셀 값이 period label (당기/전기/당분기/...) 만 또는
//      label + 단위 인 경우 캡션으로 분리.
//
// 평탄 row 가 1 cell 만 가진 separator (`|  |`) 만 등장하면 빈 행 skip.

interface MarkdownSubTable {
	caption?: string;     // 표 위에 표시될 메타 텍스트 (당기 / 전기 등)
	unit?: string;        // 우측 상단 단위 (단위 : 백만원)
	rows: string[][];     // 데이터 그리드
}

// period 라벨 — "공시금액"/"장부금액" 같은 column 헤더는 caption 으로 흡수하지 않는다 (table 안 header row 로 유지).
const PERIOD_LABEL_RE = /^(?:당기|전기|당기말|전기말|당분기|전분기|당반기|전반기|당기누적|전기누적|3개월|누적|보고기간말)$/;
const UNIT_RE = /\(?\s*단위\s*[:：]?\s*[^\)]+\)?/;

function parseRawCells(line: string): string[] {
	return line.replace(/^\||\|$/g, '').split('|').map((c) => c.trim());
}

function parseMarkdownSubTables(md: string): MarkdownSubTable[] {
	const lines = md.split('\n').map((l) => l.trim()).filter((l) => l.startsWith('|'));
	const blocks: MarkdownSubTable[] = [];
	let cur: { rows: string[][] } = { rows: [] };

	const isSep = (cells: string[]) => cells.length > 0 && cells.every((c) => /^[:\-\s]*$/.test(c));
	const isAllEmpty = (cells: string[]) => cells.every((c) => c === '');

	const flush = () => {
		if (cur.rows.length === 0) return;
		blocks.push({ rows: cur.rows });
		cur = { rows: [] };
	};

	// sub-table 경계는 **빈 행** (`|  |`) 이지 separator (`| --- |`) 가 아니다.
	// markdown 표는 한 sub-table 안에서도 header row 와 data row 사이 separator 1 줄을 가진다
	// (GFM 문법). DART HTML → 마크다운 평탄화 결과는 multi-row header (caption / period+unit /
	// column header) 가 각자 `| --- |` 로 구분되지만 *논리적으로 같은 표*. separator 를
	// boundary 로 보면 헤더와 데이터가 다른 grid 로 떨어져 컬럼 폭 불일치 발생.
	//
	// 경계 규칙: 빈 행 (모든 셀 빈) 만 boundary. separator 는 그냥 skip.
	for (const line of lines) {
		const cells = parseRawCells(line);
		if (isAllEmpty(cells)) {
			flush();
			continue;
		}
		if (isSep(cells)) {
			continue;
		}
		cur.rows.push(cells);
	}
	flush();
	return blocks;
}

// sub-table 의 앞쪽 행들에서 캡션 (period label) + 단위 분리.
function refineSubTable(block: MarkdownSubTable): MarkdownSubTable {
	const rows = [...block.rows];
	let caption = block.caption;
	let unit = block.unit;

	// 첫 행이 단일 텍스트 행 (실질 셀 1 개) 이면 caption 후보.
	const consume = () => {
		if (rows.length === 0) return false;
		const first = rows[0];
		const nonEmpty = first.filter((c) => c !== '');
		if (nonEmpty.length === 0) {
			rows.shift();
			return true;
		}
		// (a) caption 전용 1 셀 — period label, "...에 대한 공시"/"...세부내역"/"...변동내역"
		//     같은 표 제목 패턴, 또는 짧은 한글 heading-like 텍스트 (≤25 자, 숫자 콤마 0).
		//     "공시금액"/"장부금액" 같은 컬럼 헤더는 length>=2 또는 다른 row 와 col 맞춰서
		//     별개 처리 — 흡수 X.
		const looksLikeHeading = (s: string): boolean => {
			if (s.length === 0 || s.length > 25) return false;
			if (/[\d,]/.test(s)) return false;
			return /[가-힣]/.test(s);
		};
		if (nonEmpty.length === 1) {
			const v = nonEmpty[0];
			if (PERIOD_LABEL_RE.test(v) || /(에 대한 공시|세부내역|변동내역|내역)$/.test(v) || looksLikeHeading(v)) {
				caption = caption ? `${caption} · ${v}` : v;
				rows.shift();
				return true;
			}
		}
		// (b) period label + 단위 두 셀 — 둘 다 prefix 메타.
		if (nonEmpty.length === 2) {
			const [a, b] = nonEmpty;
			if (PERIOD_LABEL_RE.test(a) && UNIT_RE.test(b)) {
				caption = caption ? `${caption} · ${a}` : a;
				unit = unit || b.replace(/^\(|\)$/g, '');
				rows.shift();
				return true;
			}
			if (UNIT_RE.test(a) && (!b || PERIOD_LABEL_RE.test(b))) {
				unit = unit || a.replace(/^\(|\)$/g, '');
				if (b) caption = caption ? `${caption} · ${b}` : b;
				rows.shift();
				return true;
			}
		}
		// (c) 행 안 어딘가 단위 표기만 있고 나머지 모두 empty
		if (nonEmpty.length === 1 && UNIT_RE.test(nonEmpty[0])) {
			unit = unit || nonEmpty[0].replace(/^\(|\)$/g, '');
			rows.shift();
			return true;
		}
		return false;
	};

	// 최대 4 행까지 caption/unit 흡수 시도 (DART 가 종종 2~3 행 메타 prefix).
	let safety = 4;
	while (safety-- > 0 && consume()) { /* loop */ }
	return { caption, unit, rows };
}

// DART 원본 HTML `<table rowspan colspan>` 직접 렌더 — sanitize 후 dangerouslySetInnerHTML.
// `_tableToMarkdown` 의 HTML 출력 (2026-05-26) 이후 신규 doc.parquet 의 table 본문은
// 마크다운 평탄화 결과 (`| ... |`) 가 아니라 원본 rowspan/colspan 그대로의 HTML 이다.
// DART 본문은 untrusted (CLAUDE.md L37) — DOMPurify 로 script/style/handler/iframe 모두 제거.
const SANITIZE_CONFIG = {
	ALLOWED_TAGS: ['table', 'thead', 'tbody', 'tfoot', 'tr', 'td', 'th', 'br', 'span', 'div', 'b', 'i', 'u', 'strong', 'em', 'sub', 'sup'],
	ALLOWED_ATTR: ['colspan', 'rowspan', 'class', 'align'],
};

function HtmlTable({ html, caption, unit }: { html: string; caption?: string; unit?: string }) {
	const cleanHtml = DOMPurify.sanitize(html, SANITIZE_CONFIG) as unknown as string;
	return (
		<div className="space-y-1">
			{(caption || unit) && (
				<div className="flex items-baseline justify-between gap-2 text-[11px]">
					<div className="font-medium text-foreground">{caption}</div>
					{unit && <div className="text-muted-foreground">{unit}</div>}
				</div>
			)}
			<div className="dartlab-html-table overflow-x-auto" dangerouslySetInnerHTML={{ __html: cleanHtml }} />
		</div>
	);
}

// HTML 본문에서 `<table>...</table>` block 추출 + 그 사이 텍스트도 보존.
// returns 원본 순서대로 ['html-table' | 'text', body] 묶음.
function splitHtmlAndText(value: string): Array<['html' | 'text', string]> {
	const out: Array<['html' | 'text', string]> = [];
	const re = /<table[\s\S]*?<\/table>/gi;
	let last = 0;
	let m: RegExpExecArray | null;
	while ((m = re.exec(value)) !== null) {
		if (m.index > last) {
			const before = value.slice(last, m.index).trim();
			if (before) out.push(['text', before]);
		}
		out.push(['html', m[0]]);
		last = m.index + m[0].length;
	}
	if (last < value.length) {
		const tail = value.slice(last).trim();
		if (tail) out.push(['text', tail]);
	}
	return out;
}

function CellContent({ value, blockType }: { value: string; blockType: string }) {
	if (!value) return null;
	// HTML `<table>` 본문 — 신규 doc.parquet (2026-05-26+) 이 rowspan/colspan 보존 HTML 으로 출력.
	if (blockType === 'table' && value.includes('<table')) {
		const parts = splitHtmlAndText(value);
		return (
			<div className="space-y-3">
				{parts.map(([kind, body], i) =>
					kind === 'html' ? (
						<HtmlTable key={i} html={body} />
					) : (
						<div key={i} className="whitespace-pre-wrap break-words text-xs text-muted-foreground">{body.replace(/&cr;/g, ' ')}</div>
					),
				)}
			</div>
		);
	}
	if (blockType === 'table' && value.includes('|')) {
		const blocks = parseMarkdownSubTables(value).map(refineSubTable).filter((b) => b.rows.length > 0 || b.caption || b.unit);
		if (blocks.length === 0) return <pre className="whitespace-pre-wrap break-words text-sm">{value}</pre>;
		return (
			<div className="space-y-3">
				{blocks.map((b, bi) => {
					const ncols = b.rows.length > 0 ? Math.max(...b.rows.map((r) => r.length)) : 0;
					return (
						<div key={bi} className="space-y-1">
							{(b.caption || b.unit) && (
								<div className="flex items-baseline justify-between gap-2 text-[11px]">
									<div className="font-medium text-foreground">{b.caption}</div>
									{b.unit && <div className="text-muted-foreground">{b.unit}</div>}
								</div>
							)}
							{b.rows.length > 0 && (
								<table className="w-full border-collapse text-xs">
									<tbody>
										{b.rows.map((r, ri) => {
											const padded = [...r];
											while (padded.length < ncols) padded.push('');
											return (
												<tr key={ri}>
													{padded.map((c, ci) => (
														<td key={ci} className="border border-border px-1.5 py-0.5 align-top font-normal">
															{c.replace(/&cr;/g, ' ')}
														</td>
													))}
												</tr>
											);
										})}
									</tbody>
								</table>
							)}
						</div>
					);
				})}
			</div>
		);
	}
	return <div className="whitespace-pre-wrap break-words text-sm">{value}</div>;
}

// row 가 visible window 안에 본문이 *하나라도* 있을 때만 렌더.
// DART 의 옛 기간 row 가 신규 topic 으로 따라붙어 visible window 에서는 모두 empty 인
// 경우가 흔하다 (consolidatedNotes_22_sga 68 row 중 2 row 만 2026Q1 본문 보유).
function hasVisibleContent(row: ViewerRow, windowPeriods: string[]): boolean {
	for (const p of windowPeriods) {
		const v = row.cells?.[p];
		if (typeof v === 'string' && v.trim().length > 0) return true;
	}
	return false;
}

// sections SSOT — row × period grid. 옛 기간 잔존 row 는 visible window 기준 filter.
function SsotRowsView({ rows, windowPeriods }: { rows: ViewerRow[]; windowPeriods: string[] }) {
	if (rows.length === 0) return null;
	const periodsToShow = windowPeriods.length > 0 ? windowPeriods : Object.keys(rows[0]?.cells ?? {}).slice(0, 3);
	const visible = rows.filter((r) => hasVisibleContent(r, periodsToShow));
	if (visible.length === 0) {
		return (
			<div className="py-6 text-center text-xs text-muted-foreground">
				선택한 기간에는 이 항목 본문이 없습니다. 타임라인에서 다른 기간을 선택하세요.
			</div>
		);
	}
	return (
		<div className="space-y-3">
			{visible.map((r) => (
				<div
					key={`${r.blockOrder}|${r.segmentKey ?? ''}`}
					className="grid gap-3"
					style={{ gridTemplateColumns: `repeat(${periodsToShow.length}, 1fr)` }}
				>
					{periodsToShow.map((p) => (
						<div key={p} className="min-w-0">
							<CellContent value={r.cells?.[p] ?? ''} blockType={r.blockType} />
						</div>
					))}
				</div>
			))}
		</div>
	);
}

// Badge import 호환 — 다른 모듈에서 가져옴 (옛 코드 일부 잔존 케이스 차단).
export { Badge };
