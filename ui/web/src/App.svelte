<script>
	import "./app.css";
	import { onMount } from "svelte";
	import { fetchAiSuggestions } from "$lib/api.js";
	import { runAgentStream } from "$lib/api/agentRun.js";
	import {
		appendActivityPart,
		appendFailurePart,
		appendTextPart,
		appendViewSpecPart,
		buildConversationHistory,
		upsertToolPart,
	} from "$lib/agent/conversationModel.js";
	import { createSwipeHandler } from "$lib/utils.js";
	import { createConversationsStore } from "$lib/stores/conversations.svelte.js";
	import { createWorkspaceStore } from "$lib/stores/workspace.svelte.js";
	import { getUiStore } from "$lib/stores/ui.svelte.js";
	import { getUiMode } from "$lib/stores/uiMode.svelte.js";
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";
	import Sidebar from "$lib/components/Sidebar.svelte";
	import EmptyState from "$lib/components/EmptyState.svelte";
	import ChatArea from "$lib/components/ChatArea.svelte";
	import DashboardShell from "$lib/dashboard/DashboardShell.svelte";
	import SnapshotChip from "$lib/dashboard/SnapshotChip.svelte";
	import DeleteDialog from "$lib/components/DeleteDialog.svelte";
	import ToastNotification from "$lib/components/ToastNotification.svelte";
	import PanelResizer from "$lib/components/PanelResizer.svelte";
	import {
		Menu, PanelLeftClose, Coffee, Github, FileText, Cog,
	} from "lucide-svelte";
	import ProviderDropdown from "$lib/components/ProviderDropdown.svelte";
	import SocialIcons from "$lib/components/SocialIcons.svelte";
	import { isVSCode } from "$lib/api/transport.js";

	// ── Stores ──
	const ui = getUiStore();
	const uiMode = getUiMode();
	const dashboard = getDashboardStore();
	const store = createConversationsStore();
	const workspace = createWorkspaceStore();

	// ── State ──
	let inputText = $state("");
	let isLoading = $state(false);
	let currentStream = $state(null);
	let suggestedQuestions = $state([]);
	let onboardingDataReady = $state(null);
	let suggestionLoading = $state(false);
	let suggestRequestId = 0;
	const suggestionCache = new Map();

	// ── 모듈 선택 ──
	let selectedModules = $state(JSON.parse(localStorage.getItem("dartlab-modules") || "[]"));

	// ── 슬래시 명령어 ──
	function handleSlashCommand(cmd) {
		if (cmd === "new") handleNewChat();
		else if (cmd === "clear") {
			if (store.active) {
				store.active.messages = [];
				store.flush();
			}
		}
		else if (cmd === "provider" || cmd === "settings") ui.openSettings(cmd === "provider" ? "providers" : undefined);
		else if (cmd === "help") ui.showToast("Ctrl+K: 검색 / Ctrl+N: 새 대화 / /provider: 프로바이더 전환", "info", 5000);
	}

	// ── 워치리스트 ──
	let watchlist = $state(JSON.parse(localStorage.getItem("dartlab-watchlist") || "[]"));
	function persistWatchlist() { localStorage.setItem("dartlab-watchlist", JSON.stringify(watchlist)); }
	function addToWatchlist(code, name) {
		if (watchlist.some(w => w.code === code)) return;
		watchlist = [...watchlist, { code, name }];
		persistWatchlist();
	}
	function removeFromWatchlist(code) {
		watchlist = watchlist.filter(w => w.code !== code);
		persistWatchlist();
	}
	// ── 리사이저블 사이드바 ──
	let sidebarWidth = $state(260);
	function handleSidebarResize(delta) {
		sidebarWidth = Math.max(180, Math.min(400, sidebarWidth + delta));
	}

	// ── 모바일 스와이프 ──
	$effect(() => {
		if (!ui.isMobile) return;
		return createSwipeHandler(document.body, {
			edgeOnly: true,
			edgeWidth: 30,
			onSwipeRight: () => { if (!ui.sidebarOpen) ui.sidebarOpen = true; },
			onSwipeLeft: () => { if (ui.sidebarOpen) ui.sidebarOpen = false; },
		});
	});

	// ── Derived ──
	let activeMessages = $derived(store.active?.messages || []);
	let hasConversation = $derived(store.active && store.active.messages.length > 0);
	// provider 유효성은 ProviderDropdown과 sendMessage에서 개별 판단

	// ── Init ──
	// onMount: 컴포넌트가 DOM에 부착된 직후 1회만 실행. 모바일 호환.
	onMount(() => {
		ui.loadStatus();
	});

	$effect(() => {
		ui.checkMobile();
		const onResize = () => ui.checkMobile();
		window.addEventListener("resize", onResize);
		return () => window.removeEventListener("resize", onResize);
	});

	$effect(() => {
		const stockCode = workspace.selectedCompany?.stockCode || "";
		if (!stockCode) {
			suggestedQuestions = [];
			onboardingDataReady = null;
			suggestionLoading = false;
			return;
		}

		const cached = suggestionCache.get(stockCode);
		if (cached) {
			suggestedQuestions = cached.suggestions;
			onboardingDataReady = cached.dataReady;
			suggestionLoading = false;
			return;
		}

		const requestId = ++suggestRequestId;
		suggestedQuestions = [];
		onboardingDataReady = null;
		suggestionLoading = true;
		fetchAiSuggestions(stockCode)
			.then((payload) => {
				if (requestId !== suggestRequestId) return;
				const next = {
					suggestions: payload?.suggestions || [],
					dataReady: payload?.dataReady || null,
				};
				suggestionCache.set(stockCode, next);
				suggestedQuestions = next.suggestions;
				onboardingDataReady = next.dataReady;
				suggestionLoading = false;
			})
			.catch(() => {
				if (requestId !== suggestRequestId) return;
				suggestedQuestions = [];
				onboardingDataReady = null;
				suggestionLoading = false;
			});
	});

	// ── Helpers ──
	function syncSelectedCompanyFromConversation(conv) {
		if (!conv) {
			workspace.clearSelectedCompany();
			return;
		}
		for (let i = conv.messages.length - 1; i >= 0; i--) {
			const msg = conv.messages[i];
			if (msg.role === "assistant" && (msg.meta?.stockCode || msg.meta?.company || msg.company)) {
				workspace.syncCompanyFromMessage(
					{ company: msg.meta?.company || msg.company, stockCode: msg.meta?.stockCode },
					workspace.selectedCompany
				);
				return;
			}
		}
		workspace.clearSelectedCompany();
	}

	// ── Chat actions ──
	function handleNewChat() {
		store.createConversation();
		workspace.resetChatContext();
		inputText = "";
		isLoading = false;
		if (currentStream) { currentStream.abort(); currentStream = null; }
	}

	function handleSelectConversation(id) {
		store.setActive(id);
		syncSelectedCompanyFromConversation(store.active);
		inputText = "";
		isLoading = false;
		if (currentStream) { currentStream.abort(); currentStream = null; }
	}

	function handleDeleteConversation(id) {
		ui.deleteConfirmMode = "single";
		ui.deleteConfirmId = id;
	}
	function handleDeleteAllConversations() {
		ui.deleteConfirmMode = "all";
		ui.deleteConfirmId = "__all__";
	}

	function confirmDelete() {
		if (ui.deleteConfirmId) {
			if (ui.deleteConfirmMode === "all") {
				store.clearAll();
				workspace.resetChatContext();
				inputText = "";
				isLoading = false;
				if (currentStream) { currentStream.abort(); currentStream = null; }
				ui.deleteConfirmId = null;
				ui.deleteConfirmMode = "single";
				return;
			}
			store.deleteConversation(ui.deleteConfirmId);
			if (store.active) syncSelectedCompanyFromConversation(store.active);
			else workspace.resetChatContext();
			ui.deleteConfirmId = null;
			ui.deleteConfirmMode = "single";
		}
	}

	async function sendMessage(prefilledQuestion = null) {
		const question = (prefilledQuestion ?? inputText).trim();
		if (!question || isLoading) return;

		if (ui.statusLoading) {
			ui.showToast("프로바이더 확인 중입니다. 잠시 후 다시 시도해주세요.", "info");
			return;
		}
		if (!ui.activeProvider || !ui.providers[ui.activeProvider]?.available) {
			ui.showToast("먼저 AI Provider를 설정해주세요. 우상단 설정 버튼을 클릭하세요.");
			ui.openSettings();
			return;
		}
		const chatProvider = await ui.resolveChatProvider();
		if (!chatProvider) { ui.openSettings(); return; }

		if (!store.activeId) store.createConversation();
		const streamConvId = store.activeId;

		store.addMessage("user", question);
		inputText = "";
		isLoading = true;

		store.addMessage("assistant", "");
		store.updateLastMessage({ loading: true, startedAt: Date.now() });

		const conv = store.active;
		const { history, lastAnalyzedCode } = buildConversationHistory(conv);
		const companyHint = workspace.selectedCompany?.stockCode || lastAnalyzedCode || null;
		const agentMessages = [
			...history.map((msg) => ({ role: msg.role, content: msg.content || msg.text || "" })),
			{ role: "user", content: question },
		];
		const workspaceContext = {
			company: workspace.selectedCompany
				? {
					stockCode: workspace.selectedCompany.stockCode,
					corpName: workspace.selectedCompany.corpName,
					company: workspace.selectedCompany.company,
				}
				: companyHint ? { stockCode: companyHint } : null,
			selectedModules,
		};
		// Phase 8 — dashboard 에서 첨부한 화면 snapshot 을 함께 전송 (있을 때만).
		if (dashboard.pendingSnapshot) {
			workspaceContext.dashboardSnapshot = dashboard.pendingSnapshot;
			// 한 번 보내고 제거 — 사용자가 의도적으로 두 번째 질문 시 다시 첨부.
			dashboard.clearPendingSnapshot();
		}

		const updateAgentMessage = (updater) => {
			if (store.activeId !== streamConvId) return;
			const active = store.active;
			const last = active?.messages?.[active.messages.length - 1];
			if (!last || last.role !== "assistant") return;
			store.updateLastMessage(updater(last));
		};
		const handleStreamSettled = () => {
			isLoading = false;
			currentStream = null;
			updateAgentMessage(() => ({ loading: false, endedAt: Date.now() }));
		};
		const callbacks = {
			onTextDelta: (payload) => {
				const delta = payload?.delta || "";
				if (!delta) return;
				updateAgentMessage((last) => {
					const text = `${last.text || last.content || ""}${delta}`;
					return {
						text,
						content: text,
						parts: appendTextPart(last, delta),
					};
				});
			},
			onActivity: (payload) => {
				updateAgentMessage((last) => ({
					parts: appendActivityPart(last, payload || {}),
				}));
			},
			onToolStart: (payload) => {
				updateAgentMessage((last) => ({
					parts: upsertToolPart(last, { ...payload, status: "running" }),
				}));
			},
			onToolResult: (payload) => {
				updateAgentMessage((last) => ({
					parts: upsertToolPart(last, { ...payload, status: payload?.status || "done" }),
				}));
			},
			onViewSpec: (payload) => {
				updateAgentMessage((last) => ({
					parts: appendViewSpecPart(last, payload || {}),
				}));
			},
			onDone: (payload) => {
				updateAgentMessage(() => ({
					loading: false,
					error: payload?.status === "failed",
					refs: payload?.refs || [],
					artifacts: payload?.artifacts || [],
					agentMeta: payload?.responseMeta || {},
					suggestedQuestions: Array.isArray(payload?.suggestedQuestions)
						? payload.suggestedQuestions
						: [],
				}));
				handleStreamSettled();
			},
			onError: (payload) => {
				const message = payload?.message || "최종 답변을 생성하지 못했습니다.";
				updateAgentMessage((last) => ({
					loading: false,
					error: true,
					text: last.text || message,
					content: last.content || message,
					parts: appendFailurePart(last, { message }),
				}));
				handleStreamSettled();
			},
			onState: (payload) => {
				updateAgentMessage((last) => ({
					agentState: { ...(last.agentState || {}), ...(payload || {}) },
				}));
			},
		};

		const stream = runAgentStream({
			threadId: streamConvId,
			messages: agentMessages,
			provider: chatProvider.provider,
			role: ui.CHAT_ROLE,
			model: chatProvider.model,
			workspaceContext,
		}, callbacks);
		currentStream = stream;
	}

	function stopStream() {
		if (currentStream) {
			currentStream.abort();
			currentStream = null;
			isLoading = false;
			store.updateLastMessage({ loading: false });
			store.flush();
		}
	}

	function handleEditResend(newText) {
		if (!newText || isLoading) return;
		sendMessage(newText);
	}

	function handleRegenerate() {
		const conv = store.active;
		if (!conv || conv.messages.length < 2) return;
		let lastUserMsg = "";
		for (let i = conv.messages.length - 1; i >= 0; i--) {
			if (conv.messages[i].role === "user") { lastUserMsg = conv.messages[i].text; break; }
		}
		if (!lastUserMsg) return;
		store.removeLastMessage();
		store.removeLastMessage();
		inputText = lastUserMsg;
		requestAnimationFrame(() => { sendMessage(); });
	}

	function handleExport() {
		const conv = store.active;
		if (!conv) return;
		let md = `# ${conv.title}\n\n`;
		for (const msg of conv.messages) {
			if (msg.role === "user") md += `## You\n\n${msg.text}\n\n`;
			else if (msg.role === "assistant" && msg.text) md += `## DartLab\n\n${msg.text}\n\n`;
		}
		const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = `${conv.title || "dartlab-chat"}.md`;
		a.click();
		URL.revokeObjectURL(url);
		ui.showToast("대화가 마크다운으로 내보내졌습니다", "success");
	}

	function handleOpenEvidence(section, index = null) {
		workspace.openEvidence(section, index);
	}

	function handleCompanySelectForChat(company) {
		workspace.selectCompany(company);
		workspace.switchView("chat");
	}

	function handleCompanySelectForViewer(company) {
		workspace.openViewer(company);
	}

	// ── Keyboard shortcuts ──
	function handleGlobalKeydown(e) {
		if ((e.metaKey || e.ctrlKey) && e.key === 'n') { e.preventDefault(); handleNewChat(); }
		if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'S') { e.preventDefault(); ui.toggleSidebar(); }
		if (e.key === 'Escape' && ui.settingsOpen) { ui.settingsOpen = false; }
		else if (e.key === 'Escape' && ui.deleteConfirmId) { ui.deleteConfirmId = null; }
	}
</script>

<svelte:window onkeydown={handleGlobalKeydown} />

<div class="flex h-screen bg-dl-bg-dark overflow-hidden">
	<!-- Sidebar (브라우저에서만 — VSCode는 확장 사이드바 사용) -->
	{#if !isVSCode}
		{#if ui.isMobile && ui.sidebarOpen}
			<button class="sidebar-overlay" onclick={() => { ui.sidebarOpen = false; }} aria-label="사이드바 닫기"></button>
		{/if}
		<div class={ui.isMobile ? (ui.sidebarOpen ? "sidebar-mobile" : "hidden") : ""}>
			<Sidebar
				conversations={store.conversations}
				activeId={store.activeId}
				open={ui.isMobile ? true : ui.sidebarOpen}
				width={sidebarWidth}
				version={ui.appVersion}
				onNewChat={() => { handleNewChat(); if (ui.isMobile) ui.sidebarOpen = false; }}
				onSelect={(id) => { handleSelectConversation(id); if (ui.isMobile) ui.sidebarOpen = false; }}
				onDelete={handleDeleteConversation}
				onDeleteAll={handleDeleteAllConversations}
				onRename={(id, title) => { if (title) store.updateTitle(id, title); }}
				onTogglePin={(id) => store.togglePin?.(id)}
				onDuplicate={(id) => { const newId = store.duplicateConversation?.(id); if (newId) handleSelectConversation(newId); }}
				onOpenSettings={() => { showSettings = true; if (ui.isMobile) ui.sidebarOpen = false; }}
			/>
			{#if !ui.isMobile && ui.sidebarOpen}
				<PanelResizer onResize={handleSidebarResize} />
			{/if}
		</div>
	{/if}

	<!-- Main -->
	<div class="relative flex flex-col flex-1 min-w-0 min-h-0 glow-bg">
		<!-- Top-left: sidebar toggle (Ask 모드만 — Dashboard 는 자체 TopBar 가짐) -->
		{#if !isVSCode && uiMode.value !== "dashboard"}
			<div class="absolute top-2 left-3 z-20 pointer-events-auto flex items-center gap-1">
				<button
					class="p-1.5 rounded-lg text-dl-text-muted hover:text-dl-text hover:bg-white/5 transition-colors"
					onclick={() => ui.toggleSidebar()}
				>
					{#if ui.sidebarOpen}
						<PanelLeftClose size={18} />
					{:else}
						<Menu size={18} />
					{/if}
				</button>
			</div>
		{/if}

		<!-- Top-right controls -->
		<div class="absolute top-2 right-3 z-20 flex items-center gap-1 pointer-events-auto">
			{#if !isVSCode}
				<SocialIcons />
			{/if}
			{#if uiMode.value !== "dashboard"}
				<ProviderDropdown {ui} onOpenSettings={(section) => ui.openSettings(section)} />
			{/if}
		</div>

		<!-- Content: Ask 모드 ⇄ Dashboard 모드 -->
		<div class="flex flex-1 min-h-0">
			<div class="min-w-0 flex-1 flex flex-col">
				{#if uiMode.value === "dashboard"}
					<DashboardShell />
				{:else if hasConversation}
					<SnapshotChip />
					<ChatArea
						messages={activeMessages}
						{isLoading}
						bind:inputText
						selectedCompany={workspace.selectedCompany}
						suggestions={suggestedQuestions}
						dataReady={onboardingDataReady}
						suggestionLoading={suggestionLoading}
						providerLabel={ui.providers[ui.activeProvider]?.label || ui.activeProvider || null}
						modelLabel={ui.activeModel || null}
						onSend={sendMessage}
						onStop={stopStream}
						onRegenerate={handleRegenerate}
						onExport={handleExport}
						onEditResend={handleEditResend}
						onCompanySelect={handleCompanySelectForChat}
						onOpenEvidence={handleOpenEvidence}
						{watchlist}
						onAddWatch={addToWatchlist}
						onRemoveWatch={removeFromWatchlist}
						onCommand={handleSlashCommand}
						bind:selectedModules
					/>
				{:else}
					<SnapshotChip />
					<EmptyState
						bind:inputText
						onSend={sendMessage}
						onCompanySelect={handleCompanySelectForChat}
						onCommand={handleSlashCommand}
						dataReady={onboardingDataReady}
					/>
				{/if}
			</div>
		</div>
	</div>

	<!-- 모바일 하단 탭 바 (화면 하단 고정) -->
	{#if ui.isMobile && !isVSCode}
		<nav class="fixed bottom-0 left-0 right-0 z-30 flex items-center justify-around h-12 border-t border-dl-border/30 bg-dl-bg-darker/95 backdrop-blur-sm safe-area-bottom" aria-label="메인 탐색">
			<button
				class="flex flex-col items-center gap-0.5 flex-1 py-1.5 transition-colors text-dl-text-dim"
				onclick={() => ui.toggleSidebar()}
			>
				<Menu size={18} />
				<span class="text-[9px] font-medium">대화</span>
			</button>
			<button
				class="flex flex-col items-center gap-0.5 flex-1 py-1.5 transition-colors text-dl-text-dim"
				onclick={() => ui.openSettings()}
			>
				<Cog size={18} />
				<span class="text-[9px] font-medium">설정</span>
			</button>
		</nav>
	{/if}
</div>

<!-- Modals -->
{#if ui.settingsOpen}
	{#await import("$lib/components/SettingsPanel.svelte") then { default: SettingsPanel }}
		<SettingsPanel {ui} />
	{/await}
{/if}
<DeleteDialog {ui} onConfirm={confirmDelete} />
<ToastNotification {ui} />
