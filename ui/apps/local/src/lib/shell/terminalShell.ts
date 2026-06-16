// 로컬 셸이 TerminalSurface 에 주입하는 부품 — hosts(뷰어/재무 lazy 로더)·links(헤더 SNS).
// hosts = null → ViewerOverlay 가 viewer 포트 URL(iframe /analysis/[code]/viewer)을 쓴다. 컴포넌트 임베드는
// 단계-6(viewer surface 추출) 후 검토 — 그때 viewerStudio 로더를 채운다.
import { DARTLAB_BRAND_LINKS, type TerminalHosts } from '@dartlab/ui-surfaces/terminal';

export const localHosts: TerminalHosts = {
	viewerStudio: null,
	financeDialog: null
};

// 헤더 SNS·후원 링크 = dartlab 공통 SSOT(DARTLAB_BRAND_LINKS) 그대로 주입 — landing 셸과 동일 정본.
export const localLinks = DARTLAB_BRAND_LINKS;
