import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { renderMarkdown } from "../lib/markdown.js";

const ROOT = process.cwd();

function read(relativePath) {
	return readFileSync(path.join(ROOT, relativePath), "utf8");
}

describe("UI contracts", () => {
	it("keeps workspace evidence state as a first-class store contract", () => {
		const source = read("src/lib/stores/workspace.svelte.js");

		expect(source).toContain("activeEvidenceSection");
		expect(source).toContain("selectedEvidenceIndex");
		expect(source).toContain("function openEvidence(section, index = null)");
		expect(source).toContain("function clearEvidenceSelection()");
		expect(source).toContain('if (activeTab !== "evidence")');
		expect(source).toContain("selectedEvidenceIndex = Number.isInteger(index) ? index : null");
	});

	it("routes message evidence clicks into the shared evidence workflow", () => {
		const appSource = read("src/App.svelte");
		const chatAreaSource = read("src/lib/components/ChatArea.svelte");
		const messageSource = read("src/lib/components/MessageBubble.svelte");

		expect(appSource).toContain("function handleOpenEvidence(section, index = null)");
		expect(appSource).toContain("workspace.openEvidence(section, index)");
		expect(appSource).toContain("onOpenEvidence={handleOpenEvidence}");

		expect(chatAreaSource).toContain("onOpenEvidence");
		expect(chatAreaSource).toContain("onOpenEvidence={onOpenEvidence}");

		expect(messageSource).toContain('onOpenEvidence("contexts", idx)');
		expect(messageSource).toContain('onOpenEvidence("snapshot")');
		expect(messageSource).toContain('onOpenEvidence(event?.type === "result" ? "tool-results" : "tool-calls", idx)');
		expect(messageSource).toContain("raw trace와 tool payload는 Evidence 패널로 보내고 채팅 본문은 message.parts를 렌더한다");
		expect(messageSource).not.toContain("<TransparencyBadges");
		expect(messageSource).not.toContain("Agent Trace");
	});

	it("normalizes Ask Workbench state-machine events into message parts", () => {
		const apiSource = read("src/lib/api.js");
		const vscodeSource = read("src/lib/api/vscodeTransport.js");
		const streamSource = read("src/lib/ai/chatStream.js");
		const messageSource = read("src/lib/components/MessageBubble.svelte");
		const surfaceSource = read("src/lib/components/AssistantMessageSurface.svelte");
		const activitySource = read("src/lib/components/ActivityTimeline.svelte");
		const toolRunSource = read("src/lib/components/ToolRunCard.svelte");
		const serverStreamSource = read("../../src/dartlab/server/streaming.py");

		expect(apiSource).toContain('else if (currentEvent === "activity") onActivity?.(parsed)');
		expect(apiSource).toContain('currentEvent === "tool_start" || currentEvent === "tool_call"');
		expect(apiSource).toContain('"plan", "reference"');
		expect(apiSource).toContain('"observation", "decision"');
		expect(apiSource).toContain('"draft", "verify", "answer", "unable"');
		expect(vscodeSource).toContain('case "activity":');
		expect(vscodeSource).toContain('case "tool_start":');
		expect(vscodeSource).toContain('case "observation":');
		expect(vscodeSource).toContain('case "unable":');
		expect(streamSource).toContain("onActivity(ev)");
		expect(streamSource).toContain('const CHAT_TOOL_PARTS = new Set(["run_python", "compile_visual", "pythonExec"])');
		expect(streamSource).not.toContain("const INTERNAL_TRACE_TOOLS");
		expect(streamSource).toContain("arguments: ev.input || ev.arguments");
		expect(streamSource).toContain("summary: ev.outputSummary || ev.summary");
		expect(streamSource).toContain("evidenceRefs: ev.evidenceRefs || []");
		expect(streamSource).toContain("fullResultArtifact: ev.fullResultArtifact || null");
		expect(streamSource).toContain("persisted: ev.persisted || false");
		expect(messageSource).toContain("message.parts || []");
		expect(messageSource).toContain("<AssistantMessageSurface");
		expect(surfaceSource).toContain("<ActivityTimeline");
		expect(surfaceSource).toContain("CHAT_TOOL_NAMES");
		expect(surfaceSource).toContain("timelineParts");
		expect(surfaceSource).toContain("<ToolRunCard");
		expect(surfaceSource).toContain("<FailureNotice");
		expect(surfaceSource).not.toContain("textParts =");
		expect(surfaceSource).not.toContain("toolParts =");
		expect(messageSource).not.toContain("작업 진행");
		expect(messageSource).toContain("messageParts.length === 0 && message.codeRounds?.length");
		expect(activitySource).toContain("activityParts.length}개 완료");
		expect(activitySource).toContain("activityParts.slice(-6)");
		expect(activitySource).not.toContain("finalize_answer_failed");
		expect(read("src/lib/components/FailureNotice.svelte")).not.toContain("provider_transport_failed");
		expect(serverStreamSource).toContain('_SPINNER_ACTIVITY_TOOLS = {"run_python", "compile_visual"}');
		expect(serverStreamSource).toContain('if data.get("action")');
		expect(serverStreamSource).toContain("_toolActivityId(data, name)");
		expect(toolRunSource).toContain('replaceAll("_", " ")');
		expect(toolRunSource).toContain("{displayName} 실행함");
	});

	it("keeps chat-first company selection separate from viewer navigation", () => {
		const appSource = read("src/App.svelte");

		expect(appSource).toContain("function handleCompanySelectForChat(company)");
		expect(appSource).toContain('workspace.switchView("chat")');
		expect(appSource).toContain("function handleCompanySelectForViewer(company)");
		expect(appSource).toContain("workspace.openViewer(company)");
	});

	it("keeps the workspace evidence panel readable and drill-down capable", () => {
		const evidenceTab = read("src/lib/components/workspace/EvidenceTab.svelte");
		const evidenceModal = read("src/lib/components/EvidenceModal.svelte");
		const evidenceLabels = read("src/lib/ai/evidenceLabels.js");

		expect(evidenceTab).toContain('data-evidence-section="snapshot"');
		expect(evidenceTab).toContain('data-evidence-section="contexts"');
		expect(evidenceTab).toContain('data-evidence-section="tool-calls"');
		expect(evidenceTab).toContain('data-evidence-section="tool-results"');
		expect(evidenceTab).toContain("tool-result");
		expect(evidenceTab).toContain("입력 원문");
		expect(evidenceTab).toContain("도구 결과");
		expect(evidenceTab).toContain("formatEvidenceLabel");
		expect(evidenceTab).toContain("getIncludedEvidenceLabels");
		expect(evidenceTab).toContain("formatToolLabel");
		expect(evidenceModal).toContain("formatEvidenceLabel");
		expect(evidenceModal).toContain("formatToolLabel");
		expect(evidenceLabels).toContain("성격별 비용 분류");
		expect(evidenceLabels).toContain("실시간 공시 목록 조회");

		// DataExplorer still orchestrates evidence section routing
		const explorer = read("src/lib/components/DataExplorer.svelte");
		expect(explorer).toContain("selectedEvidenceIndex");
	});

	it("keeps the empty state aligned to the README product message", () => {
		const source = read("src/lib/components/EmptyState.svelte");

		expect(source).toContain("재무 수치와 서술 텍스트");
		expect(source).toContain("표준화된 계정");
		expect(source).toContain("40개 모듈");
		expect(source).toContain("원문 근거");
		expect(source).toContain("Evidence First");
		expect(source).toContain("summarizeDataReady");
		expect(source).toContain("dataReadyInfo.label");
		expect(source).toContain("추천 질문");
	});

	it("preserves the stable streaming affordance in chat", () => {
		const source = read("src/lib/components/ChatArea.svelte");

		expect(source).toContain("followStream");
		expect(source).toContain("showJumpToLatest");
		expect(source).toContain("streamAnchor.scrollIntoView");
		expect(source).toContain("최신 응답으로 이동");
		expect(source).toContain("dataReady");
		expect(source).toContain("추천 질문");
	});

	it("renders disclosure text as a block-first report instead of raw text block listing", () => {
		const source = read("src/lib/components/SectionsViewer.svelte");

		expect(source).toContain("textDocument");
		expect(source).toContain("커버리지");
		expect(source).toContain("과거 유지");
		expect(source).toContain("selectTextTimelinePeriod");
		expect(source).toContain("비교 없음");
	});

	it("formats scientific notation in assistant markdown tables", () => {
		const html = renderMarkdown("| 항목 | 값 |\n| --- | ---: |\n| 현금 | 5.7856e13 |");

		expect(html).toContain("57,856,000,000,000");
		expect(html).not.toContain("5.7856e13");
	});
});
