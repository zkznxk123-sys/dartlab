// Tool result 모양 dispatcher — agentGateway _publicResultPayload 가 보내는 구조 인지 분기.
// 우선순위: markdown > stdout/stderr (+ values/tableHead) > tableHead > values > JSON fallback.
// 모든 분기는 sibling — 중첩 박스 없음.
// 스크롤은 native overflow + .tiny-scroll 클래스 (Radix ScrollArea 는 부모 height 명시 필요해서 인라인 영역에서 양식 깨짐).
import { MarkdownText } from '../markdown/MarkdownText';

interface ResultLike {
	markdown?: string;
	stdout?: string;
	stderr?: string;
	stdoutTruncated?: boolean;
	stderrTruncated?: boolean;
	values?: Record<string, unknown>;
	tableHead?: unknown[];
	columnNames?: string[];
	durationMs?: number;
}

function isObj(x: unknown): x is Record<string, unknown> {
	return !!x && typeof x === 'object' && !Array.isArray(x);
}

function fmtCell(v: unknown): string {
	if (v == null) return '';
	if (typeof v === 'object') {
		try {
			return JSON.stringify(v);
		} catch {
			return String(v);
		}
	}
	return String(v);
}

function ValuesTable({ values }: { values: Record<string, unknown> }) {
	const entries = Object.entries(values);
	if (!entries.length) return null;
	return (
		<div className="rounded-md border border-border overflow-hidden">
			<table className="w-full text-xs">
				<tbody>
					{entries.map(([k, v]) => (
						<tr key={k} className="border-b border-border last:border-0">
							<td className="bg-muted/30 px-2.5 py-1.5 font-mono font-medium text-muted-foreground align-top w-1/3">
								{k}
							</td>
							<td className="px-2.5 py-1.5 font-mono break-all">{fmtCell(v)}</td>
						</tr>
					))}
				</tbody>
			</table>
		</div>
	);
}

function TablePreview({ rows, columns }: { rows: unknown[]; columns?: string[] }) {
	if (!rows.length) return null;
	// rows 가 객체 배열이면 키 사용 (columns 우선), 배열 배열이면 인덱스.
	const first = rows[0];
	let head: string[] = [];
	let body: string[][] = [];
	if (isObj(first)) {
		head = columns && columns.length ? columns : Object.keys(first);
		body = rows.map((r) =>
			head.map((c) => fmtCell(isObj(r) ? (r as Record<string, unknown>)[c] : null)),
		);
	} else if (Array.isArray(first)) {
		const w = Math.max(...rows.map((r) => (Array.isArray(r) ? r.length : 0)));
		head = columns && columns.length === w ? columns : Array.from({ length: w }, (_, i) => `c${i}`);
		body = rows.map((r) =>
			Array.isArray(r) ? r.map((v) => fmtCell(v)) : Array(w).fill(''),
		);
	} else {
		return (
			<pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(rows, null, 2)}</pre>
		);
	}
	return (
		<div className="overflow-x-auto rounded-md border border-border">
			<table className="w-full text-xs">
				<thead className="bg-muted/40">
					<tr>
						{head.map((h) => (
							<th
								key={h}
								className="border-b border-border px-2.5 py-1.5 text-left font-medium"
							>
								{h}
							</th>
						))}
					</tr>
				</thead>
				<tbody>
					{body.map((row, i) => (
						<tr key={i} className="border-b border-border last:border-0">
							{row.map((cell, j) => (
								<td key={j} className="px-2.5 py-1.5 font-mono break-all">
									{cell}
								</td>
							))}
						</tr>
					))}
				</tbody>
			</table>
		</div>
	);
}

export function ResultBody({ result }: { result: unknown }) {
	if (result == null) {
		return <span className="text-xs text-muted-foreground">결과 없음</span>;
	}
	if (typeof result === 'string') {
		// 긴 문자열도 markdown 으로 렌더 (코드/표 포함 가능성).
		return <MarkdownText text={result} />;
	}
	if (!isObj(result)) {
		return (
			<pre className="tiny-scroll max-h-[60vh] overflow-auto rounded-md border border-border bg-muted/20 p-2.5 whitespace-pre-wrap break-words text-xs font-mono">
				{JSON.stringify(result, null, 2)}
			</pre>
		);
	}

	const r = result as ResultLike;
	const blocks: React.ReactNode[] = [];

	if (typeof r.markdown === 'string' && r.markdown.trim()) {
		blocks.push(<MarkdownText key="md" text={r.markdown} />);
	}

	if (typeof r.stdout === 'string' && r.stdout) {
		blocks.push(
			<div key="stdout">
				<div className="mb-1 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
					stdout{r.stdoutTruncated ? ' (truncated)' : ''}
				</div>
				<pre className="tiny-scroll max-h-[40vh] overflow-auto rounded-md border border-border bg-muted/20 p-2.5 whitespace-pre-wrap break-words text-xs font-mono">
					{r.stdout}
				</pre>
			</div>,
		);
	}
	if (typeof r.stderr === 'string' && r.stderr) {
		blocks.push(
			<div key="stderr">
				<div className="mb-1 text-[10px] font-mono uppercase tracking-wider text-destructive">
					stderr{r.stderrTruncated ? ' (truncated)' : ''}
				</div>
				<pre className="tiny-scroll max-h-[40vh] overflow-auto rounded-md border border-destructive/30 bg-destructive/5 p-2.5 whitespace-pre-wrap break-words text-xs font-mono text-destructive">
					{r.stderr}
				</pre>
			</div>,
		);
	}

	if (Array.isArray(r.tableHead) && r.tableHead.length) {
		blocks.push(
			<TablePreview key="table" rows={r.tableHead} columns={r.columnNames} />,
		);
	}

	if (isObj(r.values) && Object.keys(r.values).length) {
		blocks.push(<ValuesTable key="values" values={r.values} />);
	}

	if (typeof r.durationMs === 'number') {
		blocks.push(
			<div key="dur" className="text-[10px] font-mono text-muted-foreground">
				⏱ {r.durationMs}ms
			</div>,
		);
	}

	if (!blocks.length) {
		// 알려진 키 없음 — fallback JSON.
		return (
			<pre className="tiny-scroll max-h-[60vh] overflow-auto rounded-md border border-border bg-muted/20 p-2.5 whitespace-pre-wrap break-words text-xs font-mono">
				{JSON.stringify(result, null, 2)}
			</pre>
		);
	}

	return <div className="space-y-2.5">{blocks}</div>;
}
