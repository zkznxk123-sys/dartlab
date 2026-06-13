import { base } from '$app/paths';
import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';

// 로컬 UI 진입 = 곧장 터미널(제품). 공표 사이트가 /terminal 로 여는 것과 동일 — 개발용 라우트
// 목록이 아니라 터미널이 첫 화면이다. 기본 종목 = 005930(삼성전자), 공표 TerminalSurface initial 과 정합.
// 챗·뷰어·설정은 터미널 안/딥링크로 접근 (홈은 절차 없이 바로 제품).
export const load: PageLoad = () => {
	redirect(307, `${base}/terminal/005930`);
};
