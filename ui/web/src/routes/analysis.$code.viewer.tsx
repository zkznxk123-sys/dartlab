// /analysis/$code/viewer — 공시 뷰어.
// 좌: TOC 트리 (chapter > topic) · 중앙: 선택된 topic 의 sections 리스트 + preview · 우상: DART 원본.
//
// cold load 경로:
//   - URL 에 topic 없음 → GET /api/company/{code}/init?compact=true (TOC + firstTopic + viewer 1 RTT)
//   - URL 에 topic 있음 → /toc + /viewer/{topic}?compact=true 병렬 2 RTT (Company cold 1 회)
// 토픽 전환: /viewer/{topic}?compact=true&limit=60. compact 가 views/timeline/blocks 제거 (payload 80%+ 감소).

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

interface ViewerSection {
	id: string;
	order: string | number;
	headingPath: string[];
	latest?: Record<string, unknown> | null;
	latestPeriod?: { period?: string } | string | null;
	firstPeriod?: { period?: string } | string | null;
	periodCount?: number;
	status?: string;            // updated · new · stable · stale
	latestChange?: string;       // "2024Q1 ↔ 2023Q4" 식 표기
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

const STATUS_LABEL: Record<string, { label: string; tone: string }> = {
	updated: { label: '변경', tone: 'bg-[var(--chart-2)]/20 text-[var(--chart-2)]' },
	new: { label: '신규', tone: 'bg-[var(--chart-5)]/20 text-[var(--chart-5)]' },
	stale: { label: '제거', tone: 'bg-[var(--chart-3)]/20 text-[var(--chart-3)]' },
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
	const sections = td?.sections ?? [];

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
					<article className="mx-auto max-w-4xl px-6 py-6">
						<header className="mb-4 flex items-start justify-between gap-4 border-b pb-3">
							<div>
								<div className="text-xs text-muted-foreground">
									{viewer?.corpName} · {code}
								</div>
								<h1 className="mt-1 flex items-center gap-2 text-lg font-semibold">
									<FileText className="size-4 text-muted-foreground" />
									{viewer?.topicLabel || viewer?.topic || activeTopic}
								</h1>
								{td && (
									<div className="mt-2 flex flex-wrap items-center gap-1.5 text-[10px] text-muted-foreground">
										<Badge variant="secondary" className="font-normal text-[10px]">
											섹션 {td.sectionCount ?? sections.length}
										</Badge>
										{td.updatedCount ? (
											<Badge variant="secondary" className="bg-[var(--chart-2)]/20 text-[var(--chart-2)] font-normal text-[10px]">
												변경 {td.updatedCount}
											</Badge>
										) : null}
										{td.newCount ? (
											<Badge variant="secondary" className="bg-[var(--chart-5)]/20 text-[var(--chart-5)] font-normal text-[10px]">
												신규 {td.newCount}
											</Badge>
										) : null}
										{td.staleCount ? (
											<Badge variant="secondary" className="bg-[var(--chart-3)]/20 text-[var(--chart-3)] font-normal text-[10px]">
												제거 {td.staleCount}
											</Badge>
										) : null}
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
							<div className="space-y-3">
								{sections.map((s) => (
									<SectionItem key={s.id} section={s} />
								))}
								{td?.truncated && td?.totalSectionCount != null && (
									<div className="rounded-md border border-dashed p-3 text-center text-[11px] text-muted-foreground">
										… 그 외 {td.totalSectionCount - sections.length} 섹션. 필터/검색은 후속 PR.
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

function SectionItem({ section }: { section: ViewerSection }) {
	const status = section.status ?? '';
	const statusInfo = STATUS_LABEL[status];
	const heading = Array.isArray(section.headingPath)
		? section.headingPath.join(' › ')
		: String(section.headingPath ?? '');
	return (
		<section className="rounded-md border bg-card p-3">
			<div className="mb-1.5 flex items-baseline justify-between gap-2">
				<h3 className="truncate text-xs font-medium">{heading || section.id}</h3>
				<div className="flex shrink-0 items-center gap-1.5 font-mono text-[10px] text-muted-foreground">
					{statusInfo && (
						<span className={cn('rounded px-1.5 py-0.5 font-normal', statusInfo.tone)}>
							{statusInfo.label}
						</span>
					)}
					{section.latestChange && <span>{_periodLabel(section.latestChange) || String(section.latestChange)}</span>}
				</div>
			</div>
			{section.preview && (
				<div className="line-clamp-3 whitespace-pre-wrap text-[11px] leading-relaxed text-muted-foreground">
					{section.preview}
				</div>
			)}
		</section>
	);
}
