// panel 셀 렌더 순수 헬퍼 — ui/web `analysis.$code.viewer.tsx` 1:1 포팅 (프레임워크 무관 TS).
// panel 셀 = raw DART XML (무손실, 대문자 정부 태그). 브라우저 렌더 위해 표준 html 로 정규화 + sanitize.

// ── DART 대문자 XML → 표준 html 태그 맵 ──
export const DART_TAG_MAP: Record<string, string> = {
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
	BR: 'br'
};

// ACODE/ACONTEXT 등 정부 메타 속성 제거, 표 구조 속성(colspan/rowspan/align)만 보존.
export function normalizeDartXml(value: string): string {
	if (!value || value.indexOf('<') < 0) return value;
	return value.replace(
		/<(\/?)([A-Za-z][\w-]*)((?:\s[^>]*)?)\s*\/?>/g,
		(_m, slash: string, tag: string, attrs: string) => {
			const upper = tag.toUpperCase();
			const name = DART_TAG_MAP[upper] ?? tag.toLowerCase();
			let keep = '';
			if (!slash && attrs) {
				const am = attrs.match(/\b(colspan|rowspan|align)\s*=\s*("[^"]*"|'[^']*'|\S+)/gi);
				if (am) keep = ' ' + am.join(' ');
			}
			return `<${slash}${name}${keep}>`;
		}
	);
}

// DART 본문은 untrusted — DOMPurify 로 script/style/handler/iframe 제거 (CellContent.svelte 에서 적용).
export const SANITIZE_CONFIG = {
	ALLOWED_TAGS: ['table', 'thead', 'tbody', 'tfoot', 'tr', 'td', 'th', 'br', 'span', 'div', 'b', 'i', 'u', 'strong', 'em', 'sub', 'sup'],
	ALLOWED_ATTR: ['colspan', 'rowspan', 'class', 'align']
};

// HTML 본문에서 `<table>...</table>` block 추출 + 사이 텍스트 보존.
export function splitHtmlAndText(value: string): Array<['html' | 'text', string]> {
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

export const PERIOD_LABEL_RE = /^(?:당기|전기|당기말|전기말|당분기|전분기|당반기|전반기|당기누적|전기누적|3개월|누적|보고기간말)$/;
export const UNIT_RE = /\(?\s*단위\s*[:：]?\s*[^)]+\)?/;
const PERIOD_DATE_RE = /^제\s*\d+\s*기/;

// HTML <table> 직전 paragraph 가 (단위 …)/회기일자/period label 패턴이면 표 caption/unit 흡수.
export function absorbCaptionUnitFromText(textBefore: string): { caption: string; unit: string; remaining: string } {
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
		if (PERIOD_DATE_RE.test(line) && line.length < 80) {
			caption = caption ? `${caption} · ${line}` : line;
			continue;
		}
		remaining.push(line);
	}
	return { caption, unit, remaining: remaining.join('\n') };
}

// 인라인 태그 strip (텍스트 조각의 caption/unit 패턴 매칭용). 블록 태그는 개행 보존.
export function stripInlineTags(s: string): string {
	return s
		.replace(/<\s*br\s*\/?>/gi, '\n')
		.replace(/<\/\s*(p|div|title|li|tr)\s*>/gi, '\n')
		.replace(/<[^>]+>/g, ' ')
		.replace(/[^\S\n]+/g, ' ')
		.replace(/[ \t]*\n[ \t]*/g, '\n')
		.replace(/\n{3,}/g, '\n\n')
		.trim();
}

// ── markdown sub-table 파서 (옛 셀 호환 — panel raw XML 엔 드묾) ──

export interface MarkdownSubTable {
	caption?: string;
	unit?: string;
	rows: string[][];
}

function parseRawCells(line: string): string[] {
	return line.replace(/^\||\|$/g, '').split('|').map((c) => c.trim());
}

export function parseMarkdownSubTables(md: string): MarkdownSubTable[] {
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

export function refineSubTable(block: MarkdownSubTable): MarkdownSubTable {
	const rows = [...block.rows];
	let caption = block.caption;
	let unit = block.unit;
	const consume = (): boolean => {
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
