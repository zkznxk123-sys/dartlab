// landing 셸이 TerminalSurface 에 주입하는 부품 — /terminal · /lab/terminal-dev 공용 SSOT.
// hosts = 뷰어 컴포넌트 lazy 로더(동적 import 리터럴은 셸 소유 → 청크 분리 유지, terminal→viewer 역의존 제거).
// links = 헤더 SNS 외부 링크(셸 brand 에서 파생 → surface 가 brand 정체성 소유 안 함, 단계-4b).
import { brand } from '$lib/brand';
import type { TerminalBrandLinks, TerminalHosts } from '@dartlab/ui-surfaces/terminal';

export const terminalHosts: TerminalHosts = {
	viewerStudio: () => import('@dartlab/ui-surfaces/viewer').then((m) => ({ default: m.ViewerStudio })),
	financeDialog: () => import('@dartlab/ui-surfaces/viewer').then((m) => ({ default: m.FinanceDialog }))
};

export const terminalLinks: TerminalBrandLinks = {
	repo: brand.repo,
	coffee: brand.coffee,
	youtube: brand.youtube,
	threads: brand.threads,
	instagram: brand.instagram
};
