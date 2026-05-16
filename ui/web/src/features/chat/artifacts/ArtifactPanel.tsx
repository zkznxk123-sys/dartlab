// Artifact 우측 Sheet — 큰 차트·표를 채팅 본문 외부에서 큰 사이즈로 본다.
// Claude Code Canvas / ChatGPT Artifact 양식. open 시 replace (스택 X).
import { FileBarChart } from 'lucide-react';

import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { VizWidget } from '../widgets/registry';
import { useArtifact } from './store';

function specKind(spec: unknown): string {
	if (spec && typeof spec === 'object') {
		const s = spec as { kind?: unknown; chartType?: unknown };
		if (typeof s.chartType === 'string') return s.chartType;
		if (typeof s.kind === 'string') return s.kind;
	}
	return 'artifact';
}

export function ArtifactPanel() {
	const open = useArtifact((s) => s.open);
	const current = useArtifact((s) => s.current);
	const close = useArtifact((s) => s.close);

	return (
		<Sheet open={open} onOpenChange={(v) => (v ? null : close())}>
			<SheetContent side="right" className="w-[720px] sm:max-w-[720px] flex flex-col gap-0 p-0">
				<SheetHeader className="border-b border-border px-4 py-3">
					<SheetTitle className="flex items-center gap-2 text-sm">
						<FileBarChart className="size-4 text-muted-foreground" />
						{current?.title || (current ? specKind(current.spec) : 'Artifact')}
					</SheetTitle>
					{current && (
						<div className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
							{specKind(current.spec)}
						</div>
					)}
				</SheetHeader>
				<div className="tiny-scroll flex-1 overflow-auto p-6">
					{current ? (
						<VizWidget spec={current.spec} />
					) : (
						<div className="text-center text-xs text-muted-foreground">선택된 artifact 없음</div>
					)}
				</div>
			</SheetContent>
		</Sheet>
	);
}
