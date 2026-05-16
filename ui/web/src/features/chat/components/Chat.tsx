// Chat 본체 — orchestration. 입력/렌더링은 하위 컴포넌트 위임.
import { useCallback, useEffect, useRef, useState } from 'react';

import { ScrollArea } from '@/components/ui/scroll-area';
import { useChat } from '@/features/chat/store/chat';
import {
	streamAsk,
	type AskStreamControl,
} from '@/features/chat/streaming/streamAsk';
import { useWorkspaceAutoExtract } from '@/features/chat/artifacts/useWorkspaceExtract';
import { ChatMessage } from './Message';
import { Composer } from './Composer';
import { EmptyState } from './EmptyState';
import { ScrollToBottomButton } from './ScrollToBottomButton';

export function Chat() {
	useWorkspaceAutoExtract();
	const conversations = useChat((s) => s.conversations);
	const activeId = useChat((s) => s.activeId);
	const newConversation = useChat((s) => s.newConversation);
	const addMessage = useChat((s) => s.addMessage);
	const appendTextDelta = useChat((s) => s.appendTextDelta);
	const addToolStart = useChat((s) => s.addToolStart);
	const setToolResult = useChat((s) => s.setToolResult);
	const addViewSpec = useChat((s) => s.addViewSpec);
	const setLastLoading = useChat((s) => s.setLastLoading);
	const setLastError = useChat((s) => s.setLastError);
	const abortRunningTools = useChat((s) => s.abortRunningTools);
	const popLastAssistantAndGetUserText = useChat((s) => s.popLastAssistantAndGetUserText);

	const active = conversations.find((c) => c.id === activeId) ?? null;
	const messages = active?.messages ?? [];
	const hasMessages = messages.length > 0;
	const lastPartsLen = messages[messages.length - 1]?.parts.length ?? 0;
	const lastTextLen = (() => {
		const last = messages[messages.length - 1];
		if (!last) return 0;
		const lp = last.parts[last.parts.length - 1];
		return lp && lp.type === 'text' ? lp.text.length : 0;
	})();

	const [input, setInput] = useState('');
	const [busy, setBusy] = useState(false);
	const streamRef = useRef<AskStreamControl | null>(null);
	const viewportRef = useRef<HTMLDivElement | null>(null);

	// auto-scroll to bottom on new content — 사용자가 위로 스크롤하면 무시 (threshold 안에 있을 때만).
	useEffect(() => {
		const el = viewportRef.current;
		if (!el) return;
		const dist = el.scrollHeight - el.scrollTop - el.clientHeight;
		if (dist < 200) {
			el.scrollTop = el.scrollHeight;
		}
	}, [messages.length, lastPartsLen, lastTextLen]);

	// 다른 대화 전환 시 abort.
	const prevActiveId = useRef<string | null>(activeId);
	useEffect(() => {
		const prev = prevActiveId.current;
		if (prev && prev !== activeId) {
			streamRef.current?.abort();
			streamRef.current = null;
			setBusy(false);
		}
		prevActiveId.current = activeId;
	}, [activeId]);

	const runStream = useCallback(
		(question: string, history: Array<{ role: 'user' | 'assistant'; text: string }>) => {
			setBusy(true);
			const workspaceCtx = active?.workspaceContext;
			streamRef.current = streamAsk(
				{ question, history, company: workspaceCtx?.stockCode },
				{
					onTextDelta: (delta) => appendTextDelta(delta),
					onToolStart: (t) => addToolStart(t),
					onToolResult: (r) => setToolResult(r.id, r),
					onViewSpec: (v) => addViewSpec(v),
					onDone: () => {
						setLastLoading(false);
						setBusy(false);
						streamRef.current = null;
					},
					onError: (err) => {
						setLastError(err.message);
						setBusy(false);
						streamRef.current = null;
					},
				},
			);
		},
		[
			active?.workspaceContext,
			appendTextDelta,
			addToolStart,
			setToolResult,
			addViewSpec,
			setLastLoading,
			setLastError,
		],
	);

	// 현재 대화 → history (서버 max 50, UI 는 20 으로 cap). 마지막 placeholder 어시스턴트는 제외.
	function buildHistory(): Array<{ role: 'user' | 'assistant'; text: string }> {
		const cap = 20;
		const out: Array<{ role: 'user' | 'assistant'; text: string }> = [];
		for (const m of messages) {
			if (m.loading) continue;
			const text = m.parts
				.map((p) => (p.type === 'text' ? p.text : ''))
				.join('')
				.trim();
			if (!text) continue;
			out.push({ role: m.role, text });
		}
		return out.slice(-cap);
	}

	function handleSend() {
		const q = input.trim();
		if (!q || busy) return;
		const history = buildHistory();
		addMessage('user', q);
		addMessage('assistant', '', true);
		setInput('');
		runStream(q, history);
	}

	function handleStop() {
		streamRef.current?.abort();
		abortRunningTools();
		setLastError('사용자가 중단했습니다');
		setBusy(false);
		streamRef.current = null;
	}

	function handleRegenerate() {
		if (busy) return;
		const userText = popLastAssistantAndGetUserText();
		if (!userText) return;
		// pop 한 뒤 남은 messages 가 history. (pop 으로 user/assistant 제거됐으니 prev 컨텍스트만)
		const history = buildHistory();
		addMessage('user', userText);
		addMessage('assistant', '', true);
		runStream(userText, history);
	}

	function handleNewConversation() {
		streamRef.current?.abort();
		streamRef.current = null;
		setBusy(false);
		setInput('');
		newConversation();
	}

	// 마지막 assistant 메시지에만 regenerate 버튼.
	const lastAssistantIdx = (() => {
		for (let i = messages.length - 1; i >= 0; i--) {
			if (messages[i]?.role === 'assistant') return i;
		}
		return -1;
	})();

	if (!hasMessages) {
		return (
			<EmptyState
				input={input}
				setInput={setInput}
				onSend={handleSend}
				onStop={handleStop}
				onNewConversation={handleNewConversation}
				busy={busy}
			/>
		);
	}

	return (
		<div className="flex flex-1 flex-col min-h-0 relative">
			<ScrollArea
				className="flex-1 min-h-0"
				viewportRef={viewportRef}
			>
				<div className="mx-auto max-w-3xl py-6">
					{messages.map((m, i) => (
						<ChatMessage
							key={m.id}
							message={m}
							onRegenerate={i === lastAssistantIdx ? handleRegenerate : undefined}
							canRegenerate={i === lastAssistantIdx && !busy}
						/>
					))}
				</div>
			</ScrollArea>
			<ScrollToBottomButton scrollContainer={viewportRef.current} />
			<div className="mx-auto w-full max-w-3xl px-4 pb-6">
				<Composer
					value={input}
					onChange={setInput}
					onSend={handleSend}
					onStop={handleStop}
					onNewConversation={handleNewConversation}
					busy={busy}
				/>
			</div>
		</div>
	);
}
