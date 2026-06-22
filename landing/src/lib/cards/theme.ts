// 라이브 카드 캐러셀 디자인 토큰 — 기존 SNS 캐러셀 파이프라인(sns/remotion-sns/src/lib/colors.ts)의
// 색감을 그대로 가져온다(새로 짓지 않음·SSOT 동기화). 규격 = 인스타 4:5(1080×1350). 폰트 = Pretendard
// Variable(landing 전역 --font-sans 이미 배선). 브랜드 마크 = 공통 아바타(landing/static/avatar.webp).

/** colors.ts 미러 — rose-red 임팩트 + 네이비 에디토리얼. drift 시 colors.ts 와 동반 수정. */
export const CARD = {
	primary: '#ea4647', // 헤드라인 한 구절 강조(rose-red, stop-the-scroll)
	primaryDark: '#c83232',
	accent: '#fb923c', // 키커 점·라벨(orange)
	accentImpact: '#fb3f6c',
	bgDark: '#050811',
	bgDarker: '#030509',
	bgCard: '#0f1219',
	text: '#f1f5f9',
	textMuted: '#94a3b8',
	textDim: '#64748b',
	border: '#1e2433',
	success: '#34d399',
	warning: '#fbbf24'
} as const;

/** 인스타 캐러셀 규격(1080×1350 = 4:5). 카드는 이 비율로 반응형. */
export const CARD_ASPECT = '1080 / 1350';

/** AccentText — `[[구절]]` 을 강조색으로 쪼갠 토막 목록. 기존 AccentText.tsx 와 동일 규약(순수·테스트 가능). */
export function accentParts(text: string): { text: string; accent: boolean }[] {
	return String(text ?? '')
		.split(/(\[\[[^\]]+\]\])/g)
		.filter((p) => p !== '')
		.map((p) => {
			const m = p.match(/^\[\[([^\]]+)\]\]$/);
			return m ? { text: m[1], accent: true } : { text: p, accent: false };
		});
}
