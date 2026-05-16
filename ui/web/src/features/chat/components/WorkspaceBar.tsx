// 현재 분석 회사를 채팅 상단에 표시 — 긴 대화 추적 보조.
// 자동 추출: 도구 호출 args 에서 stockCode 발견 → 가장 최근값을 conversation.workspaceContext 로 저장.
// 수동 해제: X 클릭 → null.
import { useEffect } from 'react';
import { Briefcase, X } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { Conversation, ToolPart } from '@/features/chat/store/chat';
import { useChat } from '@/features/chat/store/chat';

function isObj(x: unknown): x is Record<string, unknown> {
	return !!x && typeof x === 'object' && !Array.isArray(x);
}

// 도구 args 에서 stockCode 추출 — EngineCall · LookAheadGuard · OutcomeLog · RunPython code.
function extractStockCode(tool: ToolPart): string | null {
	const args = tool.args;
	if (!isObj(args)) return null;
	// 1) 직접 stockCode 필드
	if (typeof args.stockCode === 'string') return args.stockCode;
	// 2) EngineCall: args.args.stockCode
	if (isObj(args.args) && typeof args.args.stockCode === 'string') return args.args.stockCode;
	// 3) RunPython: code 안 정규식 (Company('005930') 또는 stockCode = '005930' / target = '005930')
	if (tool.name === 'RunPython' && typeof args.code === 'string') {
		const m =
			args.code.match(/Company\(\s*['"]([0-9]{6}|[A-Z]{1,6})['"]/) ||
			args.code.match(/(?:stockCode|target)\s*=\s*['"]([0-9]{6}|[A-Z]{1,6})['"]/);
		if (m) return m[1] ?? null;
	}
	return null;
}

// market 추출 — 6 자리 숫자 = KR, 그 외 = US 추정.
function inferMarket(stockCode: string): 'KR' | 'US' {
	return /^[0-9]{6}$/.test(stockCode) ? 'KR' : 'US';
}

function deriveContextFromMessages(c: Conversation): { stockCode: string; market: 'KR' | 'US' } | null {
	// 가장 최근 user→assistant pair 에서 tool 들의 stockCode 를 역순으로 스캔.
	for (let i = c.messages.length - 1; i >= 0; i--) {
		const m = c.messages[i];
		if (!m || m.role !== 'assistant') continue;
		for (let j = m.parts.length - 1; j >= 0; j--) {
			const p = m.parts[j];
			if (p?.type !== 'tool') continue;
			const code = extractStockCode(p);
			if (code) return { stockCode: code, market: inferMarket(code) };
		}
	}
	return null;
}

export function WorkspaceBar() {
	const ctx = useChat((s) => {
		const c = s.conversations.find((cv) => cv.id === s.activeId);
		return c?.workspaceContext;
	});
	const activeConv = useChat((s) => s.conversations.find((cv) => cv.id === s.activeId));
	const setWorkspaceContext = useChat((s) => s.setWorkspaceContext);

	// 메시지에서 stockCode 자동 감지 → 컨텍스트가 없거나 더 최근 stockCode 면 업데이트.
	useEffect(() => {
		if (!activeConv) return;
		const derived = deriveContextFromMessages(activeConv);
		if (!derived) return;
		if (!ctx || ctx.stockCode !== derived.stockCode) {
			setWorkspaceContext(derived);
		}
	}, [activeConv, ctx, setWorkspaceContext]);

	if (!ctx) return null;

	return (
		<div className="mx-auto flex w-full max-w-3xl items-center gap-2 px-4 py-2 border-b border-border/60">
			<Briefcase className="size-3.5 text-muted-foreground shrink-0" />
			<span className="text-xs text-muted-foreground shrink-0">분석 중</span>
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
			>
				<X className="size-3" />
			</Button>
		</div>
	);
}
