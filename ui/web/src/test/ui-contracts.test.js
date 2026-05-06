import { readFileSync } from "node:fs";
import { existsSync } from "node:fs";
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
		const messageSource = read("src/lib/components/ConversationMessage.svelte");

		expect(appSource).toContain("function handleOpenEvidence(section, index = null)");
		expect(appSource).toContain("workspace.openEvidence(section, index)");
		expect(appSource).toContain("onOpenEvidence={handleOpenEvidence}");

		expect(chatAreaSource).toContain("onOpenEvidence");
		expect(chatAreaSource).toContain("<ConversationMessage");
		expect(chatAreaSource).not.toContain("<MessageBubble");

		expect(messageSource).toContain("message.parts");
		expect(messageSource).toContain("근거 {message.refs.length}개");
		expect(messageSource).toContain("파일 {message.artifacts.length}개");
		expect(messageSource).not.toContain("<TransparencyBadges");
		expect(messageSource).not.toContain("Agent Trace");
	});

	it("uses the Agent Gateway public event path for chat messages", () => {
		const appSource = read("src/App.svelte");
		const legacyApiSource = read("src/lib/api.js");
		const agentRunSource = read("src/lib/api/agentRun.js");
		const modelSource = read("src/lib/agent/conversationModel.js");
		const messageSource = read("src/lib/components/ConversationMessage.svelte");
		const serverGatewaySource = read("../../src/dartlab/server/agent_gateway.py");

		expect(appSource).toContain("runAgentStream");
		expect(appSource).toContain("appendActivityPart");
		expect(appSource).toContain("upsertToolPart");
		expect(appSource).not.toContain("askStream(");
		expect(appSource).not.toContain("$lib/ai/chatStream.js");
		expect(legacyApiSource).not.toContain("export function askStream");
		expect(agentRunSource).toContain("/api/agent/runs");
		expect(agentRunSource).toContain("TEXT_MESSAGE_CONTENT");
		expect(agentRunSource).toContain("TOOL_CALL_START");
		expect(agentRunSource).toContain("RUN_FINISHED");
		expect(modelSource).toContain("appendTextPart");
		expect(modelSource).toContain("appendActivityPart");
		expect(modelSource).toContain("upsertToolPart");
		expect(messageSource).toContain("visibleToolName");
		expect(messageSource).not.toContain("TransparencyBadges");
		expect(messageSource).not.toContain("Agent Trace");
		expect(serverGatewaySource).toContain("_ALLOWED_EVENTS");
		expect(serverGatewaySource).toContain("ACTIVITY_DELTA");
		expect(serverGatewaySource).toContain("RUN_ERROR");
		expect(serverGatewaySource).toContain('"search_reference": "search reference"');
		expect(existsSync(path.join(ROOT, "src/lib/ai/chatStream.js"))).toBe(false);
		expect(existsSync(path.join(ROOT, "src/lib/components/MessageBubble.svelte"))).toBe(false);
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
