// 다중 대화 + localStorage 영속화.
// Message 는 parts[] 시간순 배열 — text/tool/viewSpec 이 도착 순서대로 누적된다.
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type Role = 'user' | 'assistant';

export type ToolStatus = 'running' | 'done' | 'error';

export interface TextPart {
	type: 'text';
	text: string;
}

export interface ToolPart {
	type: 'tool';
	id: string;
	name: string;
	args: unknown;
	status: ToolStatus;
	result?: unknown;
	error?: string;
	summary?: string;
	startedAt: number;
	finishedAt?: number;
}

export interface ViewSpecPart {
	type: 'viewSpec';
	id: string;
	spec: unknown;
	title?: string;
}

export type Part = TextPart | ToolPart | ViewSpecPart;

export interface Message {
	id: string;
	role: Role;
	parts: Part[];
	createdAt: number;
	loading?: boolean;
	error?: string;
}

export interface RefDetail {
	id: string;
	kind: string;
	title: string;
	source: string;
	sourceType: 'internal' | 'external' | 'llm' | string;
	payload?: Record<string, unknown>;
	hasMore?: boolean;
}

export interface Conversation {
	id: string;
	title: string;
	messages: Message[];
	createdAt: number;
	updatedAt: number;
	pinnedAt?: number; // 고정 timestamp — 없으면 미고정.
	refs?: Record<string, RefDetail>; // refId → RefDetail. evidence chip preview 용.
	refToToolMap?: Record<string, string>; // refId → toolCallId. click-to-trace 용.
	workspaceContext?: { stockCode: string; market?: string; corpName?: string };
	highlightedToolCallId?: string; // flashTool 액션이 set, 1.5 초 후 자동 해제.
}

interface ChatState {
	conversations: Conversation[];
	activeId: string | null;

	getActive: () => Conversation | null;
	newConversation: () => string;
	switchConversation: (id: string) => void;
	deleteConversation: (id: string) => void;
	clearAll: () => void;

	// 단순 텍스트 메시지 추가 (사용자 발화 + assistant placeholder 양쪽).
	addMessage: (role: Role, text: string, loading?: boolean) => void;

	// 마지막 assistant 메시지에 text delta 누적 — 마지막 part 가 text 면 concat, 아니면 새 text part push.
	appendTextDelta: (delta: string) => void;

	// 마지막 assistant 메시지 parts[] 에 tool part push.
	addToolStart: (tool: { id: string; name: string; args: unknown; startedAt: number }) => void;

	// id 매칭 tool part 의 status/result/error/summary 갱신.
	// refDetails 가 오면 conversation.refs 에 흡수 + refToToolMap 빌드.
	setToolResult: (
		toolId: string,
		payload: {
			status: 'done' | 'error';
			result?: unknown;
			error?: string;
			summary?: string;
			refs?: string[];
			refDetails?: RefDetail[];
		},
	) => void;

	// 마지막 assistant 메시지 parts[] 에 viewSpec part push.
	addViewSpec: (v: { id: string; spec: unknown; title?: string }) => void;

	setLastLoading: (loading: boolean) => void;
	setLastError: (error: string) => void;

	// 마지막 assistant 메시지 제거 + 마지막 사용자 메시지 텍스트 반환. regenerate 흐름용.
	popLastAssistantAndGetUserText: () => string | null;

	// 마지막 메시지의 모든 도구 중 running 인 것을 error 로 강등 (중단 시).
	abortRunningTools: () => void;

	// 대화 제목 변경 (사용자 inline edit).
	renameConversation: (id: string, title: string) => void;

	// 대화 고정 토글.
	togglePin: (id: string) => void;

	// 워크스페이스 컨텍스트 (현재 분석 회사) 설정/해제.
	setWorkspaceContext: (ctx: { stockCode: string; market?: string; corpName?: string } | null) => void;

	// 특정 tool call 강조 (click-to-trace) — 1.5 초 후 자동 해제.
	flashTool: (toolCallId: string) => void;
}

const newId = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 8);

function makeConv(): Conversation {
	const now = Date.now();
	return { id: newId(), title: '새 대화', messages: [], createdAt: now, updatedAt: now };
}

function updateConv(
	convs: Conversation[],
	id: string | null,
	mut: (c: Conversation) => Conversation,
): Conversation[] {
	if (!id) return convs;
	return convs.map((c) => (c.id === id ? mut(c) : c));
}

function updateLastMessage(c: Conversation, mut: (m: Message) => Message): Conversation {
	const msgs = [...c.messages];
	const last = msgs[msgs.length - 1];
	if (!last) return c;
	msgs[msgs.length - 1] = mut(last);
	return { ...c, messages: msgs, updatedAt: Date.now() };
}

export const useChat = create<ChatState>()(
	persist(
		(set, get) => ({
			conversations: [],
			activeId: null,

			getActive: () => {
				const s = get();
				return s.conversations.find((c) => c.id === s.activeId) ?? null;
			},

			newConversation: () => {
				const c = makeConv();
				set({ conversations: [c, ...get().conversations], activeId: c.id });
				return c.id;
			},

			switchConversation: (id) => set({ activeId: id }),

			deleteConversation: (id) => {
				const remaining = get().conversations.filter((c) => c.id !== id);
				const activeId = get().activeId === id ? (remaining[0]?.id ?? null) : get().activeId;
				set({ conversations: remaining, activeId });
			},

			clearAll: () => set({ conversations: [], activeId: null }),

			addMessage: (role, text, loading = false) => {
				let activeId = get().activeId;
				if (!activeId) activeId = get().newConversation();
				const parts: Part[] = text ? [{ type: 'text', text }] : [];
				const m: Message = { id: newId(), role, parts, createdAt: Date.now(), loading };
				set({
					conversations: updateConv(get().conversations, activeId, (c) => ({
						...c,
						messages: [...c.messages, m],
						title: c.messages.length === 0 && role === 'user' ? text.slice(0, 24) : c.title,
						updatedAt: Date.now(),
					})),
				});
			},

			appendTextDelta: (delta) => {
				const id = get().activeId;
				set({
					conversations: updateConv(get().conversations, id, (c) =>
						updateLastMessage(c, (m) => {
							const last = m.parts[m.parts.length - 1];
							if (last && last.type === 'text') {
								const parts = m.parts.slice(0, -1);
								parts.push({ type: 'text', text: last.text + delta });
								return { ...m, parts };
							}
							return { ...m, parts: [...m.parts, { type: 'text', text: delta }] };
						}),
					),
				});
			},

			addToolStart: (tool) => {
				const id = get().activeId;
				set({
					conversations: updateConv(get().conversations, id, (c) =>
						updateLastMessage(c, (m) => ({
							...m,
							parts: [
								...m.parts,
								{
									type: 'tool',
									id: tool.id,
									name: tool.name,
									args: tool.args,
									status: 'running',
									startedAt: tool.startedAt,
								},
							],
						})),
					),
				});
			},

			setToolResult: (toolId, payload) => {
				const id = get().activeId;
				set({
					conversations: updateConv(get().conversations, id, (c) => {
						// 1) tool part 갱신
						const next = updateLastMessage(c, (m) => ({
							...m,
							parts: m.parts.map((p) =>
								p.type === 'tool' && p.id === toolId
									? {
											...p,
											status: payload.status,
											result: payload.result,
											error: payload.error,
											summary: payload.summary,
											finishedAt: Date.now(),
										}
									: p,
							),
						}));
						// 2) conversation.refs / refToToolMap 흡수
						const refsMap = { ...(next.refs ?? {}) };
						const toolMap = { ...(next.refToToolMap ?? {}) };
						for (const ref of payload.refDetails ?? []) {
							if (!ref.id) continue;
							refsMap[ref.id] = ref;
							toolMap[ref.id] = toolId;
						}
						// refDetails 없어도 refs (id 만) 있으면 매핑은 보존
						for (const refId of payload.refs ?? []) {
							if (!refId || toolMap[refId]) continue;
							toolMap[refId] = toolId;
						}
						return { ...next, refs: refsMap, refToToolMap: toolMap };
					}),
				});
			},

			addViewSpec: (v) => {
				const id = get().activeId;
				set({
					conversations: updateConv(get().conversations, id, (c) =>
						updateLastMessage(c, (m) => ({
							...m,
							parts: [...m.parts, { type: 'viewSpec', id: v.id, spec: v.spec, title: v.title }],
						})),
					),
				});
			},

			setLastLoading: (loading) => {
				const id = get().activeId;
				set({
					conversations: updateConv(get().conversations, id, (c) =>
						updateLastMessage(c, (m) => ({ ...m, loading })),
					),
				});
			},

			setLastError: (error) => {
				const id = get().activeId;
				set({
					conversations: updateConv(get().conversations, id, (c) =>
						updateLastMessage(c, (m) => ({ ...m, error, loading: false })),
					),
				});
			},

			popLastAssistantAndGetUserText: () => {
				const id = get().activeId;
				if (!id) return null;
				let userText: string | null = null;
				const next = get().conversations.map((c) => {
					if (c.id !== id) return c;
					const msgs = [...c.messages];
					// 마지막이 assistant 면 제거
					if (msgs.length && msgs[msgs.length - 1]?.role === 'assistant') {
						msgs.pop();
					}
					// 그 직전이 user 면 텍스트 추출
					const last = msgs[msgs.length - 1];
					if (last?.role === 'user') {
						userText = last.parts
							.map((p) => (p.type === 'text' ? p.text : ''))
							.join('')
							.trim();
						msgs.pop(); // user 도 제거 → addMessage 로 다시 push 할거임
					}
					return { ...c, messages: msgs, updatedAt: Date.now() };
				});
				set({ conversations: next });
				return userText;
			},

			abortRunningTools: () => {
				const id = get().activeId;
				set({
					conversations: updateConv(get().conversations, id, (c) =>
						updateLastMessage(c, (m) => ({
							...m,
							parts: m.parts.map((p) =>
								p.type === 'tool' && p.status === 'running'
									? { ...p, status: 'error' as const, error: '중단됨', finishedAt: Date.now() }
									: p,
							),
						})),
					),
				});
			},

			renameConversation: (id, title) => {
				const trimmed = title.trim() || '새 대화';
				set({
					conversations: get().conversations.map((c) =>
						c.id === id ? { ...c, title: trimmed.slice(0, 80), updatedAt: Date.now() } : c,
					),
				});
			},

			togglePin: (id) => {
				set({
					conversations: get().conversations.map((c) =>
						c.id === id ? { ...c, pinnedAt: c.pinnedAt ? undefined : Date.now() } : c,
					),
				});
			},

			setWorkspaceContext: (ctx) => {
				const id = get().activeId;
				if (!id) return;
				set({
					conversations: get().conversations.map((c) =>
						c.id === id ? { ...c, workspaceContext: ctx ?? undefined } : c,
					),
				});
			},

			flashTool: (toolCallId) => {
				const id = get().activeId;
				if (!id) return;
				set({
					conversations: get().conversations.map((c) =>
						c.id === id ? { ...c, highlightedToolCallId: toolCallId } : c,
					),
				});
				setTimeout(() => {
					const cur = get().activeId;
					if (cur !== id) return;
					set({
						conversations: get().conversations.map((c) =>
							c.id === id && c.highlightedToolCallId === toolCallId
								? { ...c, highlightedToolCallId: undefined }
								: c,
						),
					});
				}, 1500);
			},
		}),
		{
			name: 'dartlab-chat',
			onRehydrateStorage: () => (state) => {
				if (!state) return;
				// stale loading 리셋 + persist 직후 running tool 은 error 로 강등 (재시작 후 결과 안 옴).
				state.conversations = state.conversations.map((c) => ({
					...c,
					messages: c.messages.map((m) => ({
						...m,
						loading: false,
						parts: (m.parts ?? []).map((p) =>
							p.type === 'tool' && p.status === 'running'
								? { ...p, status: 'error' as ToolStatus, error: '중단됨' }
								: p,
						),
					})),
				}));
			},
		},
	),
);
