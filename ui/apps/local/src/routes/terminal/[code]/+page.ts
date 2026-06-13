// 로컬 터미널 로더 — ssr=false(루트 +layout 캐스케이드, 브라우저 CSR)에서 RawData 씨드 조립.
import { loadTerminalRaw } from '$lib/shell/routeLoad';
import type { PageLoad } from './$types';

export const load: PageLoad = ({ params, fetch }) => loadTerminalRaw(params.code, fetch);
