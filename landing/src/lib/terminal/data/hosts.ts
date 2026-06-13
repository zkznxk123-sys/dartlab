// 뷰어 컴포넌트 주입 계약 — terminal → viewer 역의존 제거 (4a-3 주입 역전).
// 셸이 lazy 로더를 주입한다: landing = `$lib/components/viewer/*` 동적 import(청크 분리 유지),
// ui/web = null. null = "이 셸은 임베드 미지원" 명시 선언 — 패널이 직접 열화 안내를 렌더하므로
// silent fallback 이 아니다 (열화 티어 UX: 숨김 금지 + 안내, 03 §1).
import type { Component } from 'svelte';

export interface ViewerStudioHostProps {
	code: string;
	vs: string[];
	embedded: boolean;
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
