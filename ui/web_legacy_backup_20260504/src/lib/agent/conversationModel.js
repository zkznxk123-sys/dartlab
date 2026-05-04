export function createThreadMessage(role, content = "", extra = {}) {
	return {
		id: extra.id || `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
		role,
		text: content,
		content,
		parts: extra.parts || (content ? [{ type: "text", id: `text-${Date.now()}`, content }] : []),
		createdAt: extra.createdAt || Date.now(),
		...extra,
	};
}

export function buildConversationHistory(conv = null) {
	const history = [];
	let lastAnalyzedCode = null;
	if (!conv) return { history, lastAnalyzedCode };

	const messages = conv.messages.slice(0, -2);
	for (const message of messages) {
		if (!["user", "assistant"].includes(message.role)) continue;
		const text = message.text || message.content || "";
		if (!text.trim() || message.error || message.loading) continue;

		const entry = { role: message.role, content: text };
		if (message.role === "assistant" && message.meta?.stockCode) {
			entry.metadata = {
				company: message.meta.company || message.company,
				stockCode: message.meta.stockCode,
				modules: message.meta.includedModules || null,
				market: message.meta.market || null,
				topic: message.meta.topic || null,
				topicLabel: message.meta.topicLabel || null,
				dialogueMode: message.meta.dialogueMode || null,
				questionTypes: message.meta.questionTypes || null,
				userGoal: message.meta.userGoal || null,
			};
			lastAnalyzedCode = message.meta.stockCode;
		}
		history.push(entry);
	}

	return { history, lastAnalyzedCode };
}

export function appendTextPart(message, delta) {
	const parts = Array.isArray(message.parts) ? [...message.parts] : [];
	const last = parts[parts.length - 1];
	if (last?.type === "text") {
		parts[parts.length - 1] = { ...last, content: `${last.content || ""}${delta}` };
	} else {
		parts.push({ type: "text", id: `text-${Date.now()}-${parts.length}`, content: delta });
	}
	return parts;
}

export function appendActivityPart(message, activity) {
	const parts = Array.isArray(message.parts) ? [...message.parts] : [];
	parts.push({
		type: "activity",
		id: `activity-${Date.now()}-${parts.length}`,
		status: activity.status || "done",
		summary: activity.summary || "",
		refs: activity.refs || [],
	});
	return parts.slice(-80);
}

export function upsertToolPart(message, tool) {
	const parts = Array.isArray(message.parts) ? [...message.parts] : [];
	const idx = parts.findIndex((part) => part.type === "tool" && part.toolCallId === tool.toolCallId);
	const next = {
		type: "tool",
		id: tool.toolCallId || `tool-${Date.now()}`,
		toolCallId: tool.toolCallId,
		name: tool.toolName || "tool",
		status: tool.status || "running",
		summary: tool.summary || "",
		refs: tool.refs || [],
		artifacts: tool.artifacts || [],
	};
	if (idx >= 0) parts[idx] = { ...parts[idx], ...next };
	else parts.push(next);
	return parts;
}

export function appendFailurePart(message, failure) {
	const parts = Array.isArray(message.parts) ? [...message.parts] : [];
	parts.push({
		type: "failure",
		id: `failure-${Date.now()}-${parts.length}`,
		summary: failure.message || "최종 답변을 생성하지 못했습니다.",
	});
	return parts;
}
