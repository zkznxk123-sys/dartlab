// /analysis/$code/viewer — 공시 뷰어 (panel SSOT — 항목 × 기간 wide 격자).
//
// 모델 (panel = 데이터+구조 SSOT):
//   - 좌 TOC: chapter > sectionLeaf (panel index 트리). 클릭 단위 = sectionLeaf.
//   - 헤더: 전체 시간축 (toc.periods) + 현재 윈도우 3 period + 좌우 이동.
//   - 본문: panel grid 의 행(항목) × period column. 셀 = raw DART XML (tag=True 무손실).
//   - diff/timeline/캡션 = 순수 UI (인접 period 셀 비교 + window slice). 백엔드 계산 0.
//
// 서버는 panel wide 를 JSON 직렬화만 — 중간 표현 레이어 없음.
// fetch:
//   - cold: /api/company/{code}/panel/init (toc + 첫 절 full-period grid)
//   - 절 전환: /api/company/{code}/panel?section={sectionKey} (full-period grid 1회)
//   - URL ?section={sectionKey}&windowEnd={period}

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import DOMPurify from 'dompurify';
import { ChevronLeft, ChevronRight, ExternalLink, FileText, Loader2, Maximize2, Minimize2 } from 'lucide-react';
import { useEffect, useMemo, useState, type ReactElement } from 'react';

import { Badge } from '@/components/ui/badge';
import {
	fetchPanelGrid,
	fetchPanelInit,
	fetchPanelToc,
	type PanelGridResponse,
	type PanelRow,
	type PanelTocResponse,
} from '@/features/dashboard/api/client';
import { useDashboardMode } from '@/features/dashboard/store/dashboardMode';
import { cn } from '@/lib/utils';

interface ViewerSearch {
	section?: string; // sectionKey ({chapter}␟{sectionLeaf}) — 옛 ?topic= 대체
	windowEnd?: string;
}

export const Route = createFileRoute('/analysis/$code/viewer')({
	component: ViewerTab,
	validateSearch: (s: Record<string, unknown>): ViewerSearch => ({
		section: typeof s.section === 'string' && s.section ? s.section : undefined,
		windowEnd: typeof s.windowEnd === 'string' && s.windowEnd ? s.windowEnd : undefined,
	}),
});

const WINDOW_SIZE = 3;
const SECTION_KEY_SEP = '␟';

// ── panel 셀 렌더 (raw DART XML → sanitize) ──

// panel 셀은 raw DART XML (tag=True, 무손실) — 대문자 정부 태그 (<TABLE>/<TE ACODE…>/<P>/<TITLE>).
// 브라우저 렌더 + DOMPurify(소문자 허용) 통과를 위해 표준 html 태그로 정규화 (순수 렌더 디테일).
// ACODE/ACONTEXT 등 정부 메타 속성은 제거하고 표 구조 속성(colspan/rowspan/align)만 보존.
const _DART_TAG_MAP: Record<string, string> = {
	'TABLE-GROUP': 'div',
	TABLE: 'table',
	THEAD: 'thead',
	TBODY: 'tbody',
	TR: 'tr',
	TH: 'th',
	TU: 'th',
	TE: 'td',
	TD: 'td',
	P: 'div',
	SPAN: 'span',
	TITLE: 'div',
	BR: 'br',
};
function normalizeDartXml(value: string): string {
	if (!value || value.indexOf('<') < 0) return value;
	return value.replace(/<(\/?)([A-Za-z][\w-]*)((?:\s[^>]*)?)\s*\/?>/g, (_m, slash: string, tag: string, attrs: string) => {
		const upper = tag.toUpperCase();
		const name = _DART_TAG_MAP[upper] ?? tag.toLowerCase();
		let keep = '';
		if (!slash && attrs) {
			const am = attrs.match(/\b(colspan|rowspan|align)\s*=\s*("[^"]*"|'[^']*'|\S+)/gi);
			if (am) keep = ' ' + am.join(' ');
		}
		return `<${slash}${name}${keep}>`;
	});
}

// DART 본문은 untrusted (CLAUDE.md) — DOMPurify 로 script/style/handler/iframe 모두 제거.
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

// HTML <table> 직전 paragraph 가 (단위 …) / 회기 일자 / period label 패턴이면 표 caption/unit 흡수.
const _PERIOD_DATE_RE = /^제\s*\d+\s*기/;
function absorbCaptionUnitFromText(textBefore: string): { caption: string; unit: string; remaining: string } {
	const lines = textBefore.split('\n').map((l) => l.trim()).filter(Boolean);
	let caption = '';
	let unit = '';
	const remaining: string[] = [];
	for (const line of lines) {
		if (UNIT_RE.test(line) && line.length < 40) {
			if (!unit) unit = line.replace(/^\(|\)$/g, '');
			continue;
		}
		if (PERIOD_LABEL_RE.test(line)) {
			caption = caption ? `${caption} · ${line}` : line;
			continue;
		}
		if (_PERIOD_DATE_RE.test(line) && line.length < 80) {
			caption = caption ? `${caption} · ${line}` : line;
			continue;
		}
		remaining.push(line);
	}
	return { caption, unit, remaining: remaining.join('\n') };
}

// ── markdown sub-table 파서 (옛 셀 호환 — panel raw XML 엔 드묾) ──

interface MarkdownSubTable {
	caption?: string;
	unit?: string;
	rows: string[][];
}

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
	for (const line of lines) {
		const cells = parseRawCells(line);
		if (isAllEmpty(cells)) {
			flush();
			continue;
		}
		if (isSep(cells)) continue;
		cur.rows.push(cells);
	}
	flush();
	return blocks;
}

function refineSubTable(block: MarkdownSubTable): MarkdownSubTable {
	const rows = [...block.rows];
	let caption = block.caption;
	let unit = block.unit;
	const consume = () => {
		if (rows.length === 0) return false;
		const first = rows[0];
		const nonEmpty = first.filter((c) => c !== '');
		if (nonEmpty.length === 0) {
			rows.shift();
			return true;
		}
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
		if (nonEmpty.length === 1 && UNIT_RE.test(nonEmpty[0])) {
			unit = unit || nonEmpty[0].replace(/^\(|\)$/g, '');
			rows.shift();
			return true;
		}
		return false;
	};
	let safety = 4;
	while (safety-- > 0 && consume()) {
		/* loop */
	}
	return { caption, unit, rows };
}

// panel 셀 (raw DART XML) 단일 렌더. blockType 없이 content-sniffing.
function CellContent({ value }: { value: string }) {
	if (!value || !value.trim()) return null;
	// 옛 markdown table 호환 경로 (raw XML 엔 거의 없음).
	if (value.includes('|') && /\n\s*\|/.test(value) && !/<\s*[a-zA-Z]/.test(value)) {
		const blocks = parseMarkdownSubTables(value).map(refineSubTable).filter((b) => b.rows.length > 0 || b.caption || b.unit);
		if (blocks.length > 0) {
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
	}
	const html = normalizeDartXml(value);
	// 표 포함 — table block 추출 + 사이 텍스트 + caption/unit 흡수.
	if (/<\s*table[\s>]/i.test(html)) {
		const parts = splitHtmlAndText(html);
		const elements: ReactElement[] = [];
		let pendingCaption = '';
		let pendingUnit = '';
		parts.forEach(([kind, body], i) => {
			if (kind === 'text') {
				const { caption, unit, remaining } = absorbCaptionUnitFromText(stripInlineTags(body));
				if (caption) pendingCaption = pendingCaption ? `${pendingCaption} · ${caption}` : caption;
				if (unit) pendingUnit = pendingUnit || unit;
				if (remaining) {
					elements.push(
						<div key={i} className="whitespace-pre-wrap break-words text-xs text-muted-foreground">
							{remaining.replace(/&cr;/g, ' ')}
						</div>,
					);
				}
			} else {
				elements.push(<HtmlTable key={i} html={body} caption={pendingCaption || undefined} unit={pendingUnit || undefined} />);
				pendingCaption = '';
				pendingUnit = '';
			}
		});
		if (pendingCaption || pendingUnit) {
			elements.push(
				<div key="trailing-caption" className="flex items-baseline justify-between gap-2 text-[11px]">
					<div className="font-medium text-foreground">{pendingCaption}</div>
					{pendingUnit && <div className="text-muted-foreground">{pendingUnit}</div>}
				</div>,
			);
		}
		return <div className="space-y-3">{elements}</div>;
	}
	// narrative / inline 태그 — sanitize 후 렌더. 태그 없으면 pre-wrap 텍스트.
	if (!/<[a-zA-Z]/.test(html)) {
		return <div className="whitespace-pre-wrap break-words text-sm">{html.replace(/&cr;/g, ' ')}</div>;
	}
	const clean = DOMPurify.sanitize(html, SANITIZE_CONFIG) as unknown as string;
	return <div className="dartlab-html-text break-words text-sm leading-relaxed [&_div]:mb-1" dangerouslySetInnerHTML={{ __html: clean }} />;
}

// 인라인 태그 strip (텍스트 조각의 caption/unit 패턴 매칭용).
function stripInlineTags(s: string): string {
	return s.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
}

// ── diff (프론트 인접셀 비교) ──

function cellStatus(row: PanelRow, period: string, allPeriods: string[]): 'new' | 'changed' | 'same' {
	const cur = (row.cells[period] ?? '').trim();
	if (!cur) return 'same';
	const idx = allPeriods.indexOf(period);
	const prevP = idx >= 0 ? allPeriods[idx + 1] : undefined;
	const prev = prevP ? (row.cells[prevP] ?? '').trim() : '';
	if (!prev) return 'new';
	return cur !== prev ? 'changed' : 'same';
}

function rowKey(r: PanelRow): string {
	const id = r.disclosureKey ?? `NARR::${r.chapter}${SECTION_KEY_SEP}${r.sectionLeaf}${SECTION_KEY_SEP}${r.blockLeaf}`;
	return `${id}|${r.scope ?? ''}`;
}

// row 가 visible window 안에 본문이 하나라도 있을 때만 렌더 (옛 기간 ghost row 차단).
function hasVisibleContent(row: PanelRow, windowPeriods: string[]): boolean {
	for (const p of windowPeriods) {
		const v = row.cells?.[p];
		if (typeof v === 'string' && v.trim().length > 0) return true;
	}
	return false;
}

// panel grid — row × period. window 기준 filter + 인접셀 diff 배지.
function SsotRowsView({ rows, windowPeriods, allPeriods }: { rows: PanelRow[]; windowPeriods: string[]; allPeriods: string[] }) {
	if (rows.length === 0) return null;
	const periodsToShow = windowPeriods.length > 0 ? windowPeriods : Object.keys(rows[0]?.cells ?? {}).slice(0, WINDOW_SIZE);
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
				<div key={rowKey(r)} className="grid gap-3" style={{ gridTemplateColumns: `repeat(${periodsToShow.length}, 1fr)` }}>
					{periodsToShow.map((p) => {
						const st = cellStatus(r, p, allPeriods);
						return (
							<div
								key={p}
								className={cn(
									'min-w-0 rounded p-1',
									st === 'changed' && 'ring-1 ring-[var(--chart-2)]/40',
									st === 'new' && 'ring-1 ring-accent-foreground/40',
								)}
							>
								<CellContent value={r.cells?.[p] ?? ''} />
							</div>
						);
					})}
				</div>
			))}
		</div>
	);
}

// ── TOC (chapter > sectionLeaf 트리) ──

interface PanelTocTreeProps {
	toc: PanelTocResponse;
	activeSectionKey: string | undefined;
	code: string;
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	navigate: any;
}
function PanelTocTree({ toc, activeSectionKey, code, navigate }: PanelTocTreeProps) {
	const goTo = (sectionKey: string) =>
		navigate({
			to: '/analysis/$code/viewer',
			params: { code },
			search: (prev: { period?: string }) => ({
				period: prev?.period ?? 'quarterly',
				section: sectionKey,
				windowEnd: undefined,
			}),
		});
	return (
		<nav className="space-y-2">
			{toc.chapters?.map((ch) => (
				<div key={ch.chapter}>
					<div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{ch.chapter}</div>
					<div className="space-y-0.5">
						{ch.sections?.map((sec) => {
							const isActive = sec.sectionKey === activeSectionKey;
							return (
								<button
									key={sec.sectionKey}
									type="button"
									onClick={() => goTo(sec.sectionKey)}
									className={cn(
										'flex w-full items-center gap-1.5 rounded px-2 py-1 text-left text-xs transition-colors',
										isActive ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-accent/50',
									)}
								>
									<ChevronRight className="size-3 shrink-0 opacity-50" />
									<span className="truncate">{sec.sectionLeaf}</span>
								</button>
							);
						})}
					</div>
				</div>
			))}
		</nav>
	);
}

function ViewerTab() {
	const { code } = Route.useParams();
	const { section, windowEnd } = Route.useSearch();
	const navigate = useNavigate();
	const queryClient = useQueryClient();
	const setLastMode = useDashboardMode((s) => s.setLastMode);

	useEffect(() => {
		setLastMode('viewer');
	}, [setLastMode]);

	// cold load — /panel/init (toc + 첫 절 full-period grid).
	const { data: initBundle, isLoading: initLoading } = useQuery({
		queryKey: ['panel', 'init', code],
		queryFn: () => fetchPanelInit(code),
		staleTime: 5 * 60_000,
		enabled: !section,
	});

	useEffect(() => {
		if (!initBundle) return;
		queryClient.setQueryData(['panel', 'toc', code], initBundle.toc);
		if (initBundle.firstSectionKey && initBundle.grid) {
			queryClient.setQueryData(['panel', 'section', code, initBundle.firstSectionKey], initBundle.grid);
		}
	}, [initBundle, code, queryClient]);

	const { data: tocOnly, isLoading: tocOnlyLoading } = useQuery({
		queryKey: ['panel', 'toc', code],
		queryFn: () => fetchPanelToc(code),
		staleTime: 5 * 60_000,
		enabled: !!section,
	});

	const toc = initBundle?.toc ?? tocOnly;
	const tocLoading = section ? tocOnlyLoading : initLoading;

	const firstSectionKey = useMemo(
		() => initBundle?.firstSectionKey ?? toc?.chapters?.[0]?.sections?.[0]?.sectionKey,
		[initBundle?.firstSectionKey, toc],
	);
	const activeSectionKey = section ?? firstSectionKey;

	useEffect(() => {
		if (!section && firstSectionKey) {
			navigate({
				to: '/analysis/$code/viewer',
				params: { code },
				search: (prev) => ({
					period: prev?.period ?? 'quarterly',
					section: firstSectionKey,
					windowEnd: prev?.windowEnd,
				}),
				replace: true,
			});
		}
	}, [section, firstSectionKey, code, navigate]);

	// full-period grid 1회 — window slice / diff 는 프론트 (추가 fetch 0).
	const gridSeed =
		!section && initBundle?.grid && initBundle.firstSectionKey === activeSectionKey ? initBundle.grid : undefined;
	const { data: gridFetched } = useQuery({
		queryKey: ['panel', 'section', code, activeSectionKey],
		queryFn: () => fetchPanelGrid(code, activeSectionKey as string),
		enabled: !!activeSectionKey && !gridSeed,
		staleTime: 60_000,
	});
	const grid: PanelGridResponse | undefined = gridFetched ?? gridSeed;

	// 전체 기간 축 — toc.periods (panel 이 최신좌측 정렬, timeline SSOT).
	const allPeriods = useMemo<string[]>(() => toc?.periods ?? [], [toc]);

	const effectiveWindowEnd = windowEnd && allPeriods.includes(windowEnd) ? windowEnd : allPeriods[0];
	const windowEndIdx = effectiveWindowEnd ? allPeriods.indexOf(effectiveWindowEnd) : -1;
	const windowPeriods = useMemo<string[]>(() => {
		if (windowEndIdx < 0) return [];
		return allPeriods.slice(windowEndIdx, windowEndIdx + WINDOW_SIZE);
	}, [allPeriods, windowEndIdx]);

	const setWindowEnd = (next: string | undefined) => {
		navigate({
			to: '/analysis/$code/viewer',
			params: { code },
			search: (prev) => ({
				period: prev?.period ?? 'quarterly',
				section: activeSectionKey,
				windowEnd: next,
			}),
			replace: false,
		});
	};

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

	const rows = grid?.rows ?? [];
	const dartUrlByPeriod = grid?.dartUrlByPeriod ?? {};

	// 헤더 시간축 — 인접 period 셀이 다른 row 가 하나라도 있으면 변경 표시 (프론트 계산).
	const changedSet = useMemo(() => {
		const s = new Set<string>();
		for (let i = 0; i < allPeriods.length - 1; i++) {
			const cur = allPeriods[i];
			const prev = allPeriods[i + 1];
			for (const r of rows) {
				if ((r.cells[cur] ?? '').trim() !== (r.cells[prev] ?? '').trim()) {
					s.add(cur);
					break;
				}
			}
		}
		return s;
	}, [rows, allPeriods]);

	const sectionLabel = grid?.sectionLeaf ?? activeSectionKey?.split(SECTION_KEY_SEP).pop() ?? '';
	const corpName = grid?.corpName ?? toc?.corpName ?? '';

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
		<div className={cn('flex h-full min-h-0 overflow-hidden', isFullscreen && 'fixed inset-0 z-50 bg-background')}>
			<aside className={cn('w-60 shrink-0 overflow-y-auto border-r bg-card/30 p-2 tiny-scroll', isFullscreen && 'bg-card')}>
				{tocLoading ? (
					<div className="flex items-center gap-2 p-3 text-xs text-muted-foreground">
						<Loader2 className="size-3 animate-spin" /> 목차 로드 중…
					</div>
				) : toc ? (
					<PanelTocTree toc={toc} activeSectionKey={activeSectionKey} code={code} navigate={navigate} />
				) : null}
			</aside>

			<main className="min-h-0 min-w-0 flex-1 overflow-x-hidden flex flex-col">
				{!activeSectionKey ? (
					<div className="flex h-full items-center justify-center text-sm text-muted-foreground">왼쪽에서 항목을 선택하세요.</div>
				) : !grid ? (
					<div className="flex h-full items-center justify-center gap-2 text-muted-foreground">
						<Loader2 className="size-5 animate-spin" /> 본문 로드 중…
					</div>
				) : (
					<>
						<div className="shrink-0 border-b bg-background px-3">
							<header className="pb-0 pt-2">
								<div className="flex items-baseline justify-between gap-3">
									<div>
										<div className="text-xs text-muted-foreground">
											{corpName} · {code}
										</div>
										<h1 className="mt-1 flex items-center gap-2 text-xl font-semibold tracking-tight">
											<FileText className="size-4 text-muted-foreground" />
											{sectionLabel}
										</h1>
									</div>
									<div className="flex items-center gap-3">
										<div className="text-[11px] text-muted-foreground">
											항목 {rows.length} · 전체 기간 {allPeriods.length}
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
												<div className="text-[10px] text-muted-foreground">{changedSet.has(p) ? '변경 포함' : '동일'}</div>
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
							<div className="px-3 py-3">
								<SsotRowsView rows={rows} windowPeriods={windowPeriods} allPeriods={allPeriods} />
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

function TimelineRibbon({ periods, changedSet, windowPeriods, onPick, onNewer, onOlder, canNewer, canOlder }: TimelineRibbonProps) {
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

// Badge import 호환 — 다른 모듈에서 가져옴.
export { Badge };
