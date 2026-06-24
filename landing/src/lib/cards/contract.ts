// 편집 카드 캐러셀 계약 클라이언트 — hfMedia `carousels/index.json` **한 파일**에 전 계약(슬라이드까지)이
// 배열로 담겨, 피드·상세 모두 이 1회 fetch 로 해결(별도 인덱스·카드별 round-trip 0). 슬라이드 image(semantic)는
// hfMedia 해시 파일명 URL 로 해석. 키 = 글 슬러그(회사당 N편 1:N). 굽지 않음. 미게시면 graceful(빈 배열 / null).
import { originUrl } from '@dartlab/ui-runtime/data/origins/registry';
import type { CarouselContract, ContractIndex, CarouselCard, MediaIndex } from './model';
import { mediaKey, mediaCompany } from './media';

let _all: Promise<CarouselContract[]> | null = null;

/** 전 캐러셀 계약 1회 fetch(단일 파일·프로세스 캐시). posts[] 순서 = 발간 최신순(build 가 date 내림차순). */
export function loadCarousels(): Promise<CarouselContract[]> {
	_all ??= fetch(originUrl('hfMedia', 'carousels/index.json'))
		.then((r) => (r.ok ? (r.json() as Promise<ContractIndex>) : { posts: [] }))
		.then((j) => j.posts ?? [])
		.catch(() => [] as CarouselContract[]);
	return _all;
}

/** 한 글 편집 계약(슬러그) — 캐시된 전체에서 찾기(추가 fetch 0). 없으면 null. */
export function loadContract(slug: string): Promise<CarouselContract | null> {
	return loadCarousels().then((all) => all.find((c) => c.slug === slug) ?? null);
}

/** 슬라이드 image(semantic 'cleanroom-engine') → hfMedia 해시 파일명 URL. 매니페스트에 없으면 undefined(폴백). */
export function resolveSlideImage(media: MediaIndex | null, code: string, image?: string): string | undefined {
	if (!image) return undefined;
	const c = mediaCompany(media, code);
	const hit = c?.assets.find((a) => a.name.startsWith(image + '.') || a.name === image);
	return hit ? originUrl('hfMedia', `companies/${mediaKey(code)}/${hit.name}`) : undefined;
}

/** 계약 → 편집 카드 슬라이드(라이브 렌더용). image 는 hfMedia URL 로 해석해 bg 에 싣는다. */
export function contractToCards(contract: CarouselContract, media: MediaIndex | null): CarouselCard[] {
	return contract.slides.map((s) => {
		const bg = resolveSlideImage(media, contract.code, s.image);
		if (s.layout === 'editorialStat') {
			return { kind: 'editorialStat', kicker: s.kicker, bigNumber: s.bigNumber ?? '', unit: s.unit, context: s.context, bg };
		}
		if (s.layout === 'editorialBeat') {
			return { kind: 'editorialBeat', kicker: s.kicker, line: s.line ?? '', sub: s.sub, bg };
		}
		return { kind: 'editorial', date: s.date, line: s.line ?? '', sub: s.sub, bg };
	});
}
