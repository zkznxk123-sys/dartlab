// 공시 Q&A 세션 상태 — AskDrawer 외부의 모듈 싱글턴. 회사 이동(viewer +page 가 bundle 재로드 시 잠깐
// bundle=null → studio 언마운트)로 AskDrawer 가 언마운트돼도 대화·모델·Ollama 상태가 생존해야 "AI 화면
// 그대로(크로스-회사 대화 유지)" 요구가 성립한다. 컴포넌트 내부 $state 는 언마운트 시 소실되므로 여기로 올린다.
// 초기화 시점 = 전체 새로고침(F5)뿐. (탭당 뷰어 1개 — 싱글턴 오염 없음. 대화는 회사 배지로 구분된다.)
import type { SearchHit } from './searchIndex';

export interface EvRef {
	n: number;
	period: string;
	path: string;
	text: string;
	stale: boolean;
}
export interface NavOption {
	code: string;
	name: string;
}
export interface Turn {
	q: string;
	companyName: string; // 이 답을 만든 회사명 (history 태그·배지·전환 divider)
	nav: NavOption[]; // 이동 칩(타 회사 감지 시). [] 면 일반 답 turn
	det: string;
	citedLabel: string | null;
	evItems: EvRef[];
	evHits: SearchHit[];
	ai: string;
	aiRunning: boolean;
	aiErr: string | null;
}
export type ModelState = 'checking' | 'unsupported' | 'idle' | 'loading' | 'ready' | 'error';
export type OllamaState = 'hidden' | 'probing' | 'ready' | 'no-model' | 'blocked';

export const ask = $state<{
	chat: Turn[];
	modelState: ModelState;
	ollamaState: OllamaState;
	ollamaModel: string | null;
	consumedCarry: string; // 이미 자동실행한 carryQ — 재마운트에도 생존해 수동 종목검색 후 묵은 질문 재발화 차단
}>({
	chat: [],
	modelState: 'checking',
	ollamaState: 'hidden',
	ollamaModel: null,
	consumedCarry: ''
});
