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
import { Bot, ChevronLeft, ChevronRight, Columns3, ExternalLink, FileText, Loader2, Maximize2, Minimize2 } from 'lucide-react';
import { Fragment, useCallback, useEffect, useMemo, useRef, useState, type ReactElement } from 'react';

import { Badge } from '@/components/ui/badge';
import {
	fetchPanelGrid,
	fetchPanelFull,
	fetchPanelInit,
	fetchPanelToc,
	type PanelRow,
	type PanelTocResponse,
} from '@/features/dashboard/api/client';
import { useDashboardMode } from '@/features/dashboard/store/dashboardMode';
import { ViewerAskDrawer } from '@/features/dashboard/viewer/ViewerAskDrawer';
import { ViewerCommandPalette } from '@/features/dashboard/viewer/ViewerCommandPalette';
import {
	buildViewerSearchIndex,
	type ViewerSearchHit,
	type ViewerSearchIndex,
} from '@/features/dashboard/viewer/searchIndex';
import type { ViewerActionApi } from '@/features/dashboard/viewer/viewerActions';
import { cn } from '@/lib/utils';

interface ViewerSearch {
	section?: string; // sectionKey ({chapter}␟{sectionLeaf}) — 옛 ?topic= 대체
	block?: string; // blockLeaf — 주석 등 세분 항목 단위 (그 항목만 수평 격자)
	windowEnd?: string;
}

export const Route = createFileRoute('/analysis/$code/viewer')({
	component: ViewerTab,
	validateSearch: (s: Record<string, unknown>): ViewerSearch => ({
		section: typeof s.section === 'string' && s.section ? s.section : undefined,
		block: typeof s.block === 'string' && s.block ? s.block : undefined,
		windowEnd: typeof s.windowEnd === 'string' && s.windowEnd ? s.windowEnd : undefined,
	}),
});

const DEFAULT_COLS = 3; // 표시 기간 컬럼 수 기본값 (사용자가 3/6/9 로 가로 폭 확장)
const COL_CHOICES = [3, 6, 9] as const;
const SECTION_KEY_SEP = '␟';

function isAnnualLikePeriod(period: string): boolean {
	return /^\d{4}$/.test(period) || /(?:Q4|FY)$/i.test(period);
}

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
			<div
				className="dartlab-html-table overflow-x-auto [&_td]:[font-variant-numeric:tabular-nums] [&_th]:[font-variant-numeric:tabular-nums]"
				dangerouslySetInnerHTML={{ __html: cleanHtml }}
			/>
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
	// 블록 태그(<P>/<div>/<title>/<br>)는 줄바꿈으로 보존, 인라인 태그만 공백 제거.
	// (normalizeDartXml 가 <P>→<div> 변환 후이므로 닫는 div/p/title 을 개행으로.)
	return s
		.replace(/<\s*br\s*\/?>/gi, '\n')
		.replace(/<\/\s*(p|div|title|li|tr)\s*>/gi, '\n')
		.replace(/<[^>]+>/g, ' ')
		.replace(/[^\S\n]+/g, ' ')
		.replace(/[ \t]*\n[ \t]*/g, '\n')
		.replace(/\n{3,}/g, '\n\n')
		.trim();
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

// 레일 라벨 = 사용자가 탐색하는 항목 축 = blockLeaf (TOC chip 과 동일). disclosureKey 는
// 내부 정합용 코드라 라벨로 쓰지 않는다 — 서술형 절(회사의 개요)이 빈 거터를 갖던 원인.
function rowLabel(r: PanelRow): string {
	return r.blockLeaf || '';
}

interface PanelMatrixProps {
	rows: PanelRow[];
	windowPeriods: string[];
	allPeriods: string[]; // diff 용 (인접셀 prev 조회) — fetchPeriods (window+1)
	dartUrlByPeriod: Record<string, string | null>;
	changedSet: Set<string>;
	glowCell?: { rowIndex: number; period: string } | null;
}

// 수평화 매트릭스 — 한 절 전체를 양축 고정 격자로. 행=panel 항목(truth, 재조인 0),
// 열=기간. 상단 기간 헤더 sticky(top), 좌측 항목 레이블 sticky(left), 기간 컬럼이
// 전 항목에 걸쳐 일직선. 가로 스크롤로 더 많은 기간을 펼친다 (수평화의 극치).
// 셀은 원본 그대로(CellContent) — 합치거나 재계산하지 않는다.
function PanelMatrix({ rows, windowPeriods, allPeriods, dartUrlByPeriod, changedSet, glowCell }: PanelMatrixProps) {
	const visible = useMemo(
		() => rows.map((row, index) => ({ row, index })).filter(({ row }) => hasVisibleContent(row, windowPeriods)),
		[rows, windowPeriods],
	);
	if (windowPeriods.length === 0) return null;
	if (visible.length === 0) {
		return (
			<div className="py-6 text-center text-xs text-muted-foreground">
				선택한 기간에는 이 항목 본문이 없습니다. 타임라인에서 다른 기간을 선택하세요.
			</div>
		);
	}
	// 좌측 항목 레일은 "여러 항목을 구분"할 때만 의미가 있다. 서술형 절(회사의 개요 등)처럼
	// 서로 다른 라벨이 0~1 개면 빈 거터로 읽기 폭만 잡아먹으므로 생략 — distinct 라벨 ≥ 2 일 때만.
	const distinctLabels = new Set(visible.map(({ row }) => rowLabel(row)).filter(Boolean));
	const hasLabel = distinctLabels.size >= 2;
	const labelTrack = hasLabel ? 'minmax(120px, 200px) ' : '';
	const template = `${labelTrack}repeat(${windowPeriods.length}, minmax(260px, 1fr))`;

	return (
		<div className="h-full overflow-auto tiny-scroll">
			<div className="grid items-stretch" style={{ gridTemplateColumns: template }}>
				{/* ── 헤더 행 (sticky top) ── */}
				{hasLabel && (
					<div className="sticky left-0 top-0 z-30 border-b border-r bg-background px-2 py-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
						항목
					</div>
				)}
				{windowPeriods.map((p) => {
					const url = dartUrlByPeriod[p];
					return (
						<div key={`h-${p}`} className="sticky top-0 z-20 flex items-center justify-between gap-2 border-b bg-background px-2 py-2">
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
									className="inline-flex shrink-0 items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] text-muted-foreground hover:bg-accent"
								>
									<ExternalLink className="size-2.5" /> 원본
								</a>
							)}
						</div>
					);
				})}

				{/* ── 본문 행 (항목 × 기간) ── */}
				{visible.map(({ row: r, index: rowIndex }) => {
					const label = rowLabel(r);
					return (
						<Fragment key={`${rowIndex}:${rowKey(r)}`}>
							{hasLabel && (
								<div
									className="sticky left-0 z-10 border-b border-r bg-card/70 px-2 py-2 text-[11px] font-medium text-foreground backdrop-blur-sm"
									title={label}
								>
									<div className="line-clamp-6 break-words">{label}</div>
								</div>
							)}
							{windowPeriods.map((p) => {
								const st = cellStatus(r, p, allPeriods);
								return (
									<div
										key={`${rowIndex}:${p}`}
										data-block={r.blockLeaf || undefined}
										className={cn(
											'min-w-0 border-b px-2 py-2',
											st === 'changed' && 'bg-[var(--chart-2)]/5',
											st === 'new' && 'bg-accent/20',
											glowCell?.rowIndex === rowIndex &&
												glowCell.period === p &&
												'outline outline-2 outline-offset-[-2px] outline-primary bg-primary/10',
										)}
									>
										<CellContent value={r.cells?.[p] ?? ''} />
									</div>
								);
							})}
						</Fragment>
					);
				})}
			</div>
		</div>
	);
}

// ── TOC (chapter > sectionLeaf 트리) ──

interface PanelTocTreeProps {
	toc: PanelTocResponse;
	activeSectionKey: string | undefined;
	activeBlock: string | undefined;
	code: string;
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	navigate: any;
}
function PanelTocTree({ toc, activeSectionKey, activeBlock, code, navigate }: PanelTocTreeProps) {
	// sectionLeaf 클릭 = 절 전체, blockLeaf 클릭 = 그 항목만 (block). 둘 다 windowEnd 리셋.
	const go = (sectionKey: string, blockLeaf?: string) =>
		navigate({
			to: '/analysis/$code/viewer',
			params: { code },
			search: (prev: { period?: string }) => ({
				period: prev?.period ?? 'quarterly',
				section: sectionKey,
				block: blockLeaf,
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
							// 주석처럼 세분 항목(blockLeaf)이 있는 절은 미리 펼쳐 분할 네비 (뭉텅이 스크롤 대신).
							const expanded = (isActive || sec.sectionLeaf.includes('주석')) && sec.blocks.length > 0;
							return (
								<div key={sec.sectionKey}>
									<button
										type="button"
										onClick={() => go(sec.sectionKey)}
										className={cn(
											'flex w-full items-center gap-1.5 rounded px-2 py-1 text-left text-xs transition-colors',
											isActive && !activeBlock
												? 'bg-accent text-accent-foreground'
												: 'text-muted-foreground hover:bg-accent/50',
										)}
									>
										<ChevronRight className={cn('size-3 shrink-0 opacity-50 transition-transform', expanded && 'rotate-90')} />
										<span className="truncate">{sec.sectionLeaf}</span>
									</button>
									{expanded && (
										<div className="ml-3 mt-0.5 space-y-px border-l border-border/40 pl-2">
											{sec.blocks.map((b, i) => {
												const blockActive = isActive && activeBlock === b.blockLeaf;
												return (
													<button
														key={b.blockLeaf}
														type="button"
														onClick={() => go(sec.sectionKey, b.blockLeaf)}
														title={b.blockLeaf}
														className={cn(
															'block w-full truncate rounded px-1.5 py-0.5 text-left text-[11px] transition-colors',
															blockActive
																? 'bg-accent/70 font-medium text-accent-foreground'
																: 'text-muted-foreground/70 hover:bg-accent/40 hover:text-foreground',
														)}
													>
														{i + 1}. {b.blockLeaf}
													</button>
												);
											})}
										</div>
									)}
								</div>
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
	const { section, block, windowEnd } = Route.useSearch();
	const navigate = useNavigate();
	const queryClient = useQueryClient();
	const setLastMode = useDashboardMode((s) => s.setLastMode);
	const [askOpen, setAskOpen] = useState(false);
	const [searchIndex, setSearchIndex] = useState<ViewerSearchIndex | null>(null);
	const [indexing, setIndexing] = useState(false);
	const indexPromiseRef = useRef<Promise<ViewerSearchIndex | null> | null>(null);
	const [glowCell, setGlowCell] = useState<{ rowIndex: number; period: string } | null>(null);

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
			// seed 키는 grid 쿼리 키와 동일해야 적중 (periods 포함) — init.grid 가 최신 window.
			queryClient.setQueryData(
				['panel', 'section', code, initBundle.firstSectionKey, '', (initBundle.grid.periods ?? []).join(',')],
				initBundle.grid,
			);
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

	// 표시 기간 컬럼 수 — 사용자가 3/6/9 로 가로 폭 확장 (수평화 정도 조절).
	const [cols, setCols] = useState<number>(DEFAULT_COLS);
	const [annualOnly, setAnnualOnly] = useState(false);

	// 전체 기간 축 — toc.periods (panel 이 최신좌측 정렬, timeline SSOT).
	const allPeriods = useMemo<string[]>(() => toc?.periods ?? [], [toc]);
	const visiblePeriods = useMemo<string[]>(() => {
		if (!annualOnly) return allPeriods;
		const annuals = allPeriods.filter(isAnnualLikePeriod);
		return annuals.length > 0 ? annuals : allPeriods;
	}, [allPeriods, annualOnly]);

	const effectiveWindowEnd = windowEnd && visiblePeriods.includes(windowEnd) ? windowEnd : visiblePeriods[0];
	const windowEndIdx = effectiveWindowEnd ? visiblePeriods.indexOf(effectiveWindowEnd) : -1;
	// 표시 cols 기간. fetchPeriods = +1 (직전 인접셀 diff 용). full-period(수MB) 대신 window 만 fetch.
	const windowPeriods = useMemo<string[]>(() => {
		if (windowEndIdx < 0) return [];
		return visiblePeriods.slice(windowEndIdx, windowEndIdx + cols);
	}, [visiblePeriods, windowEndIdx, cols]);
	const fetchPeriods = useMemo<string[]>(() => {
		if (windowEndIdx < 0) return [];
		return visiblePeriods.slice(windowEndIdx, windowEndIdx + cols + 1);
	}, [visiblePeriods, windowEndIdx, cols]);

	// window 단위 grid fetch — windowEnd 이동 시 fetchPeriods 가 바뀌어 재fetch. 초기
	// (windowEnd 없음)는 /panel/init 이 동봉한 최신 window grid 를 seed 로 재사용 (fetch 0).
	const { data: grid } = useQuery({
		queryKey: ['panel', 'section', code, activeSectionKey, block ?? '', fetchPeriods.join(',')],
		queryFn: () => fetchPanelGrid(code, activeSectionKey as string, fetchPeriods, block),
		enabled: !!activeSectionKey && fetchPeriods.length > 0,
		staleTime: 60_000,
	});

	const setWindowEnd = (next: string | undefined) => {
		navigate({
			to: '/analysis/$code/viewer',
			params: { code },
			search: (prev) => ({
				period: prev?.period ?? 'quarterly',
				section: activeSectionKey,
				block: block,
				windowEnd: next,
			}),
			replace: false,
		});
	};

	const focusEvidence = useCallback(
		(hit: ViewerSearchHit) => {
			if (annualOnly && !isAnnualLikePeriod(hit.period)) setAnnualOnly(false);
			navigate({
				to: '/analysis/$code/viewer',
				params: { code },
				search: (prev) => ({
					period: prev?.period ?? 'quarterly',
					section: hit.sectionKey,
					block: undefined,
					windowEnd: hit.period === visiblePeriods[0] ? undefined : hit.period,
				}),
				replace: false,
			});
			setGlowCell({ rowIndex: hit.rowIndex, period: hit.period });
		},
		[annualOnly, code, navigate, visiblePeriods],
	);

	const ensureIndex = useCallback(async (): Promise<ViewerSearchIndex | null> => {
		if (searchIndex) return searchIndex;
		if (indexPromiseRef.current) return indexPromiseRef.current;
		setIndexing(true);
		const promise = fetchPanelFull(code)
			.then((full) => buildViewerSearchIndex(full))
			.then((idx) => {
				setSearchIndex(idx);
				return idx;
			})
			.catch(() => null)
			.finally(() => {
				indexPromiseRef.current = null;
				setIndexing(false);
			});
		indexPromiseRef.current = promise;
		return promise;
	}, [code, searchIndex]);

	useEffect(() => {
		setSearchIndex(null);
		indexPromiseRef.current = null;
		setGlowCell(null);
	}, [code]);

	const moveOlder = () => {
		if (windowEndIdx < 0 || windowEndIdx + 1 >= visiblePeriods.length) return;
		setWindowEnd(visiblePeriods[windowEndIdx + 1]);
	};
	const moveNewer = () => {
		if (windowEndIdx <= 0) return;
		setWindowEnd(windowEndIdx === 1 ? undefined : visiblePeriods[windowEndIdx - 1]);
	};
	const canOlder = windowEndIdx >= 0 && windowEndIdx + 1 < visiblePeriods.length;
	const canNewer = windowEndIdx > 0;

	const rows = grid?.rows ?? [];
	const dartUrlByPeriod = grid?.dartUrlByPeriod ?? {};
	const validSections = useMemo(() => new Set(toc?.chapters.flatMap((ch) => ch.sections.map((sec) => sec.sectionKey)) ?? []), [toc]);
	const viewerActionApi = useMemo<ViewerActionApi>(
		() => ({
			navigateCompany: (nextCode) => {
				navigate({
					to: '/analysis/$code/viewer',
					params: { code: nextCode },
					search: { period: 'quarterly' },
				});
			},
			focusEvidence,
			setSection: (sectionKey) => {
				navigate({
					to: '/analysis/$code/viewer',
					params: { code },
					search: (prev) => ({ period: prev?.period ?? 'quarterly', section: sectionKey, windowEnd: prev?.windowEnd }),
				});
			},
			setPeriod: (period) => {
				if (annualOnly && !isAnnualLikePeriod(period)) setAnnualOnly(false);
				setWindowEnd(period === visiblePeriods[0] ? undefined : period);
			},
			moveNewer,
			moveOlder,
			setCols: (count) => setCols(count),
			toggleAnnual: () => setAnnualOnly((v) => !v),
			hasSection: (sectionKey) => validSections.has(sectionKey),
			hasPeriod: (period) => allPeriods.includes(period),
			knownCode: (nextCode) => /^[A-Za-z0-9]{1,20}$/.test(nextCode) && nextCode !== code,
		}),
		[allPeriods, annualOnly, code, focusEvidence, moveNewer, moveOlder, navigate, validSections, visiblePeriods],
	);

	// 헤더 시간축 — 인접 period 셀이 다른 row 가 하나라도 있으면 변경 표시 (프론트 계산).
	const changedSet = useMemo(() => {
		const s = new Set<string>();
		for (let i = 0; i < fetchPeriods.length - 1; i++) {
			const cur = fetchPeriods[i];
			const prev = fetchPeriods[i + 1];
			for (const r of rows) {
				if ((r.cells[cur] ?? '').trim() !== (r.cells[prev] ?? '').trim()) {
					s.add(cur);
					break;
				}
			}
		}
		return s;
	}, [rows, fetchPeriods]);

	const sectionLabel = block ?? grid?.sectionLeaf ?? activeSectionKey?.split(SECTION_KEY_SEP).pop() ?? '';
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
					<PanelTocTree toc={toc} activeSectionKey={activeSectionKey} activeBlock={block} code={code} navigate={navigate} />
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
											항목 {rows.length} · 표시 기간 {visiblePeriods.length}/{allPeriods.length}
										</div>
										<ViewerCommandPalette
											index={searchIndex}
											indexing={indexing}
											onEnsureIndex={() => void ensureIndex()}
											onPick={focusEvidence}
										/>
										<button
											type="button"
											onClick={() => {
												setAskOpen((v) => !v);
												void ensureIndex();
											}}
											title="AI 공시 Q&A"
											className={cn(
												'inline-flex h-8 items-center gap-1 rounded border px-2 text-xs text-muted-foreground hover:bg-accent',
												askOpen && 'border-primary/60 bg-primary/10 text-foreground',
											)}
										>
											<Bot className="size-3.5" /> AI
										</button>
										<div className="flex items-center gap-1 rounded border p-0.5" title="동시 표시 기간 수 (가로 폭)">
											<Columns3 className="ml-1 size-3 text-muted-foreground" />
											{COL_CHOICES.map((n) => (
												<button
													key={n}
													type="button"
													onClick={() => setCols(n)}
													className={cn(
														'rounded px-1.5 py-0.5 font-mono text-[11px] transition-colors',
														cols === n ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-accent/50',
													)}
												>
													{n}
												</button>
											))}
										</div>
										<button
											type="button"
											onClick={() => setAnnualOnly((v) => !v)}
											title="연간 보고서 기간만 보기"
											className={cn(
												'inline-flex h-8 items-center rounded border px-2 text-xs text-muted-foreground hover:bg-accent',
												annualOnly && 'border-primary/60 bg-primary/10 text-foreground',
											)}
										>
											연간
										</button>
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
									periods={visiblePeriods}
									changedSet={changedSet}
									windowPeriods={windowPeriods}
									onPick={(p) => setWindowEnd(p === visiblePeriods[0] ? undefined : p)}
									onNewer={moveNewer}
									onOlder={moveOlder}
									canNewer={canNewer}
									canOlder={canOlder}
								/>
							</header>
						</div>

						<div className="min-h-0 flex-1">
							<PanelMatrix
								rows={rows}
								windowPeriods={windowPeriods}
								allPeriods={fetchPeriods}
								dartUrlByPeriod={dartUrlByPeriod}
								changedSet={changedSet}
								glowCell={glowCell}
							/>
						</div>
					</>
				)}
			</main>
			{askOpen && (
				<ViewerAskDrawer
					code={code}
					corpName={corpName}
					index={searchIndex}
					indexing={indexing}
					onEnsureIndex={ensureIndex}
					actionApi={viewerActionApi}
					onClose={() => setAskOpen(false)}
				/>
			)}
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
