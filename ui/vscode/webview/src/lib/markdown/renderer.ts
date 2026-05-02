/** Markdown renderer — ported from ui/src/lib/markdown.js */
import { marked } from "marked";
import hljs from "highlight.js/lib/core";
import python from "highlight.js/lib/languages/python";
import javascript from "highlight.js/lib/languages/javascript";
import json from "highlight.js/lib/languages/json";
import bash from "highlight.js/lib/languages/bash";
import sql from "highlight.js/lib/languages/sql";
import xml from "highlight.js/lib/languages/xml";

hljs.registerLanguage("python", python);
hljs.registerLanguage("javascript", javascript);
hljs.registerLanguage("json", json);
hljs.registerLanguage("bash", bash);
hljs.registerLanguage("sql", sql);
hljs.registerLanguage("xml", xml);

// Number highlighting regex (Korean financial units)
const NUM_RE =
  /(?<![a-zA-Z\d])([+\-]?\d[\d,]*\.?\d*)\s*(원|억|만|조|%|배|bps)/g;

function highlightNumbers(html: string): string {
  return html.replace(
    NUM_RE,
    '<span class="num-highlight">$1 $2</span>',
  );
}

// Configure marked
marked.setOptions({
  breaks: true,
  gfm: true,
});

const renderer = new marked.Renderer();

// Extract first meaningful line for code fold summary
function codeSummary(text: string): string {
  const lines = text.split("\n").filter((l) => l.trim() && !l.trim().startsWith("#"));
  const first = lines[0] || text.split("\n")[0] || "";
  return first.length > 60 ? first.slice(0, 57) + "..." : first;
}

// Code blocks -- collapsed by default
renderer.code = function ({ text, lang }: { text: string; lang?: string }) {
  let highlighted: string;
  if (lang && hljs.getLanguage(lang)) {
    highlighted = hljs.highlight(text, { language: lang }).value;
  } else {
    highlighted = hljs.highlightAuto(text).value;
  }
  const summary = codeSummary(text);
  const label = lang === "python" ? "Python" : lang || "Code";
  const lineCount = text.split("\n").length;

  // Only collapse Python code (AI-written). Results/output stay visible.
  const shouldCollapse = lang === "python" && lineCount > 3;

  if (!shouldCollapse) {
    return `<pre class="code-block"><code class="hljs language-${lang || "text"}">${highlighted}</code></pre>`;
  }

  // Python code -- collapsed by default
  return `<details class="code-fold">
<summary class="code-fold-summary"><span class="code-fold-icon">▸</span> <span class="code-fold-label">${label}</span> <span class="code-fold-hint">${escapeHtml(summary)}</span></summary>
<pre class="code-block"><code class="hljs language-${lang || "text"}">${highlighted}</code></pre>
</details>`;
};

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Format large numbers with commas for readability
function formatNumber(s: string): string {
  return s.replace(/(?<![.\d])(-?\d{5,})(?!\.\d)/g, (m) => {
    const n = parseInt(m, 10);
    if (isNaN(n)) return m;
    return n.toLocaleString();
  });
}

// Table styling — right-align numbers + format large numbers
renderer.tablecell = function ({
  text,
  header,
}: {
  text: string;
  header: boolean;
  align?: string | null;
}) {
  const tag = header ? "th" : "td";
  const plain = text.replace(/<[^>]+>/g, "").trim();
  const isNumeric = /^[+\-]?\d/.test(plain);
  const align = isNumeric && !header ? ' style="text-align:right"' : "";
  // Format large numbers in non-header cells
  const formatted = !header ? formatNumber(text) : text;
  return `<${tag}${align}>${formatted}</${tag}>`;
};

// Wrap tables with download button (marked v15: token-based API)
let tableCounter = 0;
renderer.table = function (token: {
  header: Array<{ text: string; align?: string | null }>;
  rows: Array<Array<{ text: string }>>;
  align: Array<string | null>;
}) {
  const id = `tbl-${++tableCounter}`;

  // Filter out "..." columns (Polars truncation)
  const skipCols = new Set<number>();
  token.header.forEach((cell, i) => {
    if (cell.text.trim() === "…" || cell.text.trim() === "...") skipCols.add(i);
  });

  // Build header row
  const ths = token.header
    .filter((_, i) => !skipCols.has(i))
    .map((cell) => `<th>${cell.text}</th>`)
    .join("");
  const headerHtml = `<tr>${ths}</tr>`;

  // Detect code-like columns (종목코드/stockCode) -- don't format numbers in these
  const codeColIndices = new Set<number>();
  token.header.forEach((cell, i) => {
    const h = cell.text.trim().toLowerCase();
    if (h.includes("종목코드") || h.includes("stockcode") || h === "code") codeColIndices.add(i);
  });

  // Build data rows
  const rowsHtml = token.rows
    .map((row) => {
      const tds = row
        .filter((_, i) => !skipCols.has(i))
        .map((cell, i) => {
          let val = cell.text.trim();
          if (val === "null" || val === "None") val = "-";
          const plain = val.replace(/<[^>]+>/g, "").trim();
          const isNum = /^[+\-]?\d/.test(plain);
          const isCodeCol = codeColIndices.has(i);
          const align = isNum && !isCodeCol ? ' style="text-align:right"' : "";
          return `<td${align}>${isCodeCol ? val : formatNumber(val)}</td>`;
        })
        .join("");
      return `<tr>${tds}</tr>`;
    })
    .join("");

  return `<div class="table-wrap" data-table-id="${id}">
<table><thead>${headerHtml}</thead><tbody>${rowsHtml}</tbody></table></div>`;
};

marked.use({ renderer });

/** Convert Polars unicode box tables (┌──┬──┐) to GFM markdown tables. */
function polarsToMarkdown(text: string): string {
  if (!text.includes("┌")) return text;
  const lines = text.split("\n");
  const result: string[] = [];
  let inTable = false;
  let headerEmitted = false;
  let colCount = 0;

  for (const line of lines) {
    const s = line.trim();
    if (s.startsWith("┌") && s.endsWith("┐")) { inTable = true; headerEmitted = false; continue; }
    if (s.startsWith("└") && s.endsWith("┘")) { inTable = false; continue; }
    if (!inTable) { result.push(line); continue; }
    if (s.startsWith("╞") || s.startsWith("├")) {
      if (!headerEmitted && colCount > 0) {
        result.push("| " + Array(colCount).fill("---").join(" | ") + " |");
        headerEmitted = true;
      }
      continue;
    }
    if (s.includes("│") || s.includes("┆")) {
      const cells = s.split(/[│┆]/).map(c => c.trim()).filter(c => c);
      if (cells.every(c => ["---", "str", "f64", "i64", "i32", "u32", "u64", "bool", "cat", "date", "datetime"].includes(c))) continue;
      if (cells.length) {
        colCount = Math.max(colCount, cells.length);
        result.push("| " + cells.join(" | ") + " |");
      }
    }
  }
  return result.join("\n");
}

/** Fix mismatched markdown table separator columns. */
function fixTableSeparators(text: string): string {
  const lines = text.split("\n");
  const result: string[] = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    // Separator row: | --- | --- | ...
    if (/^\s*\|[\s\-:|]+\|\s*$/.test(line) && i > 0) {
      // Count header columns from previous line
      const headerCols = (lines[i - 1].match(/\|/g) || []).length - 1;
      if (headerCols > 0) {
        const sep = "| " + Array(headerCols).fill("---").join(" | ") + " |";
        result.push(sep);
        continue;
      }
    }
    result.push(line);
  }
  return result.join("\n");
}

/** Render markdown to HTML with highlighting. */
export function renderMarkdown(md: string): string {
  let preprocessed = polarsToMarkdown(md);
  preprocessed = fixTableSeparators(preprocessed);
  const html = marked.parse(preprocessed, { async: false }) as string;
  return highlightNumbers(html);
}

/**
 * 스트리밍-aware incremental renderer.
 *
 * 기존 구현은 메시지 1개당 1 closure 를 5곳(text block / tool result /
 * error msg / error guide)에서 공유해서 cache state(`lastCompleteIndex`)가
 * 서로 다른 텍스트 사이에서 오염됐다 → 사용자가 본 raw markdown 노출의 원인.
 *
 * 새 구현:
 * - state 없음 (stateless) — 캐시 충돌 클래스 자체를 제거
 * - contentSplitter 로 스트리밍 중 partial table/code fence 분리
 * - committed 부분만 marked 에 넘기고, draft 는 escape 해서 placeholder 표시
 * - loading=false 면 splitter 가 전체를 commit 하므로 자연 정착
 */
import { createStreamSplitter } from "./contentSplitter";

export function createIncrementalRenderer() {
  // splitter 는 streaming text 한 흐름에 한정. 같은 closure 가 여러 텍스트에
  // 호출돼도 splitter state 는 매번 reset 되도록 stateless 시그니처.
  return function render(fullText: string, loading: boolean = false): string {
    if (!fullText) return "";
    if (!loading) {
      // 완료 상태: 전체를 그냥 렌더
      return renderMarkdown(fullText);
    }
    // 스트리밍 중: stateless splitter (매 호출마다 새 인스턴스)
    const splitter = createStreamSplitter();
    const { committed, draft, draftType } = splitter.split(fullText, true);
    const committedHtml = committed ? renderMarkdown(committed) : "";
    if (!draft) return committedHtml;
    return (
      committedHtml +
      `<div class="dl-stream-draft dl-stream-${draftType}">${escapeHtml(draft)}</div>`
    );
  };
}
