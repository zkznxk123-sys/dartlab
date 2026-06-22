// 라이브 덱 빌더 — buildReport(라이브·무-bake) + hfMedia hero 를 합쳐 CarouselDeck 를 만든다.
// 순수 투영(projectResult)과 분리: 여기는 런타임 I/O(데이터·미디어), 투영은 fixture 테스트 가능한 순수 함수.
import type { DartLabRuntime } from '@dartlab/ui-contracts';
import { originUrl } from '@dartlab/ui-runtime/data/origins/registry';
import type { CarouselDeck, CarouselSpec, MediaIndex } from './model';
import { projectResult } from './project';
import { buildReport } from '$lib/report/build';
import { findPerspective, PERSPECTIVES } from '$lib/report/perspectives';
import { getPostByStockCode } from '$lib/blog/posts';
import { loadMediaIndex, heroUrl, mediaKey, mediaCompany } from './media';

/** spec.hero(파일명) → hfMedia URL. 콘텐츠해시 stem 매칭(저장 파일명은 `{stem}.{hash}.webp`). 없으면 자동 hero. */
function resolveHero(media: MediaIndex | null, code: string, spec?: CarouselSpec): string | undefined {
	if (spec?.hero) {
		const stem = spec.hero.replace(/\.[a-z]+$/i, '');
		const c = mediaCompany(media, code);
		const hit = c?.assets.find((a) => a.name.startsWith(stem + '.') || a.name === spec.hero);
		if (hit) return originUrl('hfMedia', `companies/${mediaKey(code)}/${hit.name}`);
	}
	return heroUrl(media, code);
}

/** 종목+관점 → 라이브 슬라이드 덱. 데이터·미디어 동시 로드, blog frontmatter `carousel:` 큐레이션 오버레이.
 *  skip/pending 도 정직 카드로(빈 화면 금지). */
export async function buildDeck(rt: DartLabRuntime, code: string, perspectiveKey: string): Promise<CarouselDeck> {
	const persp = findPerspective(perspectiveKey);
	const spec = getPostByStockCode(code)?.carousel;
	const [result, media] = await Promise.all([buildReport(rt, code, perspectiveKey), loadMediaIndex()]);
	return projectResult(result, persp.label, { heroUrl: resolveHero(media, code, spec), spec });
}

/** 플레이어 관점 탭 — 구현된 관점만. */
export const DECK_PERSPECTIVES = PERSPECTIVES.filter((p) => p.built).map((p) => ({ key: p.key, label: p.label }));
