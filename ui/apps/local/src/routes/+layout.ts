// 로컬 앱 = 클라이언트 렌더 SPA(데이터는 /api, AI 는 /api/agent). 동적 [code] 라우트를 prerender 하지 않는다.
// adapter-static + fallback:'index.html' 와 짝 — 전 라우트에 ssr=false 가 캐스케이드된다.
export const ssr = false;
export const prerender = false;
