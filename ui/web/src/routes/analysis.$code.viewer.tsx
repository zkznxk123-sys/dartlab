// /analysis/$code/viewer — 공시 뷰어 3 단 구조 (법조문 모델).
// 좌 (TOC) | 중앙 (본문 prose) | 우 (history 패널 + 시점 전환).
//
// 본문은 진짜 읽히는 문서:
//   - latest.body 풀텍스트를 단락 prose 로 렌더. preview 컷 사용 X.
//   - heading 계층 = headingPath 마지막 text (h2/h3), 상위는 breadcrumb.
//   - body 가 비어있는 섹션은 [기재 없음] 로 mute 표시 — 우 패널에서 과거 시점 클릭 가능.
//
// 우 history 패널:
//   - 토픽 lifecycle (first → latest, 섹션 총합 / 활성 / 제거).
//   - 시점 list (latest → first). 클릭 → URL ?viewPeriod=X → backend 가
//     ?period=X&compact=true 로 그 시점 본문 반환. 본문 sticky 배너에
//     "[2022Q1 시점 보기] · 최신으로" 노출.
//   - "변경만 보기" 토글로 stable period 숨김.
//
// 스크롤 — 세 컬럼이 모두 독립 스크롤 (h-full overflow-hidden flex 의 자식 각각 overflow-y-auto).

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { ChevronRight, Clock, ExternalLink, FileText, History, Loader2 } from 'lucide-react';
import { useEffect, useMemo } from 'react';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface TocTopic {
	topic: string;
	label?: string;          // 백엔드 표준 — `safeTopicLabel` 결과 (한글)
	topicLabel?: string;     // 옛 field — 호환
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

interface ViewerTimelineEntry {
	period?: PeriodRef | null;
	prevPeriod?: PeriodRef | null;
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
	status?: string;            // updated · new · stable · stale
	latestChange?: string;
	preview?: string;
	timeline?: ViewerTimelineEntry[];
}

interface ViewerResponse {
	stockCode: string;
	corpName: string;
	topic: string;
	topicLabel?: string;
	compact?: boolean;
	period?: string | null;
	dartUrl?: string | null;  // 최신 정기보고서 DART 뷰어 URL (rcpNo 기반)
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
	viewPeriod?: string;
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
		viewPeriod: typeof s.viewPeriod === 'string' && s.viewPeriod ? s.viewPeriod : undefined,
	}),
});

async function fetchJson<T>(url: string): Promise<T> {
	const r = await fetch(url);
	if (!r.ok) throw new Error(`HTTP ${r.status} on ${url}`);
	return (await r.json()) as T;
}

// period 값이 dict 또는 string 둘 다 올 수 있음 — 안전 string 변환.
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

// DART 정기보고서 표준 leaf root headings — backend topic 간 cross-contamination 제거용.
// dartlab 의 `companyOverview` 응답이 "3. 자본금 변동사항" / "4. 주식의 총수 등" sections
// 까지 carjack 해서 들고 있는 데 그게 사실 다른 topic (capitalChange, shareCapital) 에
// 정상 존재한다. 이 set 에 매칭되는 *다른* leaf root 가 headingPath 에 있으면 그 section
// 은 현 topic 본문에서 제외.
const KNOWN_LEAF_ROOTS: ReadonlySet<string> = new Set([
	// I. 회사의 개요
	'회사의 개요', '회사의 연혁', '자본금 변동사항',
	'주식의 총수 등', '정관에 관한 사항', '배당에 관한 사항',
	// II. 사업의 내용
	'사업의 개요', '주요 제품 및 서비스', '원재료 및 생산설비',
	'매출 및 수주상황', '위험관리 및 파생거래', '주요계약 및 연구개발활동',
	'기타 참고사항',
	// III. 재무에 관한 사항
	'재무비율', '요약재무정보', '연결재무제표', '연결재무제표 주석',
	'재무제표', '재무제표 주석', '재무상태표', '손익계산서',
	'포괄손익계산서', '현금흐름표', '자본변동표',
]);

// 라벨 앞 번호 prefix 제거. "1. 회사의 개요" → "회사의 개요", "I. 회사의 개요" → "회사의 개요".
// 한글 가-하 번호 ("가.", "나.", ...) 도 제거.
function _stripNumbering(s: string): string {
	if (!s) return '';
	return s.replace(/^(?:\d+|[IVXivx]+|[가-하])\.\s*/, '').trim();
}

// section 의 headingPath 에 *다른* known leaf root 가 들어있으면 true (현 topic 에서 제외).
function _sectionBelongsToOtherLeaf(section: ViewerSection, ownLeafCore: string): boolean {
	const path = section.headingPath ?? [];
	if (path.length === 0) return false;
	for (const h of path) {
		const t = typeof h === 'string' ? (h as string) : (h?.text || '');
		const core = _stripNumbering(t);
		if (!core) continue;
		if (KNOWN_LEAF_ROOTS.has(core) && core !== ownLeafCore) {
			return true;
		}
	}
	return false;
}

// 본문을 단락 prose 로 분리. 빈 줄 우선, 없으면 단일 줄바꿈.
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

// section 의 실제 heading (headingPath 의 마지막 비어있지 않은 text). 없으면 null.
function _sectionTitle(section: ViewerSection): { text: string; level: number } | null {
	const path = section.headingPath ?? [];
	for (let i = path.length - 1; i >= 0; i--) {
		const h = path[i];
		const text = typeof h === 'string' ? (h as string) : h?.text ?? '';
		if (typeof text === 'string' && text.trim().length > 0) {
			const level = typeof h === 'object' && typeof h?.level === 'number' ? h.level : 0;
			return { text: text.trim(), level };
		}
	}
	return null;
}

// heading level (DART 데이터: I.→2, 1.→3, 가.→4 식) 를 display tag/style 로 매핑.
// 화면에 보이는 모든 headings 의 min level 을 1 로 정규화해 상대 hierarchy 유지.
function _headingStyle(level: number, minLevel: number): { tag: 'h1' | 'h2' | 'h3' | 'h4'; cls: string } {
	const rel = Math.max(1, level - minLevel + 1);
	if (rel <= 1) return { tag: 'h1', cls: 'text-2xl font-semibold tracking-tight' };
	if (rel === 2) return { tag: 'h2', cls: 'text-lg font-semibold tracking-tight' };
	if (rel === 3) return { tag: 'h3', cls: 'text-base font-semibold' };
	return { tag: 'h4', cls: 'text-sm font-semibold text-muted-foreground' };
}

const STATUS_LABEL: Record<string, { label: string; tone: string }> = {
	updated: { label: '변경', tone: 'bg-[var(--chart-2)]/15 text-[var(--chart-2)]' },
	new: { label: '신규', tone: 'bg-[var(--chart-5)]/15 text-[var(--chart-5)]' },
	stale: { label: '제거', tone: 'bg-[var(--chart-3)]/15 text-[var(--chart-3)]' },
	stable: { label: '유지', tone: 'bg-muted text-muted-foreground' },
};

function ViewerTab() {
	const { code } = Route.useParams();
	const { topic, viewPeriod } = Route.useSearch();
	const navigate = useNavigate();
	const queryClient = useQueryClient();

	// cold path: URL 에 topic 없으면 /init 한 번에 toc + firstTopic + viewer.
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
				['viewer', 'topic', code, initBundle.firstTopic, null],
				initBundle.viewer,
			);
		}
	}, [initBundle, code, queryClient]);

	// warm path: URL 에 topic 있으면 toc 만 별도 fetch (viewer 는 아래 useQuery 가 병렬).
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
					viewPeriod: prev?.viewPeriod,
				}),
				replace: true,
			});
		}
	}, [topic, firstTopic, code, navigate]);

	// 시점 전환 — viewPeriod 있으면 backend 에 ?period= 로 fetch, 없으면 최신.
	const periodQuery = viewPeriod ? `&period=${encodeURIComponent(viewPeriod)}` : '';
	const queryKey = ['viewer', 'topic', code, activeTopic, viewPeriod ?? null] as const;
	const initViewerSeed =
		!topic && !viewPeriod && initBundle?.viewer && initBundle.firstTopic === activeTopic
			? initBundle.viewer
			: undefined;

	const { data: viewerFetched, isLoading: viewerFetchLoading } = useQuery({
		queryKey,
		queryFn: () =>
			fetchJson<ViewerResponse>(
				`/api/company/${code}/viewer/${activeTopic}?compact=true&limit=60${periodQuery}`,
			),
		enabled: !!activeTopic && !initViewerSeed,
		staleTime: 60_000,
	});

	const viewer = viewerFetched ?? initViewerSeed;
	const viewerLoading = !viewer && (viewerFetchLoading || (!topic && initLoading));

	const td = viewer?.textDocument;
	const allSections = td?.sections ?? [];
	// leaf-level 필터: backend 의 `companyOverview` topic 응답이 다른 leaf (3.자본금변동/
	// 4.주식의총수 등) 의 sections 까지 carjack 해서 들고 있는 cross-contamination 이 있다.
	// headingPath 에 *다른 알려진 leaf root* 가 있는 sections 는 제외 — 현 topic 의 본
	// 내용만 본문에. stale 도 본문에 표시 (직전 사업보고서 기준 실제 정보).
	const ownLeafCore = _stripNumbering(viewer?.topicLabel || '');
	const sections = allSections.filter((s) => !_sectionBelongsToOtherLeaf(s, ownLeafCore));
	const staleHidden = sections.filter((s) => s.status === 'stale').length;

	const isPastView = !!viewPeriod;
	const topicLatestLabel = _periodLabel(td?.latestPeriod);
	const topicFirstLabel = _periodLabel(td?.firstPeriod);

	const setViewPeriod = (next: string | undefined) => {
		navigate({
			to: '/analysis/$code/viewer',
			params: { code },
			search: (prev) => ({
				period: prev?.period ?? 'quarterly',
				topic: activeTopic,
				viewPeriod: next,
			}),
			replace: false,
		});
	};

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
															viewPeriod: undefined,
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
			<main className="flex-1 overflow-y-auto">
				{!activeTopic ? (
					<div className="flex h-full items-center justify-center text-sm text-muted-foreground">
						왼쪽에서 항목을 선택하세요.
					</div>
				) : viewerLoading ? (
					<div className="flex h-full items-center justify-center gap-2 text-muted-foreground">
						<Loader2 className="size-5 animate-spin" /> 본문 로드 중…
					</div>
				) : (
					<>
						{isPastView && (
							<div className="sticky top-0 z-10 flex items-center justify-between gap-3 border-b border-amber-500/40 bg-amber-500/10 px-6 py-2 text-xs text-amber-100/90">
								<div className="flex items-center gap-2">
									<Clock className="size-3.5" />
									<span>
										<strong className="font-mono">{viewPeriod}</strong> 시점 본문 보는 중
									</span>
								</div>
								<button
									type="button"
									onClick={() => setViewPeriod(undefined)}
									className="rounded border border-amber-400/30 px-2 py-0.5 text-[10px] uppercase tracking-wider hover:bg-amber-500/20"
								>
									최신으로 돌아가기
								</button>
							</div>
						)}
						<article className="mx-auto max-w-3xl px-8 py-8">
							<header className="mb-8 flex items-start justify-between gap-4 border-b pb-4">
								<div>
									<div className="text-xs text-muted-foreground">
										{viewer?.corpName} · {code}
									</div>
									<h1 className="mt-1 flex items-center gap-2 text-xl font-semibold tracking-tight">
										<FileText className="size-4 text-muted-foreground" />
										{viewer?.topicLabel || viewer?.topic || activeTopic}
									</h1>
									{td && (
										<div className="mt-3 flex flex-wrap items-center gap-1.5 text-[10px] text-muted-foreground">
											<Badge variant="secondary" className="font-normal text-[10px]">
												섹션 {sections.length}
											</Badge>
											{td.updatedCount ? (
												<Badge variant="secondary" className="bg-[var(--chart-2)]/15 text-[var(--chart-2)] font-normal text-[10px]">
													변경 {td.updatedCount}
												</Badge>
											) : null}
											{td.newCount ? (
												<Badge variant="secondary" className="bg-[var(--chart-5)]/15 text-[var(--chart-5)] font-normal text-[10px]">
													신규 {td.newCount}
												</Badge>
											) : null}
											{staleHidden > 0 && (
												<Badge variant="outline" className="font-normal text-[10px] text-muted-foreground">
													제거 {staleHidden} (본문 제외)
												</Badge>
											)}
											{topicFirstLabel && topicLatestLabel && (
												<span className="ml-2 font-mono">
													{topicFirstLabel} → {topicLatestLabel}
												</span>
											)}
										</div>
									)}
								</div>
								<a
									href={
										viewer?.dartUrl ||
										`https://dart.fss.or.kr/dsab007/main.do?selectKey=${code}`
									}
									target="_blank"
									rel="noreferrer noopener"
									title={
										viewer?.dartUrl
											? '최신 정기보고서 DART 뷰어로 이동'
											: '회사 공시 검색 (최신 보고서 정보 없음 — fallback)'
									}
									className="inline-flex items-center gap-1 rounded-md border px-2.5 py-1 text-xs text-muted-foreground hover:bg-accent"
								>
									<ExternalLink className="size-3" /> DART 원본
								</a>
							</header>

							{sections.length === 0 ? (
								<div className="rounded-md border border-dashed p-6 text-center text-xs text-muted-foreground">
									본문 데이터가 없습니다.
								</div>
							) : (
								<DocumentBody sections={sections} />
							)}
							{td?.truncated && td?.totalSectionCount != null && (
								<div className="mt-10 rounded-md border border-dashed p-3 text-center text-[11px] text-muted-foreground">
									… 그 외 {td.totalSectionCount - allSections.length} 섹션. 필터/검색은 후속 PR.
								</div>
							)}
						</article>
					</>
				)}
			</main>

			{/* 우 history 패널 */}
			<aside className="hidden w-72 shrink-0 overflow-y-auto border-l bg-card/30 lg:block tiny-scroll">
				<HistoryPanel
					td={td}
					sections={allSections}
					staleHidden={staleHidden}
					viewPeriod={viewPeriod}
					onSelectPeriod={setViewPeriod}
				/>
			</aside>
		</div>
	);
}

// 본문 prose 컴포넌트 — sections 들을 자연 순서로 펼치되, body 없는 intermediate heading
// (다음 section 의 headingPath 에 pending 으로 끌려간 것) 도 자기 자체 entry 로 렌더.
// 결과: 1 → 2 (body 없음) → 3 → 4 → 가 (body 없음) → ... → 바 자연 흐름.
function DocumentBody({ sections }: { sections: ViewerSection[] }) {
	// 화면에 보일 모든 heading 의 min level 추출 — 상대 hierarchy 정규화용.
	const minLevel = useMemo(() => {
		let m = Number.POSITIVE_INFINITY;
		for (const s of sections) {
			for (const h of s.headingPath ?? []) {
				const lvl = typeof h?.level === 'number' ? h.level : 0;
				if (lvl > 0 && lvl < m) m = lvl;
			}
		}
		return Number.isFinite(m) ? m : 1;
	}, [sections]);

	const emitted = new Set<number>();
	const items: React.ReactNode[] = [];

	for (const section of sections) {
		const path = section.headingPath ?? [];
		// 마지막 heading 은 section 자체의 제목 — 그 위의 intermediate 들만 별 entry 로.
		for (let i = 0; i < path.length - 1; i++) {
			const h = path[i];
			const blockId = typeof h === 'object' && typeof h?.block === 'number' ? h.block : null;
			const text = typeof h === 'object' ? (h?.text ?? '') : (h as unknown as string);
			if (!text || (blockId != null && emitted.has(blockId))) continue;
			if (blockId != null) emitted.add(blockId);
			const level = typeof h === 'object' && typeof h?.level === 'number' ? h.level : 0;
			items.push(
				<EmptyHeading
					key={`h-${blockId ?? i}-${section.id}`}
					text={text}
					level={level}
					minLevel={minLevel}
				/>,
			);
		}
		const last = path[path.length - 1];
		const lastBlockId = typeof last === 'object' && typeof last?.block === 'number' ? last.block : null;
		if (lastBlockId != null) emitted.add(lastBlockId);
		items.push(<DocumentSection key={section.id} section={section} minLevel={minLevel} />);
	}

	return <div className="space-y-8">{items}</div>;
}

// body 없는 heading — 그 자체로 한 줄 자리만 차지. "기재 없음" 한 줄 mute 표시.
function EmptyHeading({
	text,
	level,
	minLevel,
}: {
	text: string;
	level: number;
	minLevel: number;
}) {
	const { tag: Tag, cls } = _headingStyle(level || minLevel, minLevel);
	return (
		<section className="border-l-2 border-muted/40 pl-4">
			<Tag className={cn(cls, 'text-muted-foreground')}>{text}</Tag>
			<p className="mt-1 text-[12px] italic text-muted-foreground/70">하위 본문 없음</p>
		</section>
	);
}

function DocumentSection({ section, minLevel }: { section: ViewerSection; minLevel: number }) {
	const status = section.status ?? '';
	const statusInfo = STATUS_LABEL[status];
	const title = _sectionTitle(section);
	const body = section.latest?.body ?? '';
	const paragraphs = _bodyParagraphs(body);

	const { tag: HeadingTag, cls: headingCls } = title
		? _headingStyle(title.level || minLevel, minLevel)
		: { tag: 'h2' as const, cls: '' };

	return (
		<section className="scroll-mt-6" id={`sec-${section.id}`}>
			{title && (
				<div className="flex items-baseline justify-between gap-3">
					<HeadingTag className={headingCls}>{title.text}</HeadingTag>
					<div className="flex shrink-0 items-center gap-1.5 font-mono text-[10px] text-muted-foreground">
						{statusInfo && status !== 'stable' && (
							<span className={cn('rounded px-1.5 py-0.5 font-normal', statusInfo.tone)}>
								{statusInfo.label}
							</span>
						)}
						{section.latestChange && <span>{String(section.latestChange)}</span>}
					</div>
				</div>
			)}
			<div className="mt-3 space-y-3 text-[15px] leading-7 text-foreground/90">
				{paragraphs.length > 0 ? (
					paragraphs.map((p, i) => (
						<p key={i} className="whitespace-pre-wrap">
							{p}
						</p>
					))
				) : (
					<p className="text-muted-foreground italic">[본문 기재 없음]</p>
				)}
			</div>
		</section>
	);
}

interface HistoryPanelProps {
	td: ViewerResponse['textDocument'];
	sections: ViewerSection[];
	staleHidden: number;
	viewPeriod: string | undefined;
	onSelectPeriod: (p: string | undefined) => void;
}

function HistoryPanel({ td, sections, staleHidden, viewPeriod, onSelectPeriod }: HistoryPanelProps) {
	// 토픽 전체 period list — td.periods 우선, 없으면 모든 section timeline 합집합.
	const periods = useMemo<PeriodRef[]>(() => {
		if (td?.periods && td.periods.length > 0) return td.periods;
		const seen = new Map<string, PeriodRef>();
		for (const s of sections) {
			for (const t of s.timeline ?? []) {
				const p = t.period as PeriodRef | null | undefined;
				if (!p) continue;
				const label = _periodLabel(p);
				if (label && !seen.has(label)) seen.set(label, p);
			}
		}
		return Array.from(seen.values());
	}, [td?.periods, sections]);

	// latest → first 내림차순 정렬 (sortKey 우선).
	const sortedPeriods = useMemo(() => {
		const withKey = periods.map((p) => ({
			period: p,
			label: _periodLabel(p),
			sortKey: typeof (p as { sortKey?: number }).sortKey === 'number'
				? (p as { sortKey?: number }).sortKey!
				: (p.year ?? 0) * 10 + (p.quarter ?? 5),
		}));
		withKey.sort((a, b) => b.sortKey - a.sortKey);
		return withKey;
	}, [periods]);

	// 각 period 에서 일어난 status 카운트 (union of section timelines).
	const periodStats = useMemo(() => {
		const map = new Map<string, { added: number; updated: number; removed: number; total: number }>();
		for (const s of sections) {
			for (const t of s.timeline ?? []) {
				const p = t.period as PeriodRef | null | undefined;
				if (!p) continue;
				const label = _periodLabel(p);
				if (!label) continue;
				const slot = map.get(label) ?? { added: 0, updated: 0, removed: 0, total: 0 };
				slot.total += 1;
				if (t.status === 'new') slot.added += 1;
				else if (t.status === 'updated') slot.updated += 1;
				else if (t.status === 'stale') slot.removed += 1;
				map.set(label, slot);
			}
		}
		return map;
	}, [sections]);

	const totalSections = (td?.sectionCount ?? td?.totalSectionCount ?? sections.length) || 0;

	if (!td) {
		return (
			<div className="p-4 text-xs text-muted-foreground">
				토픽 데이터 로드 후 시간축이 표시됩니다.
			</div>
		);
	}

	return (
		<div className="flex flex-col gap-4 p-3">
			<div>
				<div className="mb-1 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
					<History className="size-3" /> 시간축
				</div>
				<div className="text-[11px] leading-relaxed text-muted-foreground">
					<div>
						<span className="font-mono">{_periodLabel(td.firstPeriod) || '?'}</span>
						<span className="mx-1">→</span>
						<span className="font-mono">{_periodLabel(td.latestPeriod) || '?'}</span>
					</div>
					<div className="mt-1">
						활성 {sections.length - staleHidden} · 제거 {staleHidden} · 총 {totalSections}
					</div>
				</div>
			</div>

			<div className="border-t pt-3">
				<div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
					시점 보기
				</div>
				<div className="space-y-0.5">
					<button
						type="button"
						onClick={() => onSelectPeriod(undefined)}
						className={cn(
							'flex w-full items-center justify-between gap-2 rounded px-2 py-1.5 text-left text-xs transition-colors',
							!viewPeriod
								? 'bg-accent text-accent-foreground'
								: 'text-muted-foreground hover:bg-accent/50',
						)}
					>
						<span className="font-medium">최신</span>
						<span className="font-mono text-[10px] opacity-70">
							{_periodLabel(td.latestPeriod)}
						</span>
					</button>
					{sortedPeriods.map(({ label }) => {
						if (!label) return null;
						const isActive = viewPeriod === label;
						const stats = periodStats.get(label);
						const noChange = stats && stats.added + stats.updated + stats.removed === 0;
						return (
							<button
								key={label}
								type="button"
								onClick={() => onSelectPeriod(label)}
								className={cn(
									'flex w-full items-center justify-between gap-2 rounded px-2 py-1.5 text-left text-xs transition-colors',
									isActive
										? 'bg-accent text-accent-foreground'
										: 'text-muted-foreground hover:bg-accent/50',
								)}
							>
								<span className="font-mono">{label}</span>
								<span className="flex items-center gap-1 text-[10px]">
									{stats?.added ? (
										<span className="text-[var(--chart-5)]">+{stats.added}</span>
									) : null}
									{stats?.updated ? (
										<span className="text-[var(--chart-2)]">~{stats.updated}</span>
									) : null}
									{stats?.removed ? (
										<span className="text-[var(--chart-3)]">−{stats.removed}</span>
									) : null}
									{noChange && <span className="opacity-40">·</span>}
								</span>
							</button>
						);
					})}
				</div>
			</div>
		</div>
	);
}
