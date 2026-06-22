// 라이브 덱 빌더 — buildReport(라이브·무-bake) + hfMedia hero 를 합쳐 CarouselDeck 를 만든다.
// 순수 투영(projectResult)과 분리: 여기는 런타임 I/O(데이터·미디어), 투영은 fixture 테스트 가능한 순수 함수.
import type { DartLabRuntime } from '@dartlab/ui-contracts';
import type { CarouselDeck } from './model';
import { projectResult } from './project';
import { buildReport } from '$lib/report/build';
import { findPerspective, PERSPECTIVES } from '$lib/report/perspectives';
import { loadMediaIndex, heroUrl } from './media';

/** 종목+관점 → 라이브 슬라이드 덱. 데이터·미디어 동시 로드, skip/pending 도 정직 카드로(빈 화면 금지). */
export async function buildDeck(rt: DartLabRuntime, code: string, perspectiveKey: string): Promise<CarouselDeck> {
	const persp = findPerspective(perspectiveKey);
	const [result, media] = await Promise.all([buildReport(rt, code, perspectiveKey), loadMediaIndex()]);
	return projectResult(result, persp.label, { heroUrl: heroUrl(media, code) });
}

/** 플레이어 관점 탭 — 구현된 관점만. */
export const DECK_PERSPECTIVES = PERSPECTIVES.filter((p) => p.built).map((p) => ({ key: p.key, label: p.label }));
