// 도구 args 렌더링용 공통 primitive — CodeArgs / KvArgs / GenericArgs / helpers.
// 신규 도구 추가 시 본 파일 import 해서 조합.
import type { ReactNode } from 'react';

export function isObj(x: unknown): x is Record<string, unknown> {
	return !!x && typeof x === 'object' && !Array.isArray(x);
}

export function fmtJson(v: unknown): string {
	try {
		return JSON.stringify(v, null, 2);
	} catch {
		return String(v);
	}
}

export function CodeArgs({ code, lang }: { code: string; lang?: string }) {
	return (
		<div className="tiny-scroll max-h-[40vh] overflow-auto rounded-md border border-border bg-muted/30 p-2.5">
			{lang && (
				<div className="mb-1 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
					{lang}
				</div>
			)}
			<pre className="text-xs font-mono leading-5">
				<code className="whitespace-pre">{code}</code>
			</pre>
		</div>
	);
}

export function KvArgs({ pairs }: { pairs: Array<[string, unknown]> }) {
	if (!pairs.length) return <span className="text-xs text-muted-foreground">—</span>;
	return (
		<div className="rounded-md border border-border overflow-hidden">
			<table className="w-full text-xs">
				<tbody>
					{pairs.map(([k, v]) => (
						<tr key={k} className="border-b border-border last:border-0">
							<td className="bg-muted/30 px-2.5 py-1.5 font-mono font-medium text-muted-foreground align-top w-1/3">
								{k}
							</td>
							<td className="px-2.5 py-1.5 font-mono break-all">
								{typeof v === 'string' ? v : fmtJson(v)}
							</td>
						</tr>
					))}
				</tbody>
			</table>
		</div>
	);
}

export function GenericArgs({ args }: { args: unknown }) {
	if (args == null) return <span className="text-xs text-muted-foreground">—</span>;
	if (typeof args === 'string') {
		return (
			<pre className="tiny-scroll max-h-[40vh] overflow-auto rounded-md border border-border bg-muted/20 p-2.5 whitespace-pre-wrap break-words text-xs font-mono">
				{args}
			</pre>
		);
	}
	if (isObj(args)) {
		return <KvArgs pairs={Object.entries(args)} />;
	}
	return (
		<pre className="tiny-scroll max-h-[40vh] overflow-auto rounded-md border border-border bg-muted/20 p-2.5 whitespace-pre-wrap break-words text-xs font-mono">
			{fmtJson(args)}
		</pre>
	);
}

export interface ToolArgsProps {
	args: unknown;
}

export type ArgsRenderer = (p: ToolArgsProps) => ReactNode;
