// 도구 호출 1 단 확장 row — Claude Code / ChatGPT / Cursor 양식.
// collapsed: [icon] toolName · summary  (duration) [▾]
// expanded: In  {args}  /  Out  {result|error} — sibling, 중첩 박스 없음.
import { useEffect, useState } from 'react';
import { AlertCircle, ChevronDown, ChevronRight, CircleCheck, Loader2 } from 'lucide-react';

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import type { ToolPart } from '@/features/chat/store/chat';
import { useChat } from '@/features/chat/store/chat';
import { ResultBody } from '../results/ResultBody';
import { ToolArgs } from '../tools/registry';

interface ExecutionFailureData {
	traceback?: unknown;
	errorLine?: unknown;
	hint?: unknown;
	stdout?: unknown;
	stderr?: unknown;
	durationMs?: unknown;
}

function asString(v: unknown): string {
	if (typeof v === 'string') return v;
	if (v == null) return '';
	return String(v);
}

function ToolErrorBody({ tool }: { tool: ToolPart }) {
	// 서버 ToolResult.data 안 traceback / errorLine / hint / stdout 노출.
	// 짧은 error 코드 (tool.error) 와 함께 진짜 진단 정보를 펼침 — '왜 실패했는지' 즉시.
	const data =
		tool.result && typeof tool.result === 'object'
			? ((tool.result as { data?: ExecutionFailureData }).data ?? {})
			: {};
	const errorLine = asString(data.errorLine);
	const traceback = asString(data.traceback);
	const hint = asString(data.hint);
	const stdout = asString(data.stdout);
	return (
		<div className="space-y-2">
			<div className="flex items-baseline gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-2.5 py-1.5">
				<span className="font-mono text-[10px] uppercase tracking-wider text-destructive shrink-0">
					{tool.error || 'error'}
				</span>
				{errorLine && (
					<span className="truncate text-xs text-destructive">{errorLine}</span>
				)}
			</div>
			{hint && (
				<div className="rounded-md border border-amber-500/30 bg-amber-500/5 px-2.5 py-1.5 text-xs text-amber-700 dark:text-amber-400">
					<span className="font-mono text-[10px] uppercase tracking-wider opacity-70">hint</span>
					<span className="ml-2">{hint}</span>
				</div>
			)}
			{traceback && (
				<details className="rounded-md border border-border bg-muted/20" open={!hint && !errorLine}>
					<summary className="cursor-pointer px-2.5 py-1.5 text-[10px] font-mono uppercase tracking-wider text-muted-foreground hover:text-foreground">
						traceback
					</summary>
					<pre className="tiny-scroll max-h-[50vh] overflow-auto px-2.5 pb-2 whitespace-pre-wrap break-words text-[11px] font-mono text-muted-foreground">
						{traceback}
					</pre>
				</details>
			)}
			{stdout && (
				<details className="rounded-md border border-border bg-muted/20">
					<summary className="cursor-pointer px-2.5 py-1.5 text-[10px] font-mono uppercase tracking-wider text-muted-foreground hover:text-foreground">
						stdout
					</summary>
					<pre className="tiny-scroll max-h-[30vh] overflow-auto px-2.5 pb-2 whitespace-pre-wrap break-words text-[11px] font-mono text-muted-foreground">
						{stdout}
					</pre>
				</details>
			)}
		</div>
	);
}

function fmtMs(ms: number): string {
	if (ms < 1000) return `${ms}ms`;
	return `${(ms / 1000).toFixed(1)}s`;
}

// running 상태 동안 elapsed 라이브 갱신 — 1 초마다 re-render.
function useLiveElapsed(startedAt: number, running: boolean): number {
	const [now, setNow] = useState(() => Date.now());
	useEffect(() => {
		if (!running) return;
		const t = setInterval(() => setNow(Date.now()), 1000);
		return () => clearInterval(t);
	}, [running]);
	return now - startedAt;
}

export function ToolCallRow({ tool }: { tool: ToolPart }) {
	const [open, setOpen] = useState(false);
	const liveMs = useLiveElapsed(tool.startedAt, tool.status === 'running');
	const isHighlighted = useChat((s) => {
		const c = s.conversations.find((cv) => cv.id === s.activeId);
		return c?.highlightedToolCallId === tool.id;
	});
	const dur =
		tool.status === 'running'
			? fmtMs(liveMs)
			: tool.finishedAt
				? fmtMs(tool.finishedAt - tool.startedAt)
				: null;
	const statusIcon =
		tool.status === 'running' ? (
			<Loader2 className="size-3.5 animate-spin text-muted-foreground" />
		) : tool.status === 'error' ? (
			<AlertCircle className="size-3.5 text-destructive" />
		) : (
			<CircleCheck className="size-3.5 text-emerald-500" />
		);

	// Click-to-trace 강조 ring — flashTool 액션이 1.5 초 동안 set.
	const triggerCls = isHighlighted
		? 'ring-2 ring-[#ea4647] ring-offset-2 ring-offset-background transition-shadow'
		: 'transition-shadow';

	return (
		<Collapsible
			open={isHighlighted ? true : open}
			onOpenChange={setOpen}
			className="my-1"
			data-tool-id={tool.id}
		>
			<CollapsibleTrigger
				className={`flex w-full items-center gap-2 rounded-md border border-border/60 bg-muted/30 px-2.5 py-1.5 text-left text-xs hover:bg-muted/60 transition-colors ${triggerCls}`}
			>
				{statusIcon}
				<span className="font-mono font-medium text-foreground">{tool.name}</span>
				{tool.summary && (
					<span className="truncate text-muted-foreground">· {tool.summary}</span>
				)}
				<span className="ml-auto flex items-center gap-1.5 text-muted-foreground">
					{dur && <span className="font-mono">{dur}</span>}
					{open ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
				</span>
			</CollapsibleTrigger>
			<CollapsibleContent className="mt-1.5 space-y-3 px-2.5 pb-1.5">
				<div>
					<div className="mb-1 text-[10px] font-mono font-medium uppercase tracking-wider text-muted-foreground">
						In
					</div>
					<ToolArgs name={tool.name} args={tool.args} />
				</div>
				<div>
					<div className="mb-1 text-[10px] font-mono font-medium uppercase tracking-wider text-muted-foreground">
						Out
					</div>
					{tool.status === 'running' ? (
						<div className="flex items-center gap-2 text-xs text-muted-foreground">
							<Loader2 className="size-3 animate-spin" />
							<span>실행 중…</span>
						</div>
					) : tool.error ? (
						<ToolErrorBody tool={tool} />
					) : (
						<ResultBody result={tool.result} />
					)}
				</div>
			</CollapsibleContent>
		</Collapsible>
	);
}
