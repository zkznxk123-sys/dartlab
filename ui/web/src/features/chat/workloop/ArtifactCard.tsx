// VIEW_SPEC 인라인 카드 — VizWidget 으로 렌더 시도, 미지원 kind 면 JSON fallback.
// 큰 spec (table > 15 rows 또는 chart data > 10 rows) 은 "↗" 버튼 노출 → Artifact Sheet 패널 오픈.
import { useState } from 'react';
import { ChevronDown, ChevronRight, FileBarChart, Maximize2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import type { ViewSpecPart } from '@/features/chat/store/chat';
import { useArtifact } from '../artifacts/store';
import { VizWidget } from '../widgets/registry';

function specKind(spec: unknown): string {
	if (spec && typeof spec === 'object') {
		const s = spec as { kind?: unknown; chartType?: unknown };
		if (typeof s.chartType === 'string') return s.chartType;
		if (typeof s.kind === 'string') return s.kind;
	}
	return 'artifact';
}

function isLargeSpec(spec: unknown): boolean {
	if (!spec || typeof spec !== 'object') return false;
	const s = spec as { data?: unknown; rows?: unknown };
	const data = Array.isArray(s.data) ? s.data : Array.isArray(s.rows) ? s.rows : null;
	if (!data) return false;
	return data.length > 10;
}

export function ArtifactCard({ part }: { part: ViewSpecPart }) {
	const widget = <VizWidget spec={part.spec} />;
	const hasWidget = widget !== null && widget.type !== null;
	const [open, setOpen] = useState(hasWidget);
	const kind = specKind(part.spec);
	const large = isLargeSpec(part.spec);
	const openArtifact = useArtifact((s) => s.openArtifact);
	const json = (() => {
		try {
			return JSON.stringify(part.spec, null, 2);
		} catch {
			return String(part.spec);
		}
	})();

	return (
		<Collapsible open={open} onOpenChange={setOpen} className="my-1.5">
			<div className="flex items-center gap-1">
				<CollapsibleTrigger className="flex flex-1 items-center gap-2 rounded-md border border-border/60 bg-muted/30 px-2.5 py-1.5 text-left text-xs hover:bg-muted/60 transition-colors">
					<FileBarChart className="size-3.5 text-muted-foreground" />
					<span className="font-medium text-foreground">{part.title || kind}</span>
					<span className="text-muted-foreground">· {kind}</span>
					<span className="ml-auto text-muted-foreground">
						{open ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
					</span>
				</CollapsibleTrigger>
				{large && hasWidget && (
					<Button
						variant="ghost"
						size="icon"
						className="size-7 shrink-0"
						onClick={() => openArtifact(part)}
						aria-label="패널에서 보기"
						title="패널에서 보기"
					>
						<Maximize2 className="size-3.5" />
					</Button>
				)}
			</div>
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
