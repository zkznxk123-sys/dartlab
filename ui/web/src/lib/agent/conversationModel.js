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
	const explicitId = activity.id ? String(activity.id) : "";
	const idx = explicitId
		? parts.findIndex((p) => p.type === "activity" && p.id === explicitId)
		: -1;
	const next = {
		type: "activity",
		id: explicitId || `activity-${Date.now()}-${parts.length}`,
		status: activity.status || "done",
		summary: activity.summary || "",
		refs: activity.refs || [],
		timestamp: Date.now(),
	};
	// 백엔드 pass 메타 — groupLoops 가 같은 pass 끼리 묶기 위한 1 차 키.
	if (activity.passLabel) next.passLabel = String(activity.passLabel);
	if (activity.iteration !== undefined && activity.iteration !== null) next.iteration = activity.iteration;
	if (idx >= 0) {
		parts[idx] = { ...parts[idx], ...next };
		return parts.slice(-80);
	}
	parts.push(next);
	return parts.slice(-80);
}

export function upsertToolPart(message, tool) {
	const parts = Array.isArray(message.parts) ? [...message.parts] : [];
	const idx = parts.findIndex((part) => part.type === "tool" && part.toolCallId === tool.toolCallId);
	// args/result 는 partial update — START 에는 args, RESULT 에는 result/error.
	// 기존 값을 비우지 않고 이번 payload 가 명시적으로 준 키만 덮어쓴다.
	const incoming = {
		type: "tool",
		id: tool.toolCallId || `tool-${Date.now()}`,
		toolCallId: tool.toolCallId,
		name: tool.toolName || "tool",
		status: tool.status || "running",
		summary: tool.summary || "",
		refs: tool.refs || [],
		artifacts: tool.artifacts || [],
	};
	if (tool.args !== undefined) incoming.args = tool.args;
	if (tool.result !== undefined) incoming.result = tool.result;
	if (tool.error !== undefined) incoming.error = tool.error;
	// 백엔드 pass 메타 — groupLoops 가 같은 pass 끼리 묶기 위한 1 차 키.
	if (tool.passLabel) incoming.passLabel = String(tool.passLabel);
	if (tool.iteration !== undefined && tool.iteration !== null) incoming.iteration = tool.iteration;
	if (idx >= 0) parts[idx] = { ...parts[idx], ...incoming };
	else parts.push(incoming);
	return parts;
}

/**
 * activity 텍스트로부터 phase 추출 (계획/실행/검증/작성).
 * 도메인 6 막 분류 X — 실행 단계 분류만 (memory/feedback_chat_ui_separate_from_six_acts.md).
 */
function classifyPhase(summary) {
	const s = String(summary || "");
	if (/검증|verify|통과|숫자.*근거|날짜.*근거/.test(s)) return "verify";
	if (/답변.*작성|answer|최종|응답.*생성|generate|composing/.test(s)) return "compose";
	if (/계획|plan|brief|skill 검색|recipe/.test(s)) return "plan";
	// default — 도구 사용·진행 중인 단계는 "실행" 으로 표시 (이전엔 fallback 이 "계획"
	// 이라 도구 실행 중에도 "계획" 으로 보여 어색).
	return "execute";
}

const PHASE_LABEL = {
	plan: "계획",
	execute: "실행",
	verify: "검증",
	compose: "작성",
};

const PHASE_AVATAR = {
	plan: "/avatar-curious.png",
	execute: "/avatar-analyze.png",
	verify: "/avatar-detective.png",
	compose: "/avatar-writing.png",
};

/**
 * 연속된 activity part 들을 phase 단위로 묶어 activity-group 카드로 만든다.
 * 같은 phase 가 연속이면 한 그룹, phase 가 바뀌면 새 그룹.
 * tool/text/failure 같은 다른 type 이 끼면 그룹 종료.
 * 결과 part type: "activity-group" with phase, label, avatar, activities[], running.
 *
 * Working 카드 (ChatGPT/Claude 식) 표현용. 평면 ○ 리스트의 인지 부담 해결.
 */
export function groupActivities(parts) {
	const source = Array.isArray(parts) ? parts : [];
	const out = [];
	let bucket = null;
	for (const part of source) {
		if (part?.type === "activity") {
			const phase = classifyPhase(part.summary);
			if (!bucket || bucket.phase !== phase) {
				bucket = {
					type: "activity-group",
					id: `group-${phase}-${part.id || out.length}`,
					phase,
					label: PHASE_LABEL[phase] || "단계",
					avatar: PHASE_AVATAR[phase] || "/avatar.png",
					activities: [],
					running: false,
				};
				out.push(bucket);
			}
			bucket.activities.push(part);
			if (part.status === "running") bucket.running = true;
		} else {
			bucket = null;
			out.push(part);
		}
	}
	for (const item of out) {
		if (item.type === "activity-group") {
			item.running = item.activities.some((a) => a.status === "running");
			item.summary = item.activities[item.activities.length - 1]?.summary || "";
			const total = item.activities.length;
			const done = item.activities.filter((a) => a.status === "done" || a.status === "error").length;
			item.progress = total > 0 ? Math.round((done / total) * 100) : 0;
			const ts = item.activities
				.map((a) => a.timestamp || a.createdAt)
				.filter((t) => typeof t === "number" && t > 0);
			item.startedAt = ts.length ? Math.min(...ts) : null;
			item.lastAt = ts.length ? Math.max(...ts) : null;
		}
	}
	return out;
}

/**
 * 연속된 *조사형* 도구 호출 (ReadSkill / ReadCapability / GetSkillBody) 을 1 개
 * collapsed 카드로 fold. 실행형 도구 (RunPython / EngineCall / WebSearch / ...) 는
 * 그대로 individual `tool` part 유지.
 *
 * 답변 위에 11+ 카드가 평면으로 쌓이는 visual noise 해결. 사전조사 = "LLM 이
 * 무엇을 할지 결정" / 실행 = "실제 데이터 생성" 분리.
 *
 * 출력 part: { type: "tool-research-group", id, calls: [...individualTools],
 *              running, lastSummary, hasError }.
 */
const RESEARCH_TOOL_NAMES = new Set(["ReadSkill", "ReadCapability", "GetSkillBody"]);

export function groupTools(parts) {
	const source = Array.isArray(parts) ? parts : [];
	const out = [];
	let bucket = null;
	for (const part of source) {
		if (part?.type === "tool" && RESEARCH_TOOL_NAMES.has(part.name)) {
			if (!bucket) {
				bucket = {
					type: "tool-research-group",
					id: `research-${part.id || out.length}`,
					calls: [],
					running: false,
					hasError: false,
					lastSummary: "",
				};
				out.push(bucket);
			}
			bucket.calls.push(part);
		} else {
			bucket = null;
			out.push(part);
		}
	}
	for (const item of out) {
		if (item.type === "tool-research-group") {
			item.running = item.calls.some((c) => c.status === "running");
			item.hasError = item.calls.some((c) => c.status === "error");
			const last = item.calls[item.calls.length - 1];
			item.lastSummary = last?.summary || "";
		}
	}
	return out;
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

/**
 * 한 메시지 = 한 loop-card. 사용자 정의: "질문 → 답변까지 = 한 루프".
 *
 * activity / tool / skill 모두 단일 카드 안의 row 로 흡수. phase·kind·passLabel
 * 별 분리 폐기 — 평면 5+ 박스로 갈라지던 인지 부담 해소가 핵심.
 *
 * 입력 parts (시간 순). 출력:
 *   - 모든 activity / tool 는 단일 loop-card 1개로 묶임.
 *   - view-spec / text / failure 가 끼면 bucket 닫고 그 part 통과 후 다음 bucket.
 *
 * 출력 part: { type: "loop-card", id, label, status, running, errorCount, toolCount, activityCount, rows: [...] }
 *   rows[i] = { kind: "activity"|"tool"|"skill", ...원본 part 키 그대로 보존 }
 *
 * RESEARCH 도구 (ReadSkill·ReadCapability·GetSkillBody) 도 같은 카드 안 row.
 * kind="skill" 는 row 시각 표시용 (아이콘/라벨 분기) 만 보존.
 */
const RESEARCH_TOOL_NAMES_FOR_LOOP = new Set(["ReadSkill", "ReadCapability", "GetSkillBody"]);

export function groupLoops(parts) {
	const source = Array.isArray(parts) ? parts : [];
	const out = [];
	let bucket = null;

	function closeBucket() {
		if (!bucket) return;
		bucket.running = bucket.rows.some((r) => r.status === "running");
		bucket.errorCount = bucket.rows.filter((r) => r.status === "error").length;
		bucket.status = bucket.errorCount > 0 ? "error" : bucket.running ? "running" : "done";
		const lastWithSummary = [...bucket.rows].reverse().find((r) => r.summary);
		bucket.summary = lastWithSummary?.summary || "";
		bucket.toolCount = bucket.rows.filter((r) => r.kind === "tool" || r.kind === "skill").length;
		bucket.activityCount = bucket.rows.filter((r) => r.kind === "activity").length;
		// label — 첫 phase 또는 "분석". 메시지 단위 1 카드라 단순.
		const firstActivity = bucket.rows.find((r) => r.kind === "activity");
		const phase = firstActivity ? classifyPhase(firstActivity.summary) : null;
		bucket.label = phase ? PHASE_LABEL[phase] : "분석";
		bucket.avatar = PHASE_AVATAR[phase] || "/avatar.png";
		bucket = null;
	}

	for (const part of source) {
		if (!part || typeof part !== "object") continue;

		// loop-card 동위 — 통과 (view-spec 시각 답변, text 최종 답변, failure 실패 알림).
		if (part.type === "view-spec" || part.type === "text" || part.type === "failure") {
			closeBucket();
			out.push(part);
			continue;
		}

		const kind = rowKindFromPart(part);
		if (!kind) {
			closeBucket();
			out.push(part);
			continue;
		}

		// 한 메시지 안의 모든 도구·활동은 단일 loop-card 에 흡수.
		if (!bucket) {
			bucket = {
				type: "loop-card",
				id: `loop-${out.length}`,
				label: "분석",
				avatar: "/avatar.png",
				rows: [],
				running: false,
				status: "done",
				errorCount: 0,
				summary: "",
				toolCount: 0,
				activityCount: 0,
			};
			out.push(bucket);
		}
		bucket.rows.push({ ...part, kind });
	}
	closeBucket();
	return out;
}

function rowKindFromPart(part) {
	if (part.type === "activity") return "activity";
	if (part.type === "tool") {
		return RESEARCH_TOOL_NAMES_FOR_LOOP.has(part.name) ? "skill" : "tool";
	}
	return null;
}

/**
 * View-spec part — 차트·표·대시보드 같은 시각 답변을 메시지 흐름에 인라인.
 * spec 은 viewSpec.normalizeViewSpec 가 받는 모양 (widgets[]/charts[]/component).
 * 분석 워크벤치 정체성의 주체 — tool/activity 보다 시각적 위계가 높다.
 */
export function appendViewSpecPart(message, payload) {
	const parts = Array.isArray(message.parts) ? [...message.parts] : [];
	const spec = payload?.spec || payload?.view || payload;
	if (!spec) return parts;
	parts.push({
		type: "view-spec",
		id: payload?.id || `view-spec-${Date.now()}-${parts.length}`,
		spec,
		source: payload?.source || null,
		title: payload?.title || null,
	});
	return parts;
}
