// 연속 도구/viewSpec parts 를 단일 박스로 묶음.
// 헤더: 진행 중 = spinner + "분석 중 · {currentTool}", 완료 = "분석 완료 · {N}건" + 총 소요.
// 내부 (expanded) = ToolCallRow / ArtifactCard 들.
// 사용자 가이드: backup loop-card 양식.
import { useState } from 'react';
import { ChevronDown, ChevronRight, Loader2, Sparkles } from 'lucide-react';

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import type { Part, ToolPart, ViewSpecPart } from '@/features/chat/store/chat';
import { ArtifactCard } from './ArtifactCard';
import { ToolCallRow } from './ToolCallRow';

type LoopPart = ToolPart | ViewSpecPart;

function loopRunning(parts: LoopPart[]): boolean {
	return parts.some((p) => p.type === 'tool' && p.status === 'running');
}

function loopErrored(parts: LoopPart[]): boolean {
	return parts.some((p) => p.type === 'tool' && p.status === 'error');
}

function currentToolName(parts: LoopPart[]): string | null {
	const running = [...parts]
		.reverse()
		.find((p): p is ToolPart => p.type === 'tool' && p.status === 'running');
	return running?.name ?? null;
}

function durationLabel(parts: LoopPart[]): string | null {
	const tools = parts.filter((p): p is ToolPart => p.type === 'tool');
	if (!tools.length) return null;
	const start = Math.min(...tools.map((t) => t.startedAt));
	const ends = tools.map((t) => t.finishedAt ?? Date.now());
	const end = Math.max(...ends);
	const ms = end - start;
	if (ms < 1000) return `${ms}ms`;
	return `${(ms / 1000).toFixed(1)}s`;
}

export function WorkLoop({ parts }: { parts: LoopPart[] }) {
	const running = loopRunning(parts);
	const errored = loopErrored(parts);
	// 진행 중이면 기본 펼쳐서 사용자가 무엇이 돌고 있는지 보게 — 끝나면 자동 접힘 의도지만 사용자가 만질 수 있게 controlled.
	const [open, setOpen] = useState(running);

	// running 상태가 바뀔 때마다 close — but only if user hasn't manually opened
	// 단순화: 사용자 토글 우선. 자동 닫지 않음.

	const toolCount = parts.filter((p) => p.type === 'tool').length;
	const errorCount = parts.filter((p) => p.type === 'tool' && p.status === 'error').length;
	const cur = currentToolName(parts);
	const dur = durationLabel(parts);

	const statusIcon = running ? (
		<Loader2 className="size-3.5 animate-spin text-muted-foreground" />
	) : errored ? (
		<Sparkles className="size-3.5 text-destructive" />
	) : (
		<Sparkles className="size-3.5 text-emerald-500" />
	);

	const label = running
		? cur
			? `분석 중 · ${cur}`
			: '분석 중'
		: errored
			? `분석 실패 · ${errorCount}/${toolCount}건`
			: `분석 완료 · ${toolCount}건`;

	return (
		<Collapsible open={open} onOpenChange={setOpen} className="my-2">
			<CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md border border-border bg-muted/20 px-3 py-2 text-left text-xs hover:bg-muted/40 transition-colors">
				{statusIcon}
				<span className="text-foreground">{label}</span>
				<span className="ml-auto flex items-center gap-2 text-muted-foreground">
					{dur && <span className="font-mono">{dur}</span>}
					{open ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
				</span>
			</CollapsibleTrigger>
			<CollapsibleContent className="mt-2 space-y-1 border-l border-border pl-3">
				{parts.map((p, i) =>
					p.type === 'tool' ? (
						<ToolCallRow key={p.id} tool={p} />
					) : (
						<ArtifactCard key={p.id ?? i} part={p} />
					),
				)}
			</CollapsibleContent>
		</Collapsible>
	);
}

// chat-message.tsx 가 부른다 — parts[] 를 [textPart | LoopPart[]] 시퀀스로 변환.
export type GroupedItem = { kind: 'text'; part: Extract<Part, { type: 'text' }> } | { kind: 'loop'; parts: LoopPart[] };

export function groupParts(parts: Part[]): GroupedItem[] {
	const out: GroupedItem[] = [];
	let buf: LoopPart[] = [];
	const flush = () => {
		if (buf.length) {
			out.push({ kind: 'loop', parts: buf });
			buf = [];
		}
	};
	for (const p of parts) {
		if (p.type === 'text') {
			flush();
			out.push({ kind: 'text', part: p });
		} else {
			buf.push(p);
		}
	}
	flush();
	return out;
}
