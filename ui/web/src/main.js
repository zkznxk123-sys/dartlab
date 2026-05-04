import { mount } from "svelte";
import App from "./App.svelte";

// VSCode webview 환경 감지 → CSS 테마 매핑 활성화
if (window.__vscode || typeof window.acquireVsCodeApi === "function") {
	document.body.setAttribute("data-vscode", "");
}

const target = document.getElementById("app");
target?.querySelector("#boot-fallback")?.remove();
const app = mount(App, { target });

export default app;
