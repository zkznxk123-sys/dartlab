// 편집 카드 캐러셀 계약 클라이언트 — hfMedia `carousels/index.json`(코드 목록) + `carousels/{code}.json`
// (손글 편집 슬라이드)을 로드하고, 슬라이드 image(semantic)를 hfMedia 해시 파일명 URL 로 해석한다.
// 굽지 않음 — 계약을 라이브로 읽어 렌더. 미게시면 graceful(빈 set / null).
import { originUrl } from '@dartlab/ui-runtime/data/origins/registry';
import type { CarouselContract, ContractIndex, CarouselCard, MediaIndex } from './model';
import { mediaKey, mediaCompany } from './media';

let _codes: Promise<Set<string>> | null = null;

/** 계약 있는 회사 코드 집합(피드가 "이미지 있는 것만" 보여줄 때). 1회 fetch. */
export function loadContractCodes(): Promise<Set<string>> {
	_codes ??= fetch(originUrl('hfMedia', 'carousels/index.json'))
		.then((r) => (r.ok ? (r.json() as Promise<ContractIndex>) : { codes: [] }))
		.then((j) => new Set(j.codes ?? []))
		.catch(() => new Set<string>());
	return _codes;
}

const _cache = new Map<string, Promise<CarouselContract | null>>();

/** 한 회사 편집 계약 로드(프로세스 캐시). 없으면 null. */
export function loadContract(code: string): Promise<CarouselContract | null> {
	const key = mediaKey(code);
	if (!_cache.has(key)) {
		_cache.set(
			key,
			fetch(originUrl('hfMedia', `carousels/${key}.json`))
				.then((r) => (r.ok ? (r.json() as Promise<CarouselContract>) : null))
				.catch(() => null)
		);
	}
	return _cache.get(key)!;
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
