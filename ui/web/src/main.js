// ★ 진단용: JS 파일 첫 줄. 이게 실행되면 탭 제목이 무조건 [JS-START]로 바뀜.
//    탭 제목이 안 바뀌면 → JS가 아예 안 돌고 있음 (syntax error 또는 hydration 실패)
try { document.title = "[JS-START] DartLab"; } catch (_) {}

import { mount } from "svelte";
import App from "./App.svelte";
import { initToken, debugTokenStatus } from "./lib/api/token.js";
import { installConsoleCapture, isDebugEnabled } from "./lib/debug.js";

try { document.title = "[JS-IMPORTS] DartLab"; } catch (_) {}

// 디버그 모드 감지 + console.warn/error 캡처 (모바일 진단용)
if (isDebugEnabled()) {
	installConsoleCapture();
}

// __BUILD_ID__ 는 vite.config.js의 define 에서 주입
try {
	if (typeof __BUILD_ID__ !== "undefined") {
		console.log("[dartlab] build:", __BUILD_ID__);
	}
} catch {
	// ignore
}

// 터널 모드: URL 쿼리 ?token=... 에서 토큰 추출 → sessionStorage 저장 → URL 정리
// SPA의 모든 fetch가 이 토큰을 자동으로 Authorization 헤더에 부착한다.
initToken();
debugTokenStatus();

// VSCode webview 환경 감지 → CSS 테마 매핑 활성화
if (window.__vscode || typeof window.acquireVsCodeApi === "function") {
	document.body.setAttribute("data-vscode", "");
}

try { document.title = "[MOUNT-START] DartLab"; } catch (_) {}

let app;
try {
	app = mount(App, { target: document.getElementById("app") });
	try { document.title = "[MOUNT-OK] DartLab"; } catch (_) {}
} catch (e) {
	try { document.title = "[MOUNT-ERR] " + String(e).slice(0, 60); } catch (_) {}
	throw e;
}

export default app;
