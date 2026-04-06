/**
 * Dev harness entry — fixture 기반 스트리밍 재생기.
 *
 * 목적: Vite dev server 없이도 webview 렌더링을 브라우저에서 검증.
 * vite.config 의 second rollup input 으로 빌드됨 → dist/webview/dev.js
 *
 * harness.html 이 이 파일을 로드해서 mount.
 */
import { mount } from "svelte";
import DevShell from "./DevShell.svelte";

// VSCode API shim — 진짜 webview 환경 흉내
(globalThis as { acquireVsCodeApi?: unknown }).acquireVsCodeApi = () => ({
  postMessage: (msg: unknown) => console.log("[postMessage]", msg),
  getState: () => ({}),
  setState: () => {},
});

mount(DevShell, { target: document.getElementById("app")! });
