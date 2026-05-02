import {
	applyUiActionSideEffect,
	collectViewsFromChartPayload,
	collectViewsFromUiAction,
} from "./uiActionBridge.js";

function getLastMessage(store) {
	const conv = store.active;
	if (!conv || conv.messages.length === 0) return null;
	return conv.messages[conv.messages.length - 1];
}

function appendMessageList(store, key, item) {
	const last = getLastMessage(store);
	const prev = last?.[key] || [];
	store.updateLastMessage({ [key]: [...prev, item] });
}

function isMissingDartKeyToolResult(name, result) {
	if (!["list_live_filings", "read_filing"].includes(name)) return false;
	if (typeof result !== "string") return false;
	return result.includes("OpenDART API 키") || result.includes("DART_API_KEY");
}

export function getLastAssistantStockCode(conv = null) {
	if (!conv) return null;
	for (let i = conv.messages.length - 1; i >= 0; i -= 1) {
		const message = conv.messages[i];
		if (message.role === "assistant" && message.meta?.stockCode) {
			return message.meta.stockCode;
		}
	}
	return null;
}

export function buildConversationHistory(conv = null) {
	const history = [];
	let lastAnalyzedCode = null;
	if (!conv) return { history, lastAnalyzedCode };

	const messages = conv.messages.slice(0, -2);
	for (const message of messages) {
		if (!["user", "assistant"].includes(message.role)) continue;
		if (!message.text || !message.text.trim() || message.error || message.loading) continue;

		const entry = { role: message.role, text: message.text };
		if (message.role === "assistant" && message.meta?.stockCode) {
			entry.meta = {
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

export function createAskStreamCallbacks({
	store,
	workspace,
	uiStore,
	streamConvId,
	showToast,
	appendRenderViews,
	onStreamSettled,
	bumpScroll,
	onCompanySelect,
}) {
	const isStale = () => store.activeId !== streamConvId;
	const sideEffectContext = {
		workspace,
		uiStore,
		showToast,
		onCompanySelect,
	};

	// ── chunk 배치 처리: 토큰당 → 프레임당 1회 DOM 업데이트 ──
	let chunkBuffer = "";
	let chunkRafId = null;
	let textSegCounter = 0;

	function flushChunkBuffer() {
		if (!chunkBuffer) return;
		const batch = chunkBuffer;
		chunkBuffer = "";
		chunkRafId = null;
		const last = getLastMessage(store);
		const prevText = last?.text || "";
		// segments: 마지막 segment 가 text 이면 append, 아니면 새 text segment 생성.
		// tool_call 이 중간에 들어오면 그 이후 chunk 는 새 text segment 로 분리되어 시간축 반영.
		const prevSegments = last?.segments || [];
		const lastSeg = prevSegments.length > 0 ? prevSegments[prevSegments.length - 1] : null;
		let nextSegments;
		if (lastSeg && lastSeg.kind === "text") {
			nextSegments = [
				...prevSegments.slice(0, -1),
				{ ...lastSeg, content: lastSeg.content + batch },
			];
		} else {
			textSegCounter += 1;
			nextSegments = [
				...prevSegments,
				{ kind: "text", id: `txt-${Date.now()}-${textSegCounter}`, content: batch, ts: Date.now() },
			];
		}
		store.updateLastMessage({ text: prevText + batch, segments: nextSegments });
		bumpScroll?.();
	}

	function cancelChunkRaf() {
		if (chunkRafId) {
			cancelAnimationFrame(chunkRafId);
			chunkRafId = null;
		}
	}

	return {
		onMeta(meta) {
			if (isStale()) return;
			const last = getLastMessage(store);
			const merged = { ...(last?.meta || {}), ...meta };
			const updates = { meta: merged };
			if (meta.company) {
				updates.company = meta.company;
				if (store.activeId && store.active?.title === "새 대화") {
					store.updateTitle(store.activeId, meta.company);
				}
			}
			if (meta.stockCode) updates.stockCode = meta.stockCode;
			if (meta.company || meta.stockCode) {
				workspace.syncCompanyFromMessage(meta, workspace.selectedCompany);
			}
			store.updateLastMessage(updates);
		},
		onSnapshot(snapshot) {
			if (isStale()) return;
			store.updateLastMessage({ snapshot });
		},
		onContext(ctx) {
			if (isStale()) return;
			appendMessageList(store, "contexts", {
				module: ctx.module,
				label: ctx.label,
				text: ctx.text,
			});
		},
		onSystemPrompt(data) {
			if (isStale()) return;
			// Legacy event: the workbench UI shows reference/inspect/execute/verify
			// trace instead of exposing raw prompt payloads as first-class evidence.
		},
		onToolCall(ev) {
			if (isStale()) return;
			const last = getLastMessage(store);
			const prevEvents = last?.toolEvents || [];
			const prevSegments = last?.segments || [];
			const newEvent = {
				type: "call",
				id: ev.id,
				name: ev.name,
				label: ev.label,
				arguments: ev.arguments,
			};
			const newSegment = {
				kind: "tool",
				id: ev.id,
				name: ev.name,
				label: ev.label,
				args: ev.arguments,
				status: "running",
				summary: null,
				result: null,
				progressLines: [],
				startedAt: Date.now(),
				endedAt: null,
			};
			store.updateLastMessage({
				toolEvents: [...prevEvents, newEvent],
				segments: [...prevSegments, newSegment],
			});
			bumpScroll?.();
		},
		onToolProgress(ev) {
			if (isStale()) return;
			if (!ev?.id || typeof ev.line !== "string") return;
			const last = getLastMessage(store);
			// 기존 toolProgress dict (호환)
			const progress = { ...(last?.toolProgress || {}) };
			const entry = progress[ev.id] ? { ...progress[ev.id] } : { lines: [] };
			const nextLines = entry.lines.length >= 200 ? entry.lines.slice(-199) : entry.lines.slice();
			nextLines.push(ev.line);
			entry.lines = nextLines;
			entry.updatedAt = Date.now();
			progress[ev.id] = entry;
			// segments 의 해당 tool segment 에도 직접 append
			const prevSegments = last?.segments || [];
			const nextSegments = prevSegments.map(s => {
				if (s.kind === "tool" && s.id === ev.id) {
					const lines = s.progressLines || [];
					const updated = lines.length >= 200 ? lines.slice(-199) : lines.slice();
					updated.push(ev.line);
					return { ...s, progressLines: updated };
				}
				return s;
			});
			store.updateLastMessage({ toolProgress: progress, segments: nextSegments });
			bumpScroll?.();
		},
		onToolResult(ev) {
			if (isStale()) return;
			const last = getLastMessage(store);
			const prevEvents = last?.toolEvents || [];
			const newEvent = {
				type: "result",
				id: ev.id,
				name: ev.name,
				label: ev.label,
				status: ev.status,
				summary: ev.summary,
				result: ev.result,
			};
			// segments 의 해당 tool segment 를 done/error 로 업데이트
			const prevSegments = last?.segments || [];
			const nextSegments = prevSegments.map(s => {
				if (s.kind === "tool" && s.id === ev.id) {
					return {
						...s,
						status: ev.status === "error" ? "error" : ev.status === "auth_required" ? "error" : "done",
						summary: ev.summary,
						result: ev.result,
						endedAt: Date.now(),
					};
				}
				return s;
			});
			store.updateLastMessage({
				toolEvents: [...prevEvents, newEvent],
				segments: nextSegments,
			});
			if (isMissingDartKeyToolResult(ev.name, ev.result)) {
				showToast?.("OpenDART API 키가 필요합니다. 설정 화면을 엽니다.", "warning", 5000);
				uiStore?.openSettings?.("openDart");
			}
		},
		onCodeRound(data) {
			if (isStale()) return;
			const last = getLastMessage(store);
			const rounds = [...(last?.codeRounds ?? [])];
			// Replace existing round (prevent duplicates on reconnect)
			const idx = rounds.findIndex(r => r.round === data.round);
			if (idx >= 0) rounds[idx] = data;
			else rounds.push(data);
			store.updateLastMessage({ codeRounds: rounds });
			bumpScroll?.();
		},
		onChart(data) {
			if (isStale()) return;
			appendRenderViews(collectViewsFromChartPayload(data));
		},
		onAgentTrace(phase, data) {
			if (isStale()) return;
			const last = getLastMessage(store);
			const prev = last?.agentTrace || [];
			store.updateLastMessage({
				agentTrace: [...prev, { phase, data, ts: Date.now() }],
			});
		},
		onChunk(text) {
			if (isStale()) return;
			chunkBuffer += text;
			if (chunkRafId) return;
			chunkRafId = requestAnimationFrame(flushChunkBuffer);
		},
		onDone(data) {
			if (isStale()) return;
			cancelChunkRaf();
			flushChunkBuffer();
			const last = getLastMessage(store);
			const duration = last?.startedAt
				? ((Date.now() - last.startedAt) / 1000).toFixed(1)
				: null;
			const updates = { loading: false, duration };
			if (data?.dataReady) {
				updates.meta = { ...(last?.meta || {}), dataReady: data.dataReady };
			}
			if (!last?.text?.trim()) {
				updates.text = "응답을 받지 못했습니다. AI 서버가 일시적으로 응답하지 않았을 수 있습니다.";
				updates.error = true;
				updates.retryable = true;
			}
			store.updateLastMessage(updates);
			store.flush();
			onStreamSettled?.();
			bumpScroll?.();
		},
		onUiAction(data) {
			if (isStale()) return;
			applyUiActionSideEffect(data, sideEffectContext);
			appendRenderViews(collectViewsFromUiAction(data));
		},
		onError(err, action) {
			if (isStale()) return;
			cancelChunkRaf();
			chunkBuffer = "";
			const retryable = ["retry", "rate_limit"].includes(action);
			store.updateLastMessage({ text: err, loading: false, error: true, errorAction: action || "", retryable });
			store.flush();
			onStreamSettled?.();
		},
	};
}
