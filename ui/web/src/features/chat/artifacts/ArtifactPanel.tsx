// Artifact 우측 Sheet — ChatGPT Canvas / Claude Artifacts 패턴.
// 본 영역:
//  · 헤더: workspace 컨텍스트 (현재 분석 회사) + artifact 타이틀
//  · 본문: 현재 선택 artifact (차트/표) OR 컨텍스트만 노출 (artifact 없을 때)
import { Briefcase, FileBarChart, X } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { useChat } from '@/features/chat/store/chat';
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

function WorkspaceContextSection() {
	const ctx = useChat((s) => {
		const c = s.conversations.find((cv) => cv.id === s.activeId);
		return c?.workspaceContext;
	});
	const setWorkspaceContext = useChat((s) => s.setWorkspaceContext);
	if (!ctx) return null;
	return (
		<div className="flex items-center gap-2 border-b border-border bg-muted/20 px-4 py-2">
			<Briefcase className="size-3.5 text-muted-foreground shrink-0" />
			<span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground shrink-0">
				분석 대상
			</span>
			<Badge variant="secondary" className="font-mono font-normal text-[11px]">
				{ctx.stockCode}
			</Badge>
			{ctx.corpName && <span className="truncate text-xs">{ctx.corpName}</span>}
			{ctx.market && (
				<span className="font-mono text-[10px] text-muted-foreground">· {ctx.market}</span>
			)}
			<Button
				variant="ghost"
				size="icon"
				className="ml-auto size-6"
				onClick={() => setWorkspaceContext(null)}
				aria-label="컨텍스트 해제"
				title="컨텍스트 해제"
			>
				<X className="size-3" />
			</Button>
		</div>
	);
}

export function ArtifactPanel() {
	const open = useArtifact((s) => s.open);
	const current = useArtifact((s) => s.current);
	const close = useArtifact((s) => s.close);

	return (
		<Sheet open={open} onOpenChange={(v) => (v ? null : close())}>
			<SheetContent side="right" className="w-[720px] sm:max-w-[720px] flex flex-col gap-0 p-0">
				<WorkspaceContextSection />
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
						<div className="text-center text-xs text-muted-foreground">
							선택된 artifact 없음 — 본문에서 ↗ 아이콘 누르면 큰 차트·표를 여기서 봅니다.
						</div>
					)}
				</div>
			</SheetContent>
		</Sheet>
	);
}
