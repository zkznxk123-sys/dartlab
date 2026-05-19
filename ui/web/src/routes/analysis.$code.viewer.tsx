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
import { ChevronLeft, ChevronRight, ExternalLink, FileText, Loader2, Maximize2, Minimize2 } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { Badge } from '@/components/ui/badge';
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
		entries?: Array<{
			kind: 'section' | 'block_ref';
			order?: number;
			sectionId?: string | null;
			blockRef?: number;
			blockKind?: string;
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

// section body 또는 heading 에서 sub-order 추출 — 예 "6-1.", "6-2.", "6-3." 또는 "(1)", "(2)".
// backend entries 순서가 잘못 박힌 경우 (dividend 처럼 6-3 이 6-1 앞에 옴) 보정 용도.
function _subOrder(text: string): number | null {
	if (!text) return null;
	// "6-1.", "6-2." 같은 N-M. 패턴 우선
	const dash = /^\s*\d+-(\d+)\.\s/.exec(text);
	if (dash) return parseInt(dash[1], 10);
	// "(1)", "(2)" 패턴
	const paren = /^\s*\((\d+)\)\s/.exec(text);
	if (paren) return parseInt(paren[1], 10);
	return null;
}

// 단순 markdown 파이프 테이블 → 2D 배열. `| --- |` separator row 는 제거.
// 셀 안 `&cr;` 같은 HTML escape 는 backend 에서 이미 처리됐다고 가정.
function _parseMarkdownTable(md: string): string[][] {
	if (!md) return [];
	const lines = md
		.split(/\r?\n/)
		.map((l) => l.trim())
		.filter((l) => l.includes('|')); // leading | 없어도 OK — DART markdown 일부는 prefix 없음
	const rows: string[][] = [];
	for (const line of lines) {
		// separator row: `| --- | --- |` 또는 leading | 없는 `--- | ---`
		if (/^\|?\s*[-:|\s]+\|?\s*$/.test(line) && line.replace(/[|\s]/g, '').replace(/[-:]/g, '') === '') continue;
		const cells = line
			.replace(/^\|/, '')
			.replace(/\|$/, '')
			.split('|')
			.map((c) => c.trim());
		if (cells.length > 0) rows.push(cells);
	}
	return rows;
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
	// FIRST non-empty heading — DART headingPath 가 hierarchical 이 아니라 [own, inherited]
	// 순서로 박혀있는 케이스가 많아 마지막 을 쓰면 옆 section 의 heading 을 자기 것으로 오인.
	for (let i = 0; i < path.length; i++) {
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
	// 윈도우 3 period 중 한 곳이라도 timeline 에 포함되는 section 만 행으로 노출.
	const sections = useMemo(() => {
		if (windowPeriods.length === 0) return sectionsOwn;
		const ws = new Set(windowPeriods);
		return sectionsOwn.filter((s) =>
			(s.timeline ?? []).some((t) => ws.has(_periodLabel(t?.period))),
		);
	}, [sectionsOwn, windowPeriods]);

	// section.id → period → body. timeline 게이트로 stale 누설 차단.
	const bodyByIdByPeriod = useMemo(() => {
		const map: Record<string, Record<string, string | null>> = {};
		for (let i = 0; i < windowPeriods.length; i++) {
			const p = windowPeriods[i];
			const v = windowViewers[i];
			if (!p || !v) continue;
			const secs = v.textDocument?.sections ?? [];
			for (const s of secs) {
				const inPeriod = (s.timeline ?? []).some(
					(t) => _periodLabel(t?.period) === p,
				);
				if (!inPeriod) continue;
				if (!map[s.id]) map[s.id] = {};
				map[s.id][p] = s.latest?.body ?? null;
			}
		}
		return map;
	}, [windowPeriods, windowViewers]);

	// blockId → period → markdown (테이블). latest fetch 의 tables 사용 (period 무관).
	const tablesByBlock = latestViewer?.textDocument?.tables ?? {};

	// entries 순서대로 row 정의. latestViewer 가 SSOT — 본문 row 와 표 row 가 섞임.
	// row 가 section 이면 sectionsOwn 안에 있어야 통과 (leaf filter 거른 것).
	const ownIds = useMemo(() => new Set(sectionsOwn.map((s) => s.id)), [sectionsOwn]);
	const rows = useMemo(() => {
		const allEntries = latestViewer?.textDocument?.entries ?? [];
		const ws = new Set(windowPeriods);
		type Row = (
			| { kind: 'section'; id: string; section: ViewerSection }
			| { kind: 'table'; id: string; blockId: number; periodMd: Record<string, string> }
		) & { priority: number; subOrder: number; entryIdx: number };
		const out: Row[] = [];
		const secMap = new Map(sectionsOwn.map((s) => [s.id, s]));
		// priority: 윈도우 period index 중 가장 빠른 (=가장 newest) column 에 등장 → 작은 값.
		// 어디에도 안 보이면 dropped. 같은 priority 면 entry 순서 유지.
		const _firstWindowIdx = (periodsPresent: Set<string>): number => {
			for (let i = 0; i < windowPeriods.length; i++) {
				if (periodsPresent.has(windowPeriods[i])) return i;
			}
			return Number.POSITIVE_INFINITY;
		};
		for (let ei = 0; ei < allEntries.length; ei++) {
			const e = allEntries[ei];
			if (e.kind === 'section') {
				const sid = e.sectionId ?? '';
				if (!ownIds.has(sid)) continue;
				const s = secMap.get(sid)!;
				const tlSet = new Set((s.timeline ?? []).map((t) => _periodLabel(t?.period)).filter(Boolean));
				if (![...tlSet].some((p) => ws.has(p))) continue;
				const pri = _firstWindowIdx(tlSet);
				// sub-order — body 또는 첫 heading 에서 "N-M." 추출. backend entries 순서가
				// 잘못된 dividend 같은 topic 에서 6-1 → 6-2 → 6-3 정렬 회복.
				const titleText = _sectionTitle(s)?.text || '';
				const bodyText = s.latest?.body || '';
				const so = _subOrder(bodyText) ?? _subOrder(titleText) ?? Number.POSITIVE_INFINITY;
				out.push({ kind: 'section', id: `s-${sid}`, section: s, priority: pri, subOrder: so, entryIdx: ei });
			} else if (
				e.kind === 'block_ref' &&
				(e.blockKind === 'raw_markdown' || e.blockKind === 'finance' || e.blockKind === 'structured')
			) {
				const bid = e.blockRef;
				if (bid == null) continue;
				const pmd = tablesByBlock[bid];
				if (!pmd) continue;
				const tablePeriods = new Set(
					Object.entries(pmd).filter(([, v]) => (v ?? '').trim().length > 0).map(([p]) => p),
				);
				if (![...tablePeriods].some((p) => ws.has(p))) continue;
				const pri = _firstWindowIdx(tablePeriods);
				// 표는 sub-order 없음 — 표가 sub-section 본문 사이에 등장하면 그 section 의
				// subOrder 옆에 붙도록 entryIdx 만으로 자연 위치.
				out.push({ kind: 'table', id: `t-${bid}`, blockId: bid, periodMd: pmd, priority: pri, subOrder: Number.POSITIVE_INFINITY, entryIdx: ei });
			}
		}
		// sort 우선순위: (subOrder asc) → (priority asc) → (entryIdx asc).
		// subOrder 가 명시된 (6-1/6-2/6-3) section 이 *항상* 그 번호 순으로 먼저.
		// subOrder=∞ 인 section 들 중에선 window 의 newest period 등장 (priority 0) 우선.
		// 같은 priority 안에선 backend entryIdx 그대로.
		out.sort((a, b) => {
			if (a.subOrder !== b.subOrder) return a.subOrder - b.subOrder;
			if (a.priority !== b.priority) return a.priority - b.priority;
			return a.entryIdx - b.entryIdx;
		});
		return out;
	}, [latestViewer, sectionsOwn, ownIds, tablesByBlock, windowPeriods]);

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
		for (const s of sections) {
			for (const h of s.headingPath ?? []) {
				const lvl = typeof h?.level === 'number' ? h.level : 0;
				if (lvl > 0 && lvl < m) m = lvl;
			}
		}
		return Number.isFinite(m) ? m : 1;
	}, [sections]);

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
				'flex h-full overflow-hidden',
				isFullscreen && 'fixed inset-0 z-50 bg-background',
			)}
		>
			{/* 좌 TOC — 전체보기에서도 유지 (사용자 요청 — fullscreen 시 인덱스 같이 확장).
			   너비는 동일 (240px) 유지하되 fullscreen 모드 background 보강. */}
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
					<div className="w-full min-w-0 max-w-full overflow-hidden px-3 py-4">
						{/* 상위 타임라인 + 3-column period header 를 한 묶음으로 sticky.
						    스크롤 시에도 화면 상단에 고정 — 사용자가 본문 어디 보든 어느
						    period 인지 + 어느 topic 인지 + 시간축 이동 버튼 항상 보임.
						    전체보기 (isFullscreen) 모드 동일 동작. */}
						<div className="sticky top-0 z-20 -mx-3 mb-6 border-b bg-background/95 px-3 backdrop-blur">
						<header className="pb-2 pt-2">
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

						{/* 3-column header — period + DART link. 상위 sticky 묶음 안. */}
						<div
							className="grid gap-3 py-2"
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
					</div>
					{/* sticky 묶음 끝 */}

						{windowLoading && (
							<div className="my-3 flex items-center gap-2 text-xs text-muted-foreground">
								<Loader2 className="size-3 animate-spin" /> 윈도우 본문 로드 중…
							</div>
						)}

						{/* 본문 — entries 순서대로 row. section + table 섞임. 3 column 셀 */}
						{rows.length === 0 ? (
							<div className="rounded-md border border-dashed p-6 text-center text-xs text-muted-foreground">
								본문 데이터가 없습니다.
							</div>
						) : (
							<div className="space-y-6">
								{rows.map((r) =>
									r.kind === 'section' ? (
										<SectionRow
											key={r.id}
											section={r.section}
											windowPeriods={windowPeriods}
											bodyByPeriod={bodyByIdByPeriod[r.section.id] || {}}
											minLevel={minLevel}
										/>
									) : (
										<TableRow
											key={r.id}
											windowPeriods={windowPeriods}
											periodMd={r.periodMd}
										/>
									),
								)}
							</div>
						)}
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

interface SectionRowProps {
	section: ViewerSection;
	windowPeriods: string[];
	bodyByPeriod: Record<string, string | null>;
	minLevel: number;
}

function SectionRow({ section, windowPeriods, bodyByPeriod, minLevel }: SectionRowProps) {
	const title = _sectionTitle(section);
	const { tag: HeadingTag, cls: headingCls } = title
		? _headingStyle(title.level || minLevel, minLevel)
		: { tag: 'h3' as const, cls: '' };
	return (
		<section className="scroll-mt-6" id={`sec-${section.id}`}>
			<div
				className="grid gap-3"
				style={{ gridTemplateColumns: `repeat(${windowPeriods.length || 1}, minmax(0, 1fr))` }}
			>
				{windowPeriods.map((p) => {
					const body = bodyByPeriod[p];
					const paragraphs = _bodyParagraphs(body);
					const has = body !== undefined && body !== null && body !== '';
					return (
						<div key={p} className="min-w-0 text-[13px] leading-6 break-words">
							{title && has && (
								<HeadingTag className={cn(headingCls, 'mb-1.5')}>{title.text}</HeadingTag>
							)}
							{paragraphs.length > 0 ? (
								<div className="space-y-2 text-foreground/90">
									{paragraphs.map((para, i) => (
										<p key={i} className="whitespace-pre-wrap">
											{para}
										</p>
									))}
								</div>
							) : has ? (
								<p className="italic text-muted-foreground/50">[본문 없음]</p>
							) : (
								<p className="italic text-muted-foreground/30">—</p>
							)}
						</div>
					);
				})}
			</div>
		</section>
	);
}

interface TableRowProps {
	windowPeriods: string[];
	periodMd: Record<string, string>;
}

function TableRow({ windowPeriods, periodMd }: TableRowProps) {
	return (
		<section className="scroll-mt-6">
			<div
				className="grid gap-3"
				style={{ gridTemplateColumns: `repeat(${windowPeriods.length || 1}, minmax(0, 1fr))` }}
			>
				{windowPeriods.map((p) => {
					const md = periodMd[p];
					if (!md || !md.trim()) {
						return (
							<div key={p} className="min-w-0">
								<p className="italic text-muted-foreground/30 text-[13px]">—</p>
							</div>
						);
					}
					const rows = _parseMarkdownTable(md);
					if (rows.length === 0) {
						return (
							<div key={p} className="min-w-0">
								<p className="italic text-muted-foreground/40 text-[13px]">[표 파싱 실패]</p>
							</div>
						);
					}
					return (
						<div key={p} className="min-w-0 overflow-x-auto tiny-scroll">
							<table className="w-full border-collapse text-[12px]">
								<tbody>
									{rows.map((cells, ri) => (
										<tr key={ri} className="border-b border-border/40">
											{cells.map((c, ci) => (
												<td
													key={ci}
													className={cn(
														'border border-border/30 px-2 py-1 align-top break-words',
														ri === 0 && 'bg-muted/30 font-medium',
													)}
												>
													{c}
												</td>
											))}
										</tr>
									))}
								</tbody>
							</table>
						</div>
					);
				})}
			</div>
		</section>
	);
}

// Badge import 호환 — 다른 모듈에서 가져옴 (옛 코드 일부 잔존 케이스 차단).
export { Badge };
