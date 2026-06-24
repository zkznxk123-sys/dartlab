// 편집 카드 캐러셀 계약 클라이언트 — hfMedia `carousels/index.json`(글 목록 posts[]) + `carousels/{slug}.json`
// (손글 편집 슬라이드)을 로드하고, 슬라이드 image(semantic)를 hfMedia 해시 파일명 URL 로 해석한다.
// 키 = 글 슬러그(회사당 N편 1:N). 굽지 않음 — 계약을 라이브로 읽어 렌더. 미게시면 graceful(빈 배열 / null).
import { originUrl } from '@dartlab/ui-runtime/data/origins/registry';
import type { CarouselContract, ContractIndex, ContractPost, CarouselCard, MediaIndex } from './model';
import { mediaKey, mediaCompany } from './media';

let _posts: Promise<ContractPost[]> | null = null;

/** 발간된 캐러셀 글 목록(피드). index.json posts[] 순서 = 발간 최신순(build 가 date 내림차순). 1회 fetch. */
export function loadContractPosts(): Promise<ContractPost[]> {
	_posts ??= fetch(originUrl('hfMedia', 'carousels/index.json'))
		.then((r) => (r.ok ? (r.json() as Promise<ContractIndex>) : { posts: [] }))
		.then((j) => j.posts ?? [])
		.catch(() => [] as ContractPost[]);
	return _posts;
}

const _cache = new Map<string, Promise<CarouselContract | null>>();

/** 한 글 편집 계약 로드(슬러그 키·프로세스 캐시). 없으면 null. */
export function loadContract(slug: string): Promise<CarouselContract | null> {
	if (!_cache.has(slug)) {
		_cache.set(
			slug,
			fetch(originUrl('hfMedia', `carousels/${slug}.json`))
				.then((r) => (r.ok ? (r.json() as Promise<CarouselContract>) : null))
				.catch(() => null)
		);
	}
	return _cache.get(slug)!;
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
