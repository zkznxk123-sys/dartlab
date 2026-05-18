// /analysis/$code/viewer — 공시 뷰어.
// 좌: TOC 트리 (chapter > topic) · 중앙: 본문 prose (최신 풀텍스트) · 우상: DART 원본.
//
// 본문은 진짜 읽히는 문서 (법조문 본문 + 시간축 패널 모델의 PR1):
//   - latest.body 풀텍스트를 단락 prose 로 렌더. preview (140 자 컷) 사용 X.
//   - heading 계층 = headingPath 마지막 항목 (h2/h3), 상위는 breadcrumb.
//   - stale (제거된) 섹션은 본문에서 제외 — 후속 PR 에서 우 history 패널의 lifecycle 영역으로.
//
// 데이터 fetch:
//   - cold load (URL 에 topic 없음) → /api/company/{code}/init?compact=true (TOC + firstTopic + viewer 1 RTT)
//   - URL 에 topic 있음 → /toc + /viewer/{topic}?compact=true 병렬
// compact 는 views (period 별 풀텍스트 dict) 만 drop — latest.body, timeline 은 유지 (PR2 우 패널 데이터 기반).

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { ChevronRight, ExternalLink, FileText, Loader2 } from 'lucide-react';
import { useEffect, useMemo } from 'react';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface TocTopic {
	topic: string;
	topicLabel?: string;
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

interface ViewerSection {
	id: string;
	order?: string | number;
	headingPath: ViewerHeading[];
	latest?: ViewerTextView | null;
	latestPeriod?: PeriodRef | string | null;
	firstPeriod?: PeriodRef | string | null;
	periodCount?: number;
	status?: string;            // updated · new · stable · stale
	latestChange?: string;       // "2024Q1 → 2023Q4" 식 표기
	preview?: string;
	timeline?: unknown[];
}

interface ViewerResponse {
	stockCode: string;
	corpName: string;
	topic: string;
	topicLabel?: string;
	compact?: boolean;
	textDocument?: {
		topic?: string;
		mode?: string;
		periods?: string[];
		latestPeriod?: string;
		totalSectionCount?: number;
		truncated?: boolean;
		firstPeriod?: string;
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
		const period = obj.period;
		if (typeof period === 'string' || typeof period === 'number') return String(period);
		const label = obj.label;
		if (typeof label === 'string') return label;
		const year = obj.year;
		const quarter = obj.quarter;
		if (year != null) return quarter != null ? `${year}Q${quarter}` : String(year);
	}
	return '';
}

// headingPath 가 객체 배열일 때 안전하게 텍스트만 추출.
function _headingTexts(path: ViewerHeading[] | undefined | null): string[] {
	if (!Array.isArray(path)) return [];
	return path
		.map((h) => (typeof h === 'string' ? (h as string) : (h?.text ?? '')))
		.filter((t) => typeof t === 'string' && t.trim().length > 0);
}

// latest.body 를 prose 단락으로 분리. 빈 줄 (\n\n) 경계 우선, 없으면 단일 줄바꿈.
function _bodyParagraphs(body: string | undefined | null): string[] {
	if (!body || !body.trim()) return [];
	const blocks = body
		.replace(/\r\n?/g, '\n')
		.split(/\n\s*\n+/);
	if (blocks.length > 1) {
		return blocks.map((b) => b.replace(/\s+/g, ' ').trim()).filter(Boolean);
	}
	return body
		.split('\n')
		.map((line) => line.replace(/\s+/g, ' ').trim())
		.filter(Boolean);
}

const STATUS_LABEL: Record<string, { label: string; tone: string }> = {
	updated: { label: '변경', tone: 'bg-[var(--chart-2)]/15 text-[var(--chart-2)]' },
	new: { label: '신규', tone: 'bg-[var(--chart-5)]/15 text-[var(--chart-5)]' },
	stale: { label: '제거', tone: 'bg-[var(--chart-3)]/15 text-[var(--chart-3)]' },
	stable: { label: '유지', tone: 'bg-muted text-muted-foreground' },
};

function ViewerTab() {
	const { code } = Route.useParams();
	const { topic } = Route.useSearch();
	const navigate = useNavigate();
	const queryClient = useQueryClient();

	// cold path: URL 에 topic 없으면 /init 한 번에 toc + firstTopic + viewer.
	const { data: initBundle, isLoading: initLoading } = useQuery({
		queryKey: ['viewer', 'init', code],
		queryFn: () => fetchJson<InitResponse>(`/api/company/${code}/init?compact=true&limit=60`),
		staleTime: 5 * 60_000,
		enabled: !topic,
	});

	// init 번들 도착 → toc / viewer 캐시 시드. URL 이 topic 으로 전환돼도 재요청 없음.
	useEffect(() => {
		if (!initBundle) return;
		queryClient.setQueryData(['viewer', 'toc', code], initBundle.toc);
		if (initBundle.firstTopic && initBundle.viewer) {
			queryClient.setQueryData(['viewer', 'topic', code, initBundle.firstTopic], initBundle.viewer);
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
				}),
				replace: true,
			});
		}
	}, [topic, firstTopic, code, navigate]);

	// init 번들이 firstTopic viewer 를 들고 있으면 초기값으로 활용 — fetch 없이 즉시 렌더.
	const initViewerSeed = !topic && initBundle?.viewer && initBundle.firstTopic === activeTopic
		? initBundle.viewer
		: undefined;

	const { data: viewerFetched, isLoading: viewerFetchLoading } = useQuery({
		queryKey: ['viewer', 'topic', code, activeTopic],
		queryFn: () => fetchJson<ViewerResponse>(`/api/company/${code}/viewer/${activeTopic}?compact=true&limit=60`),
		enabled: !!activeTopic && !initViewerSeed,
		staleTime: 60_000,
	});

	const viewer = viewerFetched ?? initViewerSeed;
	const viewerLoading = !viewer && (viewerFetchLoading || (!topic && initLoading));

	const td = viewer?.textDocument;
	const allSections = td?.sections ?? [];
	// 본문에는 활성 섹션만 — stale (제거된 항목) 은 후속 PR 의 우 history 패널에서 lifecycle 로.
	const sections = allSections.filter((s) => s.status !== 'stale');
	const staleHidden = allSections.length - sections.length;

	return (
		<div className="flex flex-1 overflow-hidden">
			<aside className="w-60 shrink-0 overflow-y-auto border-r bg-card/30 p-2">
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
												<span className="truncate">{t.topicLabel || t.topic}</span>
											</button>
										);
									})}
								</div>
							</div>
						))}
					</nav>
				)}
			</aside>

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
										{td.firstPeriod && td.latestPeriod && (
											<span className="ml-2 font-mono">
												{_periodLabel(td.firstPeriod)} → {_periodLabel(td.latestPeriod)}
											</span>
										)}
									</div>
								)}
							</div>
							<a
								href={`https://dart.fss.or.kr/dsab007/main.do?selectKey=${code}`}
								target="_blank"
								rel="noreferrer noopener"
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
							<div className="space-y-10">
								{sections.map((s) => (
									<DocumentSection key={s.id} section={s} />
								))}
								{td?.truncated && td?.totalSectionCount != null && (
									<div className="rounded-md border border-dashed p-3 text-center text-[11px] text-muted-foreground">
										… 그 외 {td.totalSectionCount - allSections.length} 섹션. 필터/검색은 후속 PR.
									</div>
								)}
							</div>
						)}
					</article>
				)}
			</main>
		</div>
	);
}

function DocumentSection({ section }: { section: ViewerSection }) {
	const status = section.status ?? '';
	const statusInfo = STATUS_LABEL[status];
	const headings = _headingTexts(section.headingPath);
	const title = headings[headings.length - 1] || section.id;
	const breadcrumb = headings.slice(0, -1).join(' › ');
	const lastHeading = section.headingPath?.[section.headingPath.length - 1];
	const headingLevel = typeof lastHeading?.level === 'number' && lastHeading.level >= 3 ? 3 : 2;

	const body = section.latest?.body ?? '';
	const paragraphs = _bodyParagraphs(body);
	// latest.body 가 없으면 (옛 payload 등) preview 로 fallback.
	const fallback = paragraphs.length === 0 && section.preview ? section.preview : null;

	const HeadingTag = headingLevel === 3 ? 'h3' : 'h2';
	const headingCls =
		headingLevel === 3
			? 'text-base font-semibold tracking-tight mt-2'
			: 'text-lg font-semibold tracking-tight mt-2';

	return (
		<section className="scroll-mt-6">
			{breadcrumb && (
				<div className="text-[11px] uppercase tracking-wider text-muted-foreground/80">
					{breadcrumb}
				</div>
			)}
			<div className="flex items-baseline justify-between gap-3">
				<HeadingTag className={headingCls}>{title}</HeadingTag>
				<div className="flex shrink-0 items-center gap-1.5 font-mono text-[10px] text-muted-foreground">
					{statusInfo && status !== 'stable' && (
						<span className={cn('rounded px-1.5 py-0.5 font-normal', statusInfo.tone)}>
							{statusInfo.label}
						</span>
					)}
					{section.latestChange && <span>{String(section.latestChange)}</span>}
				</div>
			</div>
			<div className="mt-3 space-y-3 text-[15px] leading-7 text-foreground/90">
				{paragraphs.length > 0
					? paragraphs.map((p, i) => (
							<p key={i} className="whitespace-pre-wrap">
								{p}
							</p>
					  ))
					: fallback
						? <p className="text-muted-foreground italic">{fallback}</p>
						: <p className="text-muted-foreground italic">본문 없음.</p>}
			</div>
		</section>
	);
}
