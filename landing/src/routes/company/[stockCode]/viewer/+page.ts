import type { PageLoad } from './$types';

// 공시뷰어 — 브라우저가 HF panel 하나를 직접 읽어 온더플라이 렌더 (서버 0). 동적 종목.
export const prerender = 'auto';
export const ssr = false;

export const load: PageLoad = ({ params }) => ({ code: params.stockCode });
