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
			<CircleCheck className="size-3.5 text-[#ea4647]" />
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
						<pre className="tiny-scroll max-h-[60vh] overflow-auto rounded-md border border-destructive/30 bg-destructive/5 p-2.5 whitespace-pre-wrap break-words text-xs font-mono text-destructive">
							{tool.error}
						</pre>
					) : (
						<ResultBody result={tool.result} />
					)}
				</div>
			</CollapsibleContent>
		</Collapsible>
	);
}
