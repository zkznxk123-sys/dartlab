import { base } from '$app/paths';
import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';

// ui/web 의 /analysis/$code 와 동일하게 "회사 분석" 진입 = 풀스크린 터미널이다(LandingTerminalSurface).
// 로컬앱은 /terminal/[code] 를 정본 터미널 라우트로 두므로, /analysis/[code] 는 거기로 영구 합류한다
// (딥링크·홈 nav·viewer 하위 라우트 보존, 옛 placeholder 스텁 제거). vs(비교 코드)는 viewer 전용이라 무시.
export const load: PageLoad = ({ params }) => {
	redirect(307, `${base}/terminal/${params.code}`);
};
