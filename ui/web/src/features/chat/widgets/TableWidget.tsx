// 표 위젯 — viewSpec.kind === 'table'.
// spec: { kind: 'table', rows: [...], columns?: [...] }
import type { ReactNode } from 'react';

interface Spec {
	rows?: unknown[];
	columns?: string[];
}

function isObj(x: unknown): x is Record<string, unknown> {
	return !!x && typeof x === 'object' && !Array.isArray(x);
}

function fmtCell(v: unknown): ReactNode {
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

export function TableWidget({ spec }: { spec: Spec }) {
	const rows = Array.isArray(spec.rows) ? spec.rows : [];
	if (!rows.length) return null;
	const first = rows[0];
	let head: string[] = [];
	let body: ReactNode[][] = [];
	if (isObj(first)) {
		head = spec.columns?.length ? spec.columns : Object.keys(first);
		body = rows.map((r) =>
			head.map((c) => fmtCell(isObj(r) ? (r as Record<string, unknown>)[c] : null)),
		);
	} else if (Array.isArray(first)) {
		const w = Math.max(...rows.map((r) => (Array.isArray(r) ? r.length : 0)));
		head = spec.columns?.length === w ? spec.columns : Array.from({ length: w }, (_, i) => `c${i}`);
		body = rows.map((r) => (Array.isArray(r) ? r.map(fmtCell) : Array(w).fill('')));
	} else return null;
	return (
		<div className="tiny-scroll max-h-[60vh] overflow-auto rounded-md border border-border">
			<table className="w-full text-xs">
				<thead className="bg-muted/40 sticky top-0">
					<tr>
						{head.map((h) => (
							<th key={h} className="border-b border-border px-2.5 py-1.5 text-left font-medium">
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
