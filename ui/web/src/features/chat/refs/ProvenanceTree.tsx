// 답변 lineage tree — payload.provenance: list[refId] 의 transitive traversal.
// graph 아닌 *tree* (이름·구조 모두 graph 회귀 가드 명시). 답변 후 lineage 표시 컴포넌트이지
// 추론 흐름 강제 X — agent.py 본체 미터치.
//
// 표시: 자식 들여쓰기 + ref kind icon + title. 깊이 가드 4 (재귀 cycle 방어).
import { Fragment } from 'react';
import { FileBarChart, FileText, Hash } from 'lucide-react';

import type { RefDetail } from '@/features/chat/store/chat';
import { useChat } from '@/features/chat/store/chat';

const MAX_DEPTH = 4;

function iconFor(kind: string) {
	const k = (kind || '').toLowerCase();
	if (k.includes('doc')) return <FileText className="size-3 text-muted-foreground" />;
	if (k.includes('table') || k.includes('artifact'))
		return <FileBarChart className="size-3 text-muted-foreground" />;
	return <Hash className="size-3 text-muted-foreground" />;
}

function ProvenanceNode({
	refId,
	depth,
	seen,
	refs,
}: {
	refId: string;
	depth: number;
	seen: Set<string>;
	refs: Record<string, RefDetail> | undefined;
}) {
	const ref = refs?.[refId];
	const isCycle = seen.has(refId);
	const tooDeep = depth >= MAX_DEPTH;
	const parents = ref?.payload && Array.isArray(ref.payload.provenance)
		? (ref.payload.provenance as unknown[]).filter((x): x is string => typeof x === 'string')
		: [];
	const nextSeen = new Set(seen);
	nextSeen.add(refId);
	const conf = ref?.payload && typeof ref.payload.confidence === 'number'
		? (ref.payload.confidence as number)
		: null;
	return (
		<div className="space-y-0.5">
			<div className="flex items-center gap-1.5 text-[11px]">
				{iconFor(ref?.kind || '')}
				<span className="font-mono text-[10px] text-muted-foreground">
					{ref?.kind || 'ref'}
				</span>
				<span className="truncate">{ref?.title || refId}</span>
				{conf !== null && (
					<span className="ml-auto font-mono text-[10px] text-muted-foreground">
						{Math.round(conf)}
					</span>
				)}
			</div>
			{!isCycle && !tooDeep && parents.length > 0 && (
				<div className="ml-3 border-l border-border pl-2">
					{parents.map((pid, i) => (
						<Fragment key={`${pid}-${i}`}>
							<ProvenanceNode refId={pid} depth={depth + 1} seen={nextSeen} refs={refs} />
						</Fragment>
					))}
				</div>
			)}
			{isCycle && (
				<div className="ml-3 text-[10px] text-muted-foreground italic">↺ cycle</div>
			)}
			{tooDeep && parents.length > 0 && (
				<div className="ml-3 text-[10px] text-muted-foreground italic">… 깊이 한계</div>
			)}
		</div>
	);
}

export function ProvenanceTree({ refId }: { refId: string }) {
	const refs = useChat((s) => {
		const c = s.conversations.find((cv) => cv.id === s.activeId);
		return c?.refs;
	});
	const ref = refs?.[refId];
	const parents = ref?.payload && Array.isArray(ref.payload.provenance)
		? (ref.payload.provenance as unknown[]).filter((x): x is string => typeof x === 'string')
		: [];
	if (parents.length === 0) return null;
	return (
		<div className="space-y-1 rounded border border-border bg-muted/10 p-2">
			<div className="text-[10px] uppercase tracking-wider text-muted-foreground">
				lineage
			</div>
			{parents.map((pid, i) => (
				<ProvenanceNode key={`${pid}-${i}`} refId={pid} depth={1} seen={new Set([refId])} refs={refs} />
			))}
		</div>
	);
}
