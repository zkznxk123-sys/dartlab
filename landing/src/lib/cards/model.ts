// 라이브 카드 캐러셀 모델 — /report 의 ReportModel 을 슬라이드 덱으로 투영한 결과 타입.
// 굽지 않음(라이브). 카드 본문 차트는 report 인라인 SVG 헬퍼($lib/report/render)로 그려 백테스트·
// klinecharts 0 의존(백본). 손글 narration·hero 이미지는 큐레이션 오버레이(P5)·hfMedia(P0)에서 합류.
import type { ReportSourceEngine } from '$lib/report/model';

/** hfMedia(companies/index.json)의 회사별 항목 — 서빙용(name=콘텐츠해시 삽입된 served 파일명). */
export interface MediaAsset {
	/** 콘텐츠해시 삽입 served 파일명 (`dram-chip.ab12cd34.webp`). */
	name: string;
	hash: string;
}
export interface MediaCompany {
	displayName: string;
	market: 'kr' | 'us';
	similarTo: string[];
	assets: MediaAsset[];
}
export interface MediaIndex {
	version: number;
	companies: Record<string, MediaCompany>;
}

/** 슬라이드 공통 머리 — splitTitle 로 쪼갠 섹션 제목 + 큐레이션 손글 caption(note) + 배경 hero 사진. */
interface CardHead {
	heading?: string;
	sub?: string;
	engine?: ReportSourceEngine;
	/** 큐레이션 오버레이(CarouselSpec.notes)에서 주입한 손글 한 줄 — no-new-number(본문 숫자⊆). 자동 투영엔 없음. */
	note?: string;
	/** 배경 hero 사진 URL — 전 슬라이드가 회사 사진을 배경으로(인스타 에디토리얼). hero 전부를 슬라이드에 순환 배정. */
	bg?: string;
}

// 카드(슬라이드) 판별 유니온. chart 계열(line/bars/share/table)은 ReportBlock 과 1:1.
export type CarouselCard =
	| (CardHead & {
			kind: 'cover';
			corpName: string;
			stockCode: string;
			perspectiveLabel: string;
			conclusion: string;
			dataBasis: string;
	  })
	| (CardHead & { kind: 'kpis'; metrics: { label: string; value: string }[] })
	| (CardHead & { kind: 'narrative'; text: string })
	| (CardHead & { kind: 'flags'; tone: 'warning' | 'opportunity'; items: string[] })
	| (CardHead & {
			kind: 'line';
			series: number[];
			xLabels?: [string, string];
			markers?: { label: string; v: number }[];
			valueFmt?: 'won';
	  })
	| (CardHead & { kind: 'bars'; rows: { label: string; value: number; display: string; tone?: 'neg' }[] })
	| (CardHead & {
			kind: 'share';
			rows: { year: string; segs: { label: string; pct: number; key: string }[] }[];
			legend: { label: string; key: string }[];
	  })
	| (CardHead & { kind: 'table'; cols: string[]; data: Record<string, string>[]; unit?: string })
	| (CardHead & { kind: 'finChart'; stockCode: string }) // MiniFinChart 백본(finance.bundle)
	| (CardHead & { kind: 'closing'; thesis: string })
	| (CardHead & { kind: 'empty'; reason: string }) // pending/skip 정직 카드(broken img 아님)
	// ── 편집 카드(기존 SNS 캐러셀 계약 carousels/{code}.json 손글 카피) — `[[강조]]`=accentImpact ──
	| (CardHead & { kind: 'editorial'; date?: string; line: string; sub?: string }) // 커버
	| (CardHead & { kind: 'editorialBeat'; kicker?: string; line: string; sub?: string }) // 헤드라인 비트
	| (CardHead & { kind: 'editorialStat'; kicker?: string; bigNumber: string; unit?: string; context?: string }); // 큰 숫자

export interface CarouselDeck {
	stockCode: string;
	corpName: string;
	market?: 'kr' | 'us';
	perspectiveKey: string;
	perspectiveLabel: string;
	asOf: string;
	heroUrls: string[]; // 회사 hero 전부(슬라이드 배경 순환). 첫 장 = 표지 사진.
	cards: CarouselCard[];
}

// ── 편집 카드 캐러셀 계약(carousels/{code}.json) — 기존 SNS 캐러셀 손글 카피 SSOT. ──
export interface ContractSlide {
	layout: 'editorial' | 'editorialBeat' | 'editorialStat';
	date?: string;
	kicker?: string;
	line?: string;
	sub?: string;
	bigNumber?: string;
	unit?: string;
	context?: string;
	image?: string; // semantic 파일명(해시 없음) — 렌더가 hfMedia 매니페스트로 해석
}
export interface CarouselContract {
	code: string;
	name: string;
	sector?: string;
	/** 인스타 포스트 제목(meta.json title) — 우측 캡션 패널 헤드라인. */
	title?: string;
	/** 인스타 캡션(caption.txt) — 포스트 우측 설명 산문(문단=빈 줄 구분). 슬라이드와 별개의 본문. */
	caption?: string;
	/** 고정 댓글(comment_pinned.txt) — 근거·면책. 캡션 하단 작게. */
	pinnedComment?: string;
	slides: ContractSlide[];
}
export interface ContractIndex {
	codes: string[];
}

// ── 큐레이션 오버레이(P5) — blog frontmatter `carousel:` 선택 블록. 없으면 자동 투영만. ──
export interface CarouselSpec {
	/** 슬라이드별 손글 narration — key=섹션 key 또는 슬라이드 인덱스, 숫자는 모델값 부분집합(no-new-number). */
	notes?: Record<string, string>;
	/** 표지에 띄울 hero 파일명(미지정 시 hfMedia 첫 hero). */
	hero?: string;
	/** 슬라이드 노출 순서/필터(섹션 key 목록). 미지정 시 자동 순서. */
	order?: string[];
}
