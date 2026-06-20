// 관점 5종 — 같은 회사를 5개 렌즈로(투자자 질문 축으로 분리). 데이터 작업대 리얼타임.
// built=false 는 후속 사이클에서 리얼타임 구현(현재는 정직 '준비 중' 표기).
export interface PerspectiveMeta {
	key: string;
	label: string;
	question: string; // 한 줄 정의 — 투자자가 답을 얻는 질문
	focusQuestions: string[];
	built: boolean;
}

export const PERSPECTIVES: PerspectiveMeta[] = [
	{
		key: 'earningsPower',
		label: '수익체력',
		question: '얼마나 · 어떤 질로 버는가',
		focusQuestions: ['매출과 이익은 어떻게 움직였나', '마진은 개선되나', '이익이 현금으로 돌아오나'],
		built: true
	},
	{
		key: 'liquidity',
		label: '곳간과 빚',
		question: '버틸 수 있는가 · 현금이 도는가',
		focusQuestions: ['현금은 어떻게 도나', '빚을 갚을 여력은', '재무건전성은 견고한가'],
		built: true
	},
	{
		key: 'capitalReturn',
		label: '주주환원',
		question: '무엇을 돌려주고 얼마나 희석하나',
		focusQuestions: ['배당은 얼마나', '자사주는 태우나 쌓나', '주식 희석 이력'],
		built: true
	},
	{
		key: 'market',
		label: '시장의 평가',
		question: '시장은 어떻게 값매기나',
		focusQuestions: ['주가는 어떻게 움직였나', '시장과 얼마나 동행하나', '이익 대비 얼마에 거래되나'],
		built: true
	},
	{
		key: 'ownership',
		label: '누구의 회사',
		question: '주인 · 인력 · 감사의 질',
		focusQuestions: ['누가 소유했나', '누가 일하고 받나', '회계는 믿을 만한가'],
		built: true
	}
];

export function findPerspective(key: string): PerspectiveMeta {
	return PERSPECTIVES.find((p) => p.key === key) ?? PERSPECTIVES[0];
}
