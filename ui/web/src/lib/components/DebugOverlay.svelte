<script>
	/**
	 * 모바일 진단 오버레이 — 화면 우하단 고정.
	 * URL ?debug=1 일 때만 마운트된다.
	 */
	import { getLogs, disableDebug } from "../debug.js";
	import { getToken, getTokenSource } from "../api/token.js";

	let { ui } = $props();
	let logs = $state([]);
	let collapsed = $state(false);
	let buildId = $state("");

	// __BUILD_ID__는 vite.config.js의 define에서 주입
	try { buildId = typeof __BUILD_ID__ !== "undefined" ? __BUILD_ID__ : "(dev)"; } catch { buildId = "(?)"; }

	// 1초마다 logs 폴링
	$effect(() => {
		const t = setInterval(() => { logs = getLogs(); }, 1000);
		return () => clearInterval(t);
	});

	function close() {
		disableDebug();
		const el = document.getElementById("dartlab-debug-overlay");
		if (el) el.remove();
	}
</script>

<div
	id="dartlab-debug-overlay"
	style="
		position: fixed;
		right: 8px;
		bottom: 8px;
		max-width: min(360px, 90vw);
		max-height: 60vh;
		overflow: auto;
		background: rgba(0,0,0,0.85);
		color: #0f0;
		font-family: 'SF Mono', Menlo, Consolas, monospace;
		font-size: 11px;
		line-height: 1.4;
		padding: 8px 10px;
		border: 1px solid #0f0;
		border-radius: 6px;
		z-index: 999999;
		pointer-events: auto;
	"
>
	<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
		<strong>dartlab debug</strong>
		<div>
			<button
				type="button"
				onclick={() => (collapsed = !collapsed)}
				style="background: transparent; color: #0f0; border: 1px solid #0f0; padding: 0 6px; margin-right: 4px; font-size: 10px;"
			>{collapsed ? "+" : "-"}</button>
			<button
				type="button"
				onclick={close}
				style="background: transparent; color: #f55; border: 1px solid #f55; padding: 0 6px; font-size: 10px;"
			>X</button>
		</div>
	</div>
	{#if !collapsed}
		<div>build: <span style="color: #6ff;">{buildId}</span></div>
		<div>token: <span style="color: #6ff;">{getToken() ? "yes" : "no"}</span> ({getTokenSource()})</div>
		<div>statusLoading: <span style="color: {ui.statusLoading ? '#f55' : '#5f5'};">{String(ui.statusLoading)}</span></div>
		<div>activeProvider: <span style="color: #6ff;">{ui.activeProvider || "(null)"}</span></div>
		<div>activeModel: <span style="color: #6ff;">{ui.activeModel || "(null)"}</span></div>
		<div>providers: <span style="color: #6ff;">{Object.keys(ui.providers).length}</span></div>
		<div style="margin-top: 6px; border-top: 1px dashed #0f0; padding-top: 4px;">
			<strong>logs</strong> ({logs.length})
		</div>
		{#each logs as log}
			<div style="color: {log.level === 'error' ? '#f55' : '#fc6'}; word-break: break-all;">
				[{log.ts}] {log.text}
			</div>
		{/each}
		{#if logs.length === 0}
			<div style="color: #555;">(no warnings yet)</div>
		{/if}
	{/if}
</div>
