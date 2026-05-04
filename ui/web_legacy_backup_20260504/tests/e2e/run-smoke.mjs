import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

const ROOT = process.cwd();

function assert(condition, message) {
	if (!condition) {
		throw new Error(message);
	}
}

function read(relativePath) {
	return readFileSync(path.join(ROOT, relativePath), "utf8");
}

function main() {
	const appSource = read("src/App.svelte");
	const workspaceSource = read("src/lib/stores/workspace.svelte.js");
	const explorerSource = read("src/lib/components/DataExplorer.svelte");
	const evidenceTabSource = read("src/lib/components/workspace/EvidenceTab.svelte");
	const chatAreaSource = read("src/lib/components/ChatArea.svelte");
	const messageSource = read("src/lib/components/ConversationMessage.svelte");
	const agentRunSource = read("src/lib/api/agentRun.js");
	const apiSource = read("src/lib/api.js");
	const buildIndexPath = path.join(ROOT, "build/index.html");

	assert(existsSync(buildIndexPath), "build/index.html is missing. Run npm run build first.");
	assert(appSource.includes("handleOpenEvidence"), "App.svelte is missing evidence routing.");
	assert(appSource.includes("onOpenEvidence={handleOpenEvidence}"), "ChatArea is not wired to evidence routing.");
	assert(workspaceSource.includes("openEvidence(section, index = null)"), "workspace store is missing openEvidence.");
	assert(workspaceSource.includes("clearEvidenceSelection()"), "workspace store is missing clearEvidenceSelection.");
	assert(evidenceTabSource.includes('data-evidence-section="tool-results"'), "EvidenceTab is missing tool-results evidence section.");
	assert(explorerSource.includes("copyWorkspaceLink"), "DataExplorer is missing workspace link action.");
	assert(appSource.includes("runAgentStream"), "App.svelte is not using the Agent Gateway stream.");
	assert(agentRunSource.includes("/api/agent/runs"), "Agent Gateway endpoint is missing.");
	assert(!apiSource.includes("export function askStream"), "Legacy web askStream should not be exported.");
	assert(chatAreaSource.includes("<ConversationMessage"), "ChatArea is not using the new conversation surface.");
	assert(!chatAreaSource.includes("<MessageBubble"), "ChatArea still renders the legacy MessageBubble surface.");
	assert(messageSource.includes("message.parts"), "ConversationMessage is missing message parts rendering.");
	assert(messageSource.includes("최신 응답으로 이동") || chatAreaSource.includes("최신 응답으로 이동"), "Jump-to-latest affordance is missing.");

	console.log("e2e smoke passed");
}

main();
