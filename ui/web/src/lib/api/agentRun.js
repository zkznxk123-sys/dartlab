import { BASE } from "./http.js";

const ALLOWED_EVENTS = new Set([
	"TEXT_MESSAGE_START",
	"TEXT_MESSAGE_CONTENT",
	"TEXT_MESSAGE_END",
	"TOOL_CALL_START",
	"TOOL_CALL_ARGS",
	"TOOL_CALL_END",
	"TOOL_CALL_RESULT",
	"STATE_SNAPSHOT",
	"STATE_DELTA",
	"MESSAGES_SNAPSHOT",
	"ACTIVITY_SNAPSHOT",
	"ACTIVITY_DELTA",
	"VIEW_SPEC",
	"RUN_FINISHED",
	"RUN_ERROR",
]);

export function runAgentStream({ threadId, messages, provider, model, role, workspaceContext }, callbacks = {}) {
	const controller = new AbortController();
	fetch(`${BASE}/api/agent/runs`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({
			threadId,
			messages,
			agentId: "dartlab-research",
			provider,
			model,
			role,
			workspaceContext,
			stream: true,
		}),
		signal: controller.signal,
	})
		.then(async (res) => {
			if (!res.ok) {
				const err = await res.json().catch(() => ({}));
				callbacks.onError?.({ message: err.detail || "Agent Gateway 실행 실패" });
				return;
			}
			await readEventStream(res.body, callbacks);
		})
		.catch((err) => {
			if (err.name !== "AbortError") callbacks.onError?.({ message: err.message || "Agent Gateway 연결 실패" });
		});
	return { abort: () => controller.abort() };
}

async function readEventStream(body, callbacks) {
	const reader = body.getReader();
	const decoder = new TextDecoder();
	let buffer = "";
	let eventName = null;

	while (true) {
		const { done, value } = await reader.read();
		if (done) break;
		buffer += decoder.decode(value, { stream: true });
		const lines = buffer.split("\n");
		buffer = lines.pop() || "";
		for (const line of lines) {
			if (line.startsWith("event:")) {
				eventName = line.slice(6).trim();
				continue;
			}
			if (!line.startsWith("data:") || !eventName) continue;
			const payload = parsePayload(line.slice(5).trim());
			if (!payload || !ALLOWED_EVENTS.has(eventName)) {
				eventName = null;
				continue;
			}
			dispatch(eventName, payload, callbacks);
			eventName = null;
		}
	}
}

function parsePayload(raw) {
	try {
		return JSON.parse(raw);
	} catch {
		return null;
	}
}

function dispatch(type, payload, callbacks) {
	if (type === "TEXT_MESSAGE_START") callbacks.onTextStart?.(payload);
	else if (type === "TEXT_MESSAGE_CONTENT") callbacks.onTextDelta?.(payload);
	else if (type === "TEXT_MESSAGE_END") callbacks.onTextEnd?.(payload);
	else if (type === "ACTIVITY_DELTA" || type === "ACTIVITY_SNAPSHOT") callbacks.onActivity?.(payload);
	else if (type === "TOOL_CALL_START") callbacks.onToolStart?.(payload);
	else if (type === "TOOL_CALL_RESULT") callbacks.onToolResult?.(payload);
	else if (type === "VIEW_SPEC") callbacks.onViewSpec?.(payload);
	else if (type === "RUN_FINISHED") callbacks.onDone?.(payload);
	else if (type === "RUN_ERROR") callbacks.onError?.(payload);
	else if (type === "STATE_SNAPSHOT" || type === "STATE_DELTA") callbacks.onState?.(payload);
}
