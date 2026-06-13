// 로컬 셸이 TerminalSurface 에 주입하는 부품 — hosts(뷰어/재무 lazy 로더)·links(헤더 SNS).
// hosts = null → ViewerOverlay 가 viewer 포트 URL(iframe /analysis/[code]/viewer)을 쓴다. 컴포넌트 임베드는
// 단계-6(viewer surface 추출) 후 검토 — 그때 viewerStudio 로더를 채운다.
import type { TerminalBrandLinks, TerminalHosts } from '@dartlab/ui-surfaces/terminal';

export const localHosts: TerminalHosts = {
	viewerStudio: null,
	financeDialog: null
};

// 헤더 SNS 외부 링크 — dartlab 공개 정체성(브랜드 링크, 데이터 URL 아님).
export const localLinks: TerminalBrandLinks = {
	repo: 'https://github.com/eddmpython/dartlab',
	coffee: 'https://buymeacoffee.com/eddmpython',
	youtube: 'https://www.youtube.com/@eddmpython',
	threads: 'https://www.threads.net/@dartlab.ai',
	instagram: 'https://www.instagram.com/dartlab.ai/'
};
