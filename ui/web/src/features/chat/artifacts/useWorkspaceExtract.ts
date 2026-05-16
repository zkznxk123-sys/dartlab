// 현재 분석 회사 자동 추출 — 도구 호출 args 에서 stockCode 가장 최근값을 conversation.workspaceContext 로 저장.
// ArtifactPanel 헤더에서 사용. 옛 WorkspaceBar useEffect 로직 이전.
import { useEffect } from 'react';

import type { Conversation, ToolPart } from '@/features/chat/store/chat';
import { useChat } from '@/features/chat/store/chat';

function isObj(x: unknown): x is Record<string, unknown> {
	return !!x && typeof x === 'object' && !Array.isArray(x);
}

function extractStockCode(tool: ToolPart): string | null {
	const args = tool.args;
	if (!isObj(args)) return null;
	if (typeof args.stockCode === 'string') return args.stockCode;
	if (isObj(args.args) && typeof args.args.stockCode === 'string') return args.args.stockCode;
	if (tool.name === 'RunPython' && typeof args.code === 'string') {
		const m =
			args.code.match(/Company\(\s*['"]([0-9]{6}|[A-Z]{1,6})['"]/) ||
			args.code.match(/(?:stockCode|target)\s*=\s*['"]([0-9]{6}|[A-Z]{1,6})['"]/);
		if (m) return m[1] ?? null;
	}
	return null;
}

function inferMarket(stockCode: string): 'KR' | 'US' {
	return /^[0-9]{6}$/.test(stockCode) ? 'KR' : 'US';
}

function deriveContext(c: Conversation): { stockCode: string; market: 'KR' | 'US' } | null {
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

export function useWorkspaceAutoExtract() {
	const activeConv = useChat((s) => s.conversations.find((cv) => cv.id === s.activeId));
	const ctx = activeConv?.workspaceContext;
	const setWorkspaceContext = useChat((s) => s.setWorkspaceContext);

	useEffect(() => {
		if (!activeConv) return;
		const derived = deriveContext(activeConv);
		if (!derived) return;
		if (!ctx || ctx.stockCode !== derived.stockCode) {
			setWorkspaceContext(derived);
		}
	}, [activeConv, ctx, setWorkspaceContext]);
}
