// VIEW_SPEC 인라인 카드 — VizWidget 으로 렌더 시도, 미지원 kind 면 JSON fallback.
// 차트는 collapsed 상태에서도 미니 미리보기 노출 (기본 펼침).
import { useState } from 'react';
import { ChevronDown, ChevronRight, FileBarChart } from 'lucide-react';

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import type { ViewSpecPart } from '@/features/chat/store/chat';
import { VizWidget } from '../widgets/registry';

function specKind(spec: unknown): string {
	if (spec && typeof spec === 'object') {
		const s = spec as { kind?: unknown; chartType?: unknown };
		if (typeof s.chartType === 'string') return s.chartType;
		if (typeof s.kind === 'string') return s.kind;
	}
	return 'artifact';
}

export function ArtifactCard({ part }: { part: ViewSpecPart }) {
	// VizWidget 이 렌더 가능한지 사전 체크 — 가능하면 펼친 상태 기본.
	const widget = <VizWidget spec={part.spec} />;
	const hasWidget = widget !== null && widget.type !== null;
	const [open, setOpen] = useState(hasWidget);
	const kind = specKind(part.spec);
	const json = (() => {
		try {
			return JSON.stringify(part.spec, null, 2);
		} catch {
			return String(part.spec);
		}
	})();

	return (
		<Collapsible open={open} onOpenChange={setOpen} className="my-1.5">
			<CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md border border-border/60 bg-muted/30 px-2.5 py-1.5 text-left text-xs hover:bg-muted/60 transition-colors">
				<FileBarChart className="size-3.5 text-muted-foreground" />
				<span className="font-medium text-foreground">{part.title || kind}</span>
				<span className="text-muted-foreground">· {kind}</span>
				<span className="ml-auto text-muted-foreground">
					{open ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
				</span>
			</CollapsibleTrigger>
			<CollapsibleContent className="mt-2 rounded-md border border-border/60 bg-muted/10 p-3">
				{hasWidget ? (
					widget
				) : (
					<pre className="tiny-scroll max-h-[60vh] overflow-auto whitespace-pre-wrap break-words text-xs font-mono text-foreground/80">
						{json}
					</pre>
				)}
			</CollapsibleContent>
		</Collapsible>
	);
}
