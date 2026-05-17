// 본문 안 인라인 evidence chip — `[1]` superscript 양식.
// hover/click 시 Popover 에 ref 의 title + payload preview.
// "↪ 도구 호출" 클릭 시 store.flashTool 으로 ToolCallRow 강조 (Track 5).
import { useMemo } from 'react';
import { CornerDownRight, ExternalLink, FileBarChart, FileText, Globe, Hash, Settings2, Sparkles } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import type { RefDetail } from '@/features/chat/store/chat';
import { useChat } from '@/features/chat/store/chat';
import { ProvenanceTree } from './ProvenanceTree';

function kindIcon(kind: string) {
	const k = kind.toLowerCase();
	if (k.includes('doc')) return <FileText className="size-3" />;
	if (k.includes('table') || k.includes('artifact')) return <FileBarChart className="size-3" />;
	if (k.includes('value') || k.includes('date')) return <Hash className="size-3" />;
	if (k.includes('execution') || k.includes('run')) return <Settings2 className="size-3" />;
	if (k.includes('skill') || k.includes('capability')) return <Sparkles className="size-3" />;
	return <Hash className="size-3" />;
}

function previewBody(ref: RefDetail): string | null {
	const p = ref.payload;
	if (!p) return null;
	// 우선순위: body / markdown / text / preview / value
	const keys = ['body', 'markdown', 'text', 'preview', 'value'];
	for (const k of keys) {
		const v = p[k];
		if (typeof v === 'string' && v.trim()) return v;
	}
	// JSON fallback (작은 dict)
	try {
		return JSON.stringify(p, null, 2);
	} catch {
		return null;
	}
}

interface Props {
	refId: string;
	index: number; // 본문 안 등장 순서 (1, 2, 3...)
}

export function EvidenceChip({ refId, index }: Props) {
	const ref = useChat((s) => {
		const c = s.conversations.find((cv) => cv.id === s.activeId);
		return c?.refs?.[refId];
	});
	const toolCallId = useChat((s) => {
		const c = s.conversations.find((cv) => cv.id === s.activeId);
		return c?.refToToolMap?.[refId];
	});
	const flashTool = useChat((s) => s.flashTool);

	const body = useMemo(() => (ref ? previewBody(ref) : null), [ref]);
	const docId = ref?.payload && typeof ref.payload.docId === 'string' ? (ref.payload.docId as string) : null;
	const sourcePath = ref?.payload && typeof ref.payload.sourcePath === 'string' ? (ref.payload.sourcePath as string) : null;
	const reportType = ref?.payload && typeof ref.payload.reportType === 'string' ? (ref.payload.reportType as string) : null;

	if (!ref) {
		// refDetail 못 받았으면 작은 plain chip 만 표시 (id 잘림).
		return (
			<sup className="mx-0.5 inline-flex items-center rounded bg-muted/60 px-1 py-0 text-[10px] font-mono text-muted-foreground">
				[{index}]
			</sup>
		);
	}

	const isExternal = ref.sourceType === 'external';

	function gotoTool() {
		if (!toolCallId) return;
		const el = document.querySelector(`[data-tool-id="${toolCallId}"]`);
		if (el && 'scrollIntoView' in el) {
			(el as HTMLElement).scrollIntoView({ behavior: 'smooth', block: 'center' });
		}
		flashTool(toolCallId);
	}

	return (
		<Popover>
			<PopoverTrigger asChild>
				<sup className="mx-0.5 inline-flex cursor-pointer items-center gap-0.5 rounded bg-muted/60 px-1 py-0 align-super text-[10px] font-mono text-muted-foreground hover:bg-muted hover:text-foreground transition-colors">
					{kindIcon(ref.kind)}
					[{index}]
				</sup>
			</PopoverTrigger>
			<PopoverContent className="w-96 p-3" side="top" align="start">
				<div className="space-y-2 text-xs">
					<div className="flex items-center gap-1.5">
						{isExternal ? (
							<Globe className="size-3 text-muted-foreground" />
						) : (
							kindIcon(ref.kind)
						)}
						<span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
							{ref.kind || 'ref'}
							{isExternal && ' · 외부'}
						</span>
					</div>
					{ref.title && <div className="text-sm font-medium leading-snug">{ref.title}</div>}
					<div className="font-mono text-[10px] text-muted-foreground truncate">{ref.id}</div>
					{docId && sourcePath && (
						<a
							href={sourcePath}
							target="_blank"
							rel="noreferrer noopener"
							className="flex items-center justify-between gap-2 rounded border border-border bg-muted/30 px-2 py-1.5 text-[11px] hover:bg-muted transition-colors"
						>
							<span className="flex items-center gap-1.5">
								<ExternalLink className="size-3 text-muted-foreground" />
								<span className="font-medium">DART 원문</span>
								{reportType && <span className="text-muted-foreground">· {reportType}</span>}
							</span>
							<span className="font-mono text-[9px] text-muted-foreground">{docId}</span>
						</a>
					)}
					{body && (
						<pre className="tiny-scroll max-h-[200px] overflow-auto rounded border border-border bg-muted/20 p-2 text-[11px] font-mono whitespace-pre-wrap break-words">
							{body}
						</pre>
					)}
					{ref.hasMore && (
						<div className="text-[10px] text-muted-foreground">
							미리보기 — 전체는 도구 결과 본문에 있음.
						</div>
					)}
					<ProvenanceTree refId={refId} />
					{toolCallId && (
						<Button
							size="sm"
							variant="ghost"
							onClick={gotoTool}
							className="h-7 w-full justify-start gap-1.5 text-xs"
						>
							<CornerDownRight className="size-3" />
							도구 호출 보기
						</Button>
					)}
				</div>
			</PopoverContent>
		</Popover>
	);
}
