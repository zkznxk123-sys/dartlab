// 뷰어 컴포넌트 주입 계약 — terminal → viewer 역의존 제거 (4a-3 주입 역전).
// 셸이 lazy 로더를 주입한다: landing = `$lib/components/viewer/*` 동적 import(청크 분리 유지),
// ui/web = null. null = "이 셸은 임베드 미지원" 명시 선언 — 패널이 직접 열화 안내를 렌더하므로
// silent fallback 이 아니다 (열화 티어 UX: 숨김 금지 + 안내, 03 §1).
import type { Component } from 'svelte';

export interface ViewerStudioHostProps {
	code: string;
	vs: string[];
	embedded: boolean;
	basePath?: string; // 셸 base 경로(에셋 — 임베드 뷰어 아바타) — ViewerOverlay 가 runtime.env.basePath 주입.
	tier?: 'public' | 'local'; // export tier 라벨(03 §7) — ViewerOverlay 가 runtime.env.kind 로 주입.
	focusAsk?: boolean; // 터미널 "AI" 진입 → 마운트 시 AskDrawer 자동 오픈(컴포넌트 임베드 경로).
	onNavigate: (code: string, vs: string[]) => void;
	onclose: () => void;
}

export interface FinanceDialogHostProps {
	code: string;
	corpName: string;
	open: boolean;
	onclose: () => void;
}

export interface TerminalHosts {
	/** 공시뷰어 본체(ViewerStudio) lazy 로더 — null 이면 ViewerOverlay 는 URL(iframe) 경로만 지원. */
	viewerStudio: (() => Promise<{ default: Component<ViewerStudioHostProps> }>) | null;
	/** 정량 재무제표 모달(FinanceDialog) lazy 로더 — null 이면 열화 안내 모달. */
	financeDialog: (() => Promise<{ default: Component<FinanceDialogHostProps> }>) | null;
}

/** 셸 식별 외부 링크 — 헤더 SNS·이슈·후원 칩. 셸(landing·ui/web)이 자기 brand 에서 주입한다.
 * surface 가 brand 정체성을 소유하지 않게 하는 주입 계약(역의존 제거, 단계-4b). 값은 공개 URL. */
export interface TerminalBrandLinks {
	repo: string;
	coffee: string;
	youtube: string;
	threads: string;
	instagram: string;
}
