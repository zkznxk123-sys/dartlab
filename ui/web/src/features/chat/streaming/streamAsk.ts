// POST /api/ask SSE 클라이언트 — fetch + ReadableStream 직접 파싱.
// EventSource 는 POST 미지원이라 manual parse.
// AG-UI 이벤트 — TEXT_MESSAGE_CONTENT · TOOL_CALL_START · TOOL_CALL_RESULT · VIEW_SPEC · ACTIVITY_DELTA ·
//   RUN_FINISHED · RUN_ERROR — 를 콜백으로 분기.

export interface AskRequest {
	question: string;
	company?: string;
	provider?: string;
	role?: string;
	model?: string;
}

export interface ToolStartPayload {
	id: string;
	name: string;
	args: unknown;
	startedAt: number;
}

export interface ToolResultPayload {
	id: string;
	status: 'done' | 'error';
	result?: unknown;
	error?: string;
	summary?: string;
}

export interface ViewSpecPayload {
	id: string;
	spec: unknown;
	title?: string;
}

export interface ActivityPayload {
	summary?: string;
	passLabel?: string;
}

export interface AskCallbacks {
	onTextDelta?: (delta: string) => void;
	onToolStart?: (t: ToolStartPayload) => void;
	onToolResult?: (r: ToolResultPayload) => void;
	onViewSpec?: (v: ViewSpecPayload) => void;
	onActivity?: (a: ActivityPayload) => void;
	onEvent?: (event: { type: string; data: unknown }) => void;
	onDone?: () => void;
	onError?: (err: Error) => void;
}

export interface AskStreamControl {
	abort: () => void;
	promise: Promise<void>;
}

interface ToolStartEvent {
	toolCallId?: string;
	toolName?: string;
	args?: unknown;
	[k: string]: unknown;
}

interface ToolResultEvent {
	toolCallId?: string;
	status?: 'done' | 'error' | string;
	result?: unknown;
	error?: string;
	summary?: string;
	[k: string]: unknown;
}

interface ViewSpecEvent {
	id?: string;
	spec?: unknown;
	title?: string;
	[k: string]: unknown;
}

function asObj(x: unknown): Record<string, unknown> | null {
	return x && typeof x === 'object' ? (x as Record<string, unknown>) : null;
}

export function streamAsk(req: AskRequest, cb: AskCallbacks): AskStreamControl {
	const controller = new AbortController();
	const tag = Math.random().toString(36).slice(2, 6);
	console.log(`[ask:${tag}] start`);
	controller.signal.addEventListener('abort', () =>
		console.log(`[ask:${tag}] ABORTED reason=`, controller.signal.reason),
	);

	const promise = (async () => {
		try {
			const resp = await fetch('/api/ask', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
				body: JSON.stringify({ ...req, stream: true }),
				signal: controller.signal,
			});
			console.log(`[ask:${tag}] resp status=${resp.status}`);

			if (!resp.ok) {
				const text = await resp.text().catch(() => '');
				throw new Error(`HTTP ${resp.status}: ${text || resp.statusText}`);
			}
			if (!resp.body) throw new Error('no response body');

			const reader = resp.body.getReader();
			const decoder = new TextDecoder();
			let buffer = '';
			let chunkCount = 0;

			for (;;) {
				const { value, done } = await reader.read();
				if (done) {
					console.log(`[ask:${tag}] reader done, chunks=${chunkCount}`);
					break;
				}
				chunkCount++;
				// sse_starlette 는 \r\n 사용. \n 으로 정규화 후 파싱.
				buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n');

				let sepIdx: number;
				while ((sepIdx = buffer.indexOf('\n\n')) !== -1) {
					const raw = buffer.slice(0, sepIdx);
					buffer = buffer.slice(sepIdx + 2);
					if (!raw.trim()) continue;

					let eventName = 'message';
					const dataLines: string[] = [];
					for (const line of raw.split('\n')) {
						if (line.startsWith('event:')) eventName = line.slice(6).trim();
						else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
					}
					const dataStr = dataLines.join('\n');
					if (!dataStr) continue;

					let parsed: unknown = dataStr;
					try {
						parsed = JSON.parse(dataStr);
					} catch {
						/* keep as string */
					}

					cb.onEvent?.({ type: eventName, data: parsed });
					dispatch(eventName, parsed, cb);
				}
			}

			cb.onDone?.();
		} catch (err) {
			if ((err as Error).name === 'AbortError') return;
			cb.onError?.(err as Error);
		}
	})();

	return { abort: () => controller.abort(), promise };
}

function dispatch(eventName: string, parsed: unknown, cb: AskCallbacks) {
	const obj = asObj(parsed);
	if (!obj) return;
	// 일부 게이트웨이 구현은 envelope.type 으로도 이벤트명 전송 — 둘 중 하나로 판정.
	const name = eventName !== 'message' ? eventName : typeof obj.type === 'string' ? obj.type : '';

	switch (name) {
		case 'TEXT_MESSAGE_CONTENT':
		case 'text_delta': {
			const delta = obj.delta;
			if (typeof delta === 'string' && delta) cb.onTextDelta?.(delta);
			break;
		}
		case 'TOOL_CALL_START': {
			const t = obj as ToolStartEvent;
			if (typeof t.toolCallId === 'string' && typeof t.toolName === 'string') {
				cb.onToolStart?.({
					id: t.toolCallId,
					name: t.toolName,
					args: t.args ?? {},
					startedAt: Date.now(),
				});
			}
			break;
		}
		case 'TOOL_CALL_RESULT': {
			// TOOL_CALL_END 는 status 확정용으로만 따로 옴 (result 필드 없음) — UI 갱신 트리거 아님.
			const t = obj as ToolResultEvent;
			if (typeof t.toolCallId !== 'string') break;
			const status: 'done' | 'error' = t.status === 'error' ? 'error' : 'done';
			cb.onToolResult?.({
				id: t.toolCallId,
				status,
				result: t.result,
				error: typeof t.error === 'string' ? t.error : undefined,
				summary: typeof t.summary === 'string' ? t.summary : undefined,
			});
			break;
		}
		case 'VIEW_SPEC': {
			const v = obj as ViewSpecEvent;
			if (typeof v.id === 'string' && v.spec !== undefined) {
				cb.onViewSpec?.({
					id: v.id,
					spec: v.spec,
					title: typeof v.title === 'string' ? v.title : undefined,
				});
			}
			break;
		}
		case 'ACTIVITY_DELTA': {
			cb.onActivity?.({
				summary: typeof obj.summary === 'string' ? obj.summary : undefined,
				passLabel: typeof obj.passLabel === 'string' ? obj.passLabel : undefined,
			});
			break;
		}
		case 'RUN_ERROR': {
			const msg = typeof obj.message === 'string' ? obj.message : 'run failed';
			cb.onError?.(new Error(msg));
			break;
		}
		default:
			// TEXT_MESSAGE_START / TEXT_MESSAGE_END / STATE_SNAPSHOT / STATE_DELTA / RUN_FINISHED 는 skip.
			break;
	}
}
