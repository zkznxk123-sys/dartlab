// 터미널 "AI" 진입 신호 — 헤더(TerminalSurface)와 공시뷰어 오버레이 소유자(RightStack)가 서로 다른
// 컴포넌트라, 헤더 버튼이 오버레이를 챗 모드로 여는 신호를 모듈 rune 스토어로 전한다(prop drilling 회피).
//
// pulse 단조 증가 = "AI 챗 모드로 열어라". RightStack 가 마지막 처리한 pulse 와 비교해 변할 때만 1회
// 반응한다 — 단조 증가라 reset·untrack 불필요(자기참조 루프 없음, Phase 2b self-clear 회귀 회피).
export const askEntry = $state({ pulse: 0 });

/** 헤더 "AI" 버튼이 호출 — 터미널 내 뷰어 오버레이를 AskDrawer 포커스로 연다. */
export function requestAsk(): void {
	askEntry.pulse += 1;
}
