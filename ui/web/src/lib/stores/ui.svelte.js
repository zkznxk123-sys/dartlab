/**
 * 중앙 UI 상태 관리 — layout, modals, toast, provider 상태를 한 곳에서 관리.
 *
 * AI가 ui_action 이벤트로 레이아웃/뷰를 제어하기 위한 단일 진입점 역할.
 * App.svelte의 55+ 산발 상태변수를 이 store로 통합한다.
 */
import {
	fetchAiProfile,
	fetchModels,
	fetchStatus,
	subscribeAiProfileEvents,
	deleteDartKey,
	updateAiProfile,
	updateAiSecret,
	saveDartKey,
	validateProvider as validateProviderApi,
	validateDartKey as validateDartKeyApi,
	codexLogout,
	oauthAuthorize,
	oauthLogout,
	oauthStatus,
	pullOllamaModel,
	fetchDevChannelStatus,
	startDevChannel as startDevChannelApi,
	stopDevChannel as stopDevChannelApi,
} from "$lib/api/ai.js";
import {
	applyProfileSnapshot,
	mergeProviderDetail,
	mergeProviderStatus,
	normalizeProvider,
} from "$lib/ai/providerProfile.js";

const CHAT_ROLE = "analysis";

const OLLAMA_MODELS = [
	{ name: "gemma3",       size: "3B",  gb: "2.3",  desc: "Google, 빠르고 가벼움",         tag: "추천" },
	{ name: "gemma3:12b",   size: "12B", gb: "8.1",  desc: "Google, 균형잡힌 성능" },
	{ name: "llama3.1",     size: "8B",  gb: "4.7",  desc: "Meta, 범용 최강",              tag: "추천" },
	{ name: "qwen2.5",      size: "7B",  gb: "4.7",  desc: "Alibaba, 한국어 우수" },
	{ name: "qwen2.5:14b",  size: "14B", gb: "9.0",  desc: "Alibaba, 한국어 최고 수준" },
	{ name: "deepseek-r1",  size: "7B",  gb: "4.7",  desc: "추론 특화, 분석에 적합" },
	{ name: "phi4",         size: "14B", gb: "9.1",  desc: "Microsoft, 수학/코드 강점" },
	{ name: "mistral",      size: "7B",  gb: "4.1",  desc: "Mistral AI, 가볍고 빠름" },
	{ name: "exaone3.5",    size: "8B",  gb: "4.9",  desc: "LG AI, 한국어 특화",           tag: "한국어" },
];

export function createUiStore() {
	// ── Layout ──
	// 데스크톱은 default 열림 (외부 챗 표면 표준). 모바일은 effect 에서 false 강제.
	let sidebarOpen = $state(typeof window !== "undefined" && window.innerWidth >= 768);
	let viewerFullscreen = $state(false);
	let isMobile = $state(false);

	// ── Toast Queue ──
	let toastQueue = $state([]);
	let toastIdCounter = 0;

	function showToast(msg, type = "error", duration = 4000) {
		const id = ++toastIdCounter;
		const timer = setTimeout(() => dismissToast(id), duration);
		const entry = { id, message: msg, type, duration, timer };
		// max 5 toasts
		if (toastQueue.length >= 5) {
			const oldest = toastQueue[0];
			clearTimeout(oldest.timer);
			toastQueue = [...toastQueue.slice(1), entry];
		} else {
			toastQueue = [...toastQueue, entry];
		}
	}

	function dismissToast(id) {
		const idx = toastQueue.findIndex(t => t.id === id);
		if (idx >= 0) {
			clearTimeout(toastQueue[idx].timer);
			toastQueue = [...toastQueue.slice(0, idx), ...toastQueue.slice(idx + 1)];
		}
	}

	// ── Modals ──
	let settingsOpen = $state(false);
	let settingsSection = $state("providers");
	let deleteConfirmId = $state(null);
	let deleteConfirmMode = $state("single");

	// ── Provider / Model ──
	// 핵심 원칙: 스피너에 직접 영향을 주는 상태는 단일 $state 객체로 묶는다.
	// 개별 let + getter 노출 패턴이 일부 모바일 브라우저에서 reactivity가 끊기는 사례가
	// 보고되어 proxy 객체 방식이 가장 안전하다.
	const _core = $state({
		statusLoading: true,
		providers: {},
		activeProvider: null,
		activeModel: null,
		availableModels: [],
		expandedProvider: null,
	});
	let providerModels = $state({});
	let modelsLoading = $state({});
	let appVersion = $state("");
	let openDart = $state({});
	let channels = $state({});
	let channel = $state({ kind: "devtunnel", running: false, url: null, qrDataUrl: null, error: null });

	// API key
	let apiKeyInput = $state("");
	let apiKeyVerifying = $state(false);
	let apiKeyResult = $state(null);

	// OpenDART key
	let dartKeyInput = $state("");
	let dartKeyValidating = $state(false);
	let dartKeySaving = $state(false);
	let dartKeyResult = $state(null);

	// Ollama detail
	let ollamaDetail = $state({});
	let codexDetail = $state({});
	let oauthCodexDetail = $state({});
	let oauthLoginPending = $state(false);
	let channelBusy = $state(false);

	// Ollama pull
	let pullModelName = $state("");
	let isPulling = $state(false);
	let pullProgress = $state("");
	let pullPercent = $state(0);
	let pullHandle = $state(null);

	// SSE subscription
	let profileEvents = null;

	// ── Provider logic ──
	function providerSupportsRole(provider, role) {
		const normalized = normalizeProvider(provider);
		const supportedRoles = _core.providers[normalized]?.supportedRoles;
		return !Array.isArray(supportedRoles) || supportedRoles.length === 0 || supportedRoles.includes(role);
	}

	async function validateProvider(provider, model = null, apiKey = null) {
		const result = await validateProviderApi(provider, model, apiKey);
		if (result?.provider) {
			const name = normalizeProvider(result.provider);
			_core.providers = {
				..._core.providers,
				[name]: {
					...(_core.providers[name] || {}),
					checked: true,
					available: !!result.available,
					model: result.model || _core.providers[name]?.model || model || null,
				},
			};
		}
		return result;
	}

	async function refreshProviderStatus(provider = null, probe = true) {
		const data = await fetchStatus(provider, probe);
		if (data.profile) _core.providers = applyProfileSnapshot(_core.providers, data.profile);
		_core.providers = mergeProviderStatus(_core.providers, data.providers || {});
		if (data.ollama) ollamaDetail = mergeProviderDetail(ollamaDetail, data.ollama, { preserveChecked: true });
		if (data.codex) codexDetail = mergeProviderDetail(codexDetail, data.codex);
		if (data.oauthCodex) oauthCodexDetail = mergeProviderDetail(oauthCodexDetail, data.oauthCodex, { preserveChecked: true });
		if (data.openDart) openDart = { ...openDart, ...data.openDart };
		if (data.channels) channels = data.channels;
		if (data.channel) channel = data.channel;
		if (data.version) appVersion = data.version;
		return data;
	}

	async function handleProfileChanged(profile) {
		_core.providers = applyProfileSnapshot(_core.providers, profile);
		const nextProvider = normalizeProvider(profile?.defaultProvider || _core.activeProvider || "codex");
		_core.activeProvider = nextProvider;
		_core.expandedProvider = nextProvider;
		apiKeyInput = "";
		apiKeyResult = null;
		await loadModelsFor(nextProvider);
		_core.availableModels = providerModels[nextProvider] || [];
		const nextModel = profile?.providers?.[nextProvider]?.model || _core.providers[nextProvider]?.model || _core.availableModels[0] || null;
		_core.activeModel = nextModel;
		if (nextModel && !profile?.providers?.[nextProvider]?.model) {
			try { await updateAiProfile({ provider: nextProvider, model: nextModel }); } catch {}
		}
		await refreshProviderStatus(nextProvider, true);
	}

	async function loadStatus() {
		_core.statusLoading = true;
		// 핵심 원칙: statusLoading은 "프로바이더 목록이 있는가"만 의미한다.
		// /api/status 응답 오는 순간 풀리고, 나머지(모델 로드/검증/SSE)는 백그라운드.
		// 첫 호출은 probe=false — 모든 provider 직렬 점검 회피해 화면 로드를 빠르게.
		// 활성 provider availability 는 아래 백그라운드 validateProvider 가 단독 검증.
		// 사용자가 설정 패널을 열면 selectProvider/openSettings 경로에서 probe=true 가 동작.
		let profile = null;
		try {
			profile = await fetchAiProfile();
			_core.providers = applyProfileSnapshot(_core.providers, profile);
		} catch (e) {
			console.warn("[loadStatus] fetchAiProfile:", e);
		}
		const preferredProvider = normalizeProvider(profile?.defaultProvider || "codex");
		try {
			await refreshProviderStatus(preferredProvider, false);
		} catch (e) {
			console.warn("[loadStatus] refreshProviderStatus:", e);
		}
		_core.activeProvider = preferredProvider;
		_core.expandedProvider = preferredProvider;
		apiKeyInput = "";
		_core.statusLoading = false;

		// 이하 백그라운드: 실패해도 UI는 동작 (모델 선택/SSE는 사용자가 설정 패널 열 때 다시 시도)
		(async () => {
			try { await loadModelsFor(preferredProvider); } catch (e) { console.warn("[loadStatus.bg] loadModelsFor:", e); }
			const models = providerModels[preferredProvider] || [];
			_core.availableModels = models;
			const savedModel = profile?.providers?.[preferredProvider]?.model || _core.providers[preferredProvider]?.model || null;
			if (savedModel && (models.length === 0 || models.includes(savedModel))) {
				_core.activeModel = savedModel;
			} else if (models.length > 0) {
				_core.activeModel = models[0];
				try { await updateAiProfile({ provider: preferredProvider, model: _core.activeModel }); } catch (e) { console.warn("[loadStatus.bg] updateAiProfile:", e); }
			} else {
				_core.activeModel = null;
			}
			if (!_core.providers[preferredProvider]?.checked || _core.providers[preferredProvider]?.available !== true) {
				try { await validateProvider(preferredProvider, _core.activeModel || null, null); } catch (e) { console.warn("[loadStatus.bg] validateProvider:", e); }
			}
			if (!profileEvents) {
				try {
					profileEvents = subscribeAiProfileEvents({
						onProfileChanged(profilePayload) {
							handleProfileChanged(profilePayload).catch((e) => console.warn("profile_changed:", e));
						},
						onError(err) { console.warn("profile events:", err); },
					});
				} catch (e) {
					console.warn("[loadStatus.bg] subscribeAiProfileEvents:", e);
				}
			}
		})();
	}

	function cleanupProfileEvents() {
		if (profileEvents) {
			profileEvents.close?.();
			profileEvents = null;
		}
	}

	async function loadModelsFor(provider) {
		provider = normalizeProvider(provider);
		modelsLoading = { ...modelsLoading, [provider]: true };
		try {
			const data = await fetchModels(provider);
			providerModels = { ...providerModels, [provider]: data.models || [] };
		} catch (e) {
			console.warn("loadModelsFor:", e);
			providerModels = { ...providerModels, [provider]: [] };
		}
		modelsLoading = { ...modelsLoading, [provider]: false };
	}

	async function selectProvider(name) {
		name = normalizeProvider(name);
		_core.activeProvider = name;
		_core.activeModel = null;
		_core.expandedProvider = name;
		apiKeyInput = "";
		apiKeyResult = null;
		await updateAiProfile({ provider: name });
		await refreshProviderStatus(name, true);
		await loadModelsFor(name);
		const models = providerModels[name] || [];
		_core.availableModels = models;
		const savedModel = _core.providers[name]?.model || null;
		if (savedModel && (models.length === 0 || models.includes(savedModel))) {
			_core.activeModel = savedModel;
		} else if (models.length > 0) {
			_core.activeModel = models[0];
			await updateAiProfile({ provider: name, model: _core.activeModel });
		}
		if (!providerSupportsRole(name, CHAT_ROLE)) {
			showToast("Codex CLI는 코드 작업용입니다. GUI 대화/분석은 `GPT (ChatGPT 구독 계정)`을 권장합니다.", "error", 4500);
		}
		try { await validateProvider(name, _core.activeModel, null); } catch {}
	}

	async function selectModel(model) {
		_core.activeModel = model;
		await updateAiProfile({ provider: normalizeProvider(_core.activeProvider), model });
		const configured = _core.providers[_core.activeProvider]?.secretConfigured;
		if (configured || _core.activeProvider === "codex" || _core.activeProvider === "oauth-codex" || _core.activeProvider === "ollama") {
			try { await validateProvider(normalizeProvider(_core.activeProvider), model, null); } catch {}
		}
	}

	function toggleExpandProvider(name) {
		name = normalizeProvider(name);
		if (_core.expandedProvider === name) {
			_core.expandedProvider = null;
		} else {
			_core.expandedProvider = name;
			loadModelsFor(name);
		}
	}

	async function submitApiKey() {
		const key = apiKeyInput.trim();
		if (!key || !_core.activeProvider) return;
		apiKeyVerifying = true;
		apiKeyResult = null;
		try {
			const result = await validateProvider(normalizeProvider(_core.activeProvider), _core.activeModel, key);
			if (result.available) {
				await updateAiSecret(_core.activeProvider, key, false);
				apiKeyResult = "success";
				if (!_core.activeModel && result.model) {
					_core.activeModel = result.model;
					await updateAiProfile({ provider: _core.activeProvider, model: _core.activeModel });
				}
				await loadModelsFor(_core.activeProvider);
				_core.availableModels = providerModels[_core.activeProvider] || [];
				apiKeyInput = "";
				showToast("API 키 인증 성공", "success");
			} else {
				apiKeyResult = "error";
			}
		} catch {
			apiKeyResult = "error";
		}
		apiKeyVerifying = false;
	}

	async function handleCodexLogout() {
		try {
			await codexLogout();
			if (_core.activeProvider === "codex") {
				_core.providers = { ..._core.providers, codex: { ..._core.providers.codex, available: false } };
			}
			showToast("Codex 계정 로그아웃 완료", "success");
			await loadStatus();
		} catch {
			showToast("로그아웃 실패");
		}
	}

	async function handleOauthCodexLogin() {
		if (oauthLoginPending) return;
		oauthLoginPending = true;
		try {
			const { authUrl } = await oauthAuthorize();
			window.open(authUrl, "dartlab-oauth-codex", "popup=yes,width=540,height=760");
			const started = Date.now();
			while (Date.now() - started < 120000) {
				await new Promise((resolve) => setTimeout(resolve, 1000));
				const status = await oauthStatus();
				if (!status.done) continue;
				if (status.error) throw new Error(status.error);
				await refreshProviderStatus("oauth-codex", true);
				const profile = await fetchAiProfile();
				await handleProfileChanged(profile);
				showToast("ChatGPT OAuth 인증 완료", "success");
				oauthLoginPending = false;
				return;
			}
			throw new Error("oauth_timeout");
		} catch (e) {
			const message = e?.message === "oauth_timeout" ? "OAuth 인증 시간이 초과되었습니다" : `OAuth 인증 실패: ${e?.message || "unknown"}`;
			showToast(message);
		}
		oauthLoginPending = false;
	}

	async function handleOauthCodexLogout() {
		try {
			await oauthLogout();
			oauthCodexDetail = { ...oauthCodexDetail, authenticated: false, checked: true };
			const profile = await fetchAiProfile();
			await handleProfileChanged(profile);
			showToast("ChatGPT OAuth 로그아웃 완료", "success");
		} catch {
			showToast("OAuth 로그아웃 실패");
		}
	}

	// ── Ollama pull ──
	function startPullModel() {
		const name = pullModelName.trim();
		if (!name || isPulling) return;
		isPulling = true;
		pullProgress = "준비 중...";
		pullPercent = 0;
		pullHandle = pullOllamaModel(name, {
			onProgress(data) {
				if (data.total && data.completed !== undefined) {
					pullPercent = Math.round((data.completed / data.total) * 100);
					pullProgress = `다운로드 중... ${pullPercent}%`;
				} else if (data.status) {
					pullProgress = data.status;
				}
			},
			async onDone() {
				isPulling = false;
				pullHandle = null;
				pullModelName = "";
				pullProgress = "";
				pullPercent = 0;
				showToast(`${name} 다운로드 완료`, "success");
				await loadModelsFor("ollama");
				_core.availableModels = providerModels["ollama"] || [];
				if (_core.availableModels.includes(name)) {
					await selectModel(name);
				}
			},
			onError(err) {
				isPulling = false;
				pullHandle = null;
				pullProgress = "";
				pullPercent = 0;
				showToast(`다운로드 실패: ${err}`);
			},
		});
	}

	function cancelPull() {
		if (pullHandle) { pullHandle.abort(); pullHandle = null; }
		isPulling = false;
		pullModelName = "";
		pullProgress = "";
		pullPercent = 0;
	}

	// ── Chat provider resolution ──
	async function resolveChatProvider() {
		const normalized = normalizeProvider(_core.activeProvider);
		if (!normalized) return null;
		if (providerSupportsRole(normalized, CHAT_ROLE)) {
			return { provider: normalized, model: _core.activeModel };
		}
		if (!_core.providers["oauth-codex"]?.available) {
			showToast("Codex CLI는 GUI 일반 대화용이 아니라 코딩용입니다. 설정에서 `GPT (ChatGPT 구독 계정)` 또는 다른 분석용 provider를 선택하세요.");
			return null;
		}
		await loadModelsFor("oauth-codex");
		const models = providerModels["oauth-codex"] || [];
		const nextModel = _core.activeModel && (models.length === 0 || models.includes(_core.activeModel))
			? _core.activeModel
			: _core.providers["oauth-codex"]?.model || models[0] || null;
		_core.activeProvider = "oauth-codex";
		_core.expandedProvider = "oauth-codex";
		_core.availableModels = models;
		_core.activeModel = nextModel;
		try {
			if (nextModel) await updateAiProfile({ provider: "oauth-codex", model: nextModel });
			else await updateAiProfile({ provider: "oauth-codex" });
		} catch {}
		showToast("Codex CLI는 GUI 일반 대화용이 아니라 코딩용입니다. GPT OAuth provider로 전환해서 보냅니다.", "success", 4500);
		return { provider: "oauth-codex", model: nextModel };
	}

	// ── Theme ──
	let theme = $state(
		(typeof localStorage !== "undefined" && localStorage.getItem("dl-theme")) || "dark"
	);

	function setTheme(value) {
		theme = value;
		if (typeof document !== "undefined") {
			document.documentElement.setAttribute("data-theme", value);
		}
		if (typeof localStorage !== "undefined") {
			localStorage.setItem("dl-theme", value);
		}
	}

	function cycleTheme() {
		const order = ["dark", "light", "auto"];
		const next = order[(order.indexOf(theme) + 1) % order.length];
		setTheme(next);
	}

	// Apply saved theme on creation
	if (typeof document !== "undefined") {
		document.documentElement.setAttribute("data-theme", theme);
	}

	// ── Mobile detection ──
	function checkMobile() {
		isMobile = window.innerWidth <= 768;
		if (isMobile) sidebarOpen = false;
	}

	// ── Settings open ──
	function openSettings(section = "providers") {
		apiKeyInput = "";
		apiKeyResult = null;
		dartKeyInput = "";
		dartKeyResult = null;
		settingsSection = section || "providers";
		if (_core.activeProvider) {
			_core.expandedProvider = _core.activeProvider;
		} else {
			const names = Object.keys(_core.providers);
			_core.expandedProvider = names.length > 0 ? names[0] : null;
		}
		settingsOpen = true;
		if (_core.expandedProvider) loadModelsFor(_core.expandedProvider);
		if (settingsSection === "channels") refreshDevChannel();
	}

	async function refreshDevChannel() {
		try {
			channel = await fetchDevChannelStatus();
		} catch (e) {
			channel = { ...channel, error: e?.message || "Channel 상태 확인 실패" };
		}
	}

	async function startDevChannel() {
		if (channelBusy) return;
		channelBusy = true;
		try {
			channel = await startDevChannelApi();
			if (channel?.error) showToast(channel.error);
			else showToast("모바일 Channel QR을 준비했습니다", "success");
		} catch (e) {
			showToast(e?.message || "Channel 시작 실패");
		}
		channelBusy = false;
	}

	async function stopDevChannel() {
		if (channelBusy) return;
		channelBusy = true;
		try {
			channel = await stopDevChannelApi();
			showToast("Channel을 종료했습니다", "success");
		} catch (e) {
			showToast(e?.message || "Channel 종료 실패");
		}
		channelBusy = false;
	}

	async function validateDartKey() {
		const key = dartKeyInput.trim();
		if (!key) return;
		dartKeyValidating = true;
		dartKeyResult = null;
		try {
			const result = await validateDartKeyApi(key);
			if (result.openDart) openDart = { ...openDart, ...result.openDart };
			dartKeyResult = "valid";
			showToast("OpenDART 키 검증 성공", "success");
		} catch (e) {
			dartKeyResult = "error";
			showToast(e?.message || "OpenDART 키 검증 실패");
		}
		dartKeyValidating = false;
	}

	async function submitDartKey() {
		const key = dartKeyInput.trim();
		if (!key) return;
		dartKeySaving = true;
		dartKeyResult = null;
		try {
			const result = await saveDartKey(key);
			if (result.openDart) openDart = { ...openDart, ...result.openDart };
			dartKeyInput = "";
			dartKeyResult = "saved";
			showToast("OpenDART 키 저장 완료", "success");
		} catch (e) {
			dartKeyResult = "error";
			showToast(e?.message || "OpenDART 키 저장 실패");
		}
		dartKeySaving = false;
	}

	async function removeDartKey() {
		dartKeySaving = true;
		dartKeyResult = null;
		try {
			const result = await deleteDartKey();
			if (result.openDart) openDart = { ...openDart, ...result.openDart };
			dartKeyInput = "";
			dartKeyResult = "deleted";
			showToast("프로젝트 .env의 OpenDART 키를 제거했습니다", "success");
		} catch (e) {
			dartKeyResult = "error";
			showToast(e?.message || "OpenDART 키 삭제 실패");
		}
		dartKeySaving = false;
	}

	// ── AI action entry point ──
	function applyAiAction(action) {
		if (!action || typeof action !== "object") return;
		const name = action.action || "";
		if (name === "layout") {
			const target = action.target;
			const value = action.value;
			if (target === "sidebar") {
				sidebarOpen = value === "toggle" ? !sidebarOpen : value === "open";
			} else if (target === "fullscreen") {
				viewerFullscreen = typeof value === "boolean" ? value : !viewerFullscreen;
			}
		} else if (name === "toast") {
			showToast(action.message || action.text || "", action.level || "info");
		} else if (name === "update" && action.target === "settings") {
			if (action.message) showToast(action.message, "info", 4500);
			openSettings(action.section || "providers");
			if (action.open === false) settingsOpen = false;
		}
	}

	return {
		// layout
		get sidebarOpen() { return sidebarOpen; },
		set sidebarOpen(v) { sidebarOpen = v; },
		get viewerFullscreen() { return viewerFullscreen; },
		set viewerFullscreen(v) { viewerFullscreen = v; },
		get isMobile() { return isMobile; },
		toggleSidebar() { sidebarOpen = !sidebarOpen; },
		checkMobile,

		// toast
		get toastQueue() { return toastQueue; },
		get toastMessage() { return toastQueue.length > 0 ? toastQueue[toastQueue.length - 1].message : ""; },
		get toastType() { return toastQueue.length > 0 ? toastQueue[toastQueue.length - 1].type : "error"; },
		get toastVisible() { return toastQueue.length > 0; },
		get toastDuration() { return toastQueue.length > 0 ? toastQueue[toastQueue.length - 1].duration : 4000; },
		showToast,
		dismissToast,

		// modals
		get settingsOpen() { return settingsOpen; },
		set settingsOpen(v) { settingsOpen = v; },
		get settingsSection() { return settingsSection; },
		set settingsSection(v) { settingsSection = v; },
		get deleteConfirmId() { return deleteConfirmId; },
		set deleteConfirmId(v) { deleteConfirmId = v; },
		get deleteConfirmMode() { return deleteConfirmMode; },
		set deleteConfirmMode(v) { deleteConfirmMode = v; },
		openSettings,

		// provider
		get providers() { return _core.providers; },
		get activeProvider() { return _core.activeProvider; },
		get activeModel() { return _core.activeModel; },
		get availableModels() { return _core.availableModels; },
		get expandedProvider() { return _core.expandedProvider; },
		get providerModels() { return providerModels; },
		get modelsLoading() { return modelsLoading; },
		get statusLoading() { return _core.statusLoading; },
		get appVersion() { return appVersion; },
		get openDart() { return openDart; },
		get channels() { return channels; },
		get channel() { return channel; },
		get channelBusy() { return channelBusy; },

		// api key
		get apiKeyInput() { return apiKeyInput; },
		set apiKeyInput(v) { apiKeyInput = v; },
		get apiKeyVerifying() { return apiKeyVerifying; },
		get apiKeyResult() { return apiKeyResult; },

		// OpenDART key
		get dartKeyInput() { return dartKeyInput; },
		set dartKeyInput(v) { dartKeyInput = v; },
		get dartKeyValidating() { return dartKeyValidating; },
		get dartKeySaving() { return dartKeySaving; },
		get dartKeyResult() { return dartKeyResult; },

		// detail
		get ollamaDetail() { return ollamaDetail; },
		get codexDetail() { return codexDetail; },
		get oauthCodexDetail() { return oauthCodexDetail; },
		get oauthLoginPending() { return oauthLoginPending; },

		// pull
		get pullModelName() { return pullModelName; },
		set pullModelName(v) { pullModelName = v; },
		get isPulling() { return isPulling; },
		get pullProgress() { return pullProgress; },
		get pullPercent() { return pullPercent; },

		// provider methods
		selectProvider,
		selectModel,
		toggleExpandProvider,
		submitApiKey,
		validateDartKey,
		submitDartKey,
		removeDartKey,
		refreshDevChannel,
		startDevChannel,
		stopDevChannel,
		handleCodexLogout,
		handleOauthCodexLogin,
		handleOauthCodexLogout,
		startPullModel,
		cancelPull,
		loadStatus,
		loadModelsFor,
		providerSupportsRole,
		resolveChatProvider,
		cleanupProfileEvents,

		// constants
		CHAT_ROLE,
		OLLAMA_MODELS,

		// theme
		get theme() { return theme; },
		setTheme,
		cycleTheme,

		// AI action
		applyAiAction,
	};
}

// 모듈 싱글톤 — props 전달 시 reactive 추적이 끊기는 문제를 우회하기 위해
// 모든 컴포넌트가 같은 인스턴스를 직접 import할 수 있게 노출.
let _singleton = null;
let _autoLoadStarted = false;
export function getUiStore() {
	if (!_singleton) {
		_singleton = createUiStore();
	}
	// 첫 호출 시 자동으로 loadStatus 실행 — onMount/$effect 발화에 의존하지 않음.
	// 일부 모바일 브라우저에서 lifecycle hook 미발화 케이스를 우회.
	if (!_autoLoadStarted) {
		_autoLoadStarted = true;
		try {
			// 비동기지만 await 안 함 — 호출 직후 store 반환
			_singleton.loadStatus();
		} catch (_) {}
	}
	return _singleton;
}
