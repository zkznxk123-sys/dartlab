// table-export 계약 — 공시 표 → 진짜 .xlsx 내보내기. 3 표면(엔진·공개 landing·로컬 터미널)을 한 Port 로 통제.
// 왜 신 ExportPort 인가(ServicesPort 단독 기각, 03 §2): ServiceCommandResult 는 status/toast/panel/ask 만 —
// Blob/파일 URL 을 실어 나를 표면이 없다. export 에 욱여넣으면 payload:unknown 에 Blob 을 숨겨 타입 안전·
// public_contract_only 위반. 15 Port 가 이미 도메인 분리라 Port 추가가 일관(runtime.ts §required·silent fallback 금지).
//
// 분업: ServiceGroup 'export'(services.ts) = command palette(⌘K) 진입점. 그 command 의 execute 가 ExportPort.generate
// 를 호출 후 ServiceCommandResult{kind:'toast'} 반환. 두 계약 분업.

/**
 * 내보내기 가능한 표 1행 — `listExportableTables(bundle)` 산출. PanelBundle 의 gridBySection 순회로 수집.
 * (sectionKey, blockLeaf, disclosureKey, scope) 로 식별. 선택 UX(체크박스 오버레이)가 이 목록을 렌더.
 */
export interface ExportableTable {
	/** 안정 id — `${sectionKey}|${blockLeaf}` (disclosureKey 우선). 같은 blockLeaf 다중행은 surface 가 절대 인덱스로 보강. */
	id: string;
	sectionKey: string;
	blockLeaf: string;
	disclosureKey: string | null;
	scope: string | null;
	/** blockType==='table'. text 블록도 narrative 시트로 내보낼 수 있어 목록엔 포함하되 이 플래그로 구분. */
	hasTable: boolean;
	/** 이 행이 값을 가진 기간(최신 좌측). 빈 기간 honest-gap. */
	periods: string[];
}

/**
 * 한 시트 선택 DTO — 직렬화 가능(JSON-safe). 임시 양식 = 선택 그대로. 미래 AI `viewerActions.exportSelection`
 * 채널이 자연어를 selection 으로 변환할 수 있게 순수 데이터로 둔다(03 §5).
 */
export interface SheetSelectionDTO {
	id: string;
	sectionKey: string;
	blockLeaf: string;
	disclosureKey: string | null;
	scope: string | null;
	/** 시트명(편집됨, 31자 트림은 writer 가 최종 담당). */
	label: string;
	mode: 'asFiled' | 'horizontalized';
	/** 셀 선택이면 그 period(들), 행 전체면 'all'. */
	periods: string[] | 'all';
	/** 드래그 정렬 = 시트 순서. */
	order: number;
}

/**
 * 내보내기 입력 — 회사 + 선택 시트들(+ 회사 이식·출처 옵션). public·local 어댑터 공통 입력(패리티 토대).
 */
export interface ExportInput {
	code: string;
	selections: SheetSelectionDTO[];
	/** 회사 이식(N사) 대상 종목코드들 — local 일괄 ZIP, public 후속. */
	grafts?: string[];
	/** 출처 시트(어떤 회사·시점·섹션을 어떤 모드로) 포함 여부(기본 true 권장). */
	includeProvenance?: boolean;
}

/**
 * 내보내기 산출물 — public 은 브라우저 생성 Blob, local 은 서버 FileResponse url(또는 ZIP url). 둘 중 하나만 채움.
 * surface 가 blob → downloadBlob / url → navigate 로 분기(동일 다운로드 UX).
 */
export interface ExportArtifact {
	filename: string;
	mime: string;
	/** public — 브라우저 OOXML 생성. */
	blob?: Blob;
	/** local — 서버 FileResponse(.xlsx 또는 ZIP) URL. */
	url?: string;
}

// ── 양식(ExcelTemplate) 스키마 — 엔진 `viz/export/template.py` 의 JSON 미러(public↔local 패리티 토대) ──
// SheetSource = discriminated union(ModuleSource | PanelTableSource) + str 하위호환(엔진 _coerceSource 가 흡수).
// 브라우저 selection 은 PanelTableSource 형태만 직접 만들지만, 양식 CRUD 는 union 전체를 round-trip 해야 한다.

/** 모듈/재무 시트 소스 — IS/BS/CF/ratios/dividend/... 분기(엔진 writer). */
export interface ModuleSource {
	kind: 'module';
	name: string;
}

/** 공시 panel 단일 표 소스 — 병합 보존 격자 export(엔진 PanelTableSource 7-필드 식별, leafSeq 디스앰비그). */
export interface PanelTableSource {
	kind: 'panelTable';
	chapter: string;
	sectionLeaf: string;
	blockLeaf: string;
	leafType: string;
	disclosureKey: string | null;
	scope: string | null;
	/** wide 행의 섹션 내 ordinal — 같은 섹션 다중 표 디스앰비그(null=첫 매칭). */
	leafSeq: number | null;
	periodMode: 'asFiled' | 'horizontalized';
	/** asFiled 면 단일 기간; horizontalized 면 null(전 기간). */
	period: string | null;
}

/** 시트 데이터 소스 — union + str 하위호환(저장 양식 JSON 의 `"source":"IS"`). */
export type SheetSource = ModuleSource | PanelTableSource | string;

/** 단일 시트 명세 — 엔진 SheetSpec 미러. columns/years/sortBy/maxRows 는 ModuleSource 한정. */
export interface SheetSpec {
	source: SheetSource;
	label: string;
	columns?: string[];
	years?: string[];
	sortBy?: string;
	maxRows?: number;
}

/** Excel 내보내기 양식 — 엔진 ExcelTemplate 미러(toJson/fromJson round-trip 동형). */
export interface ExcelTemplate {
	name: string;
	sheets: SheetSpec[];
	description?: string;
	createdAt?: number;
	updatedAt?: number;
	templateId?: string;
}

/**
 * 내보내기 가능한 표 목록을 추출하는 순수 함수가 읽는 PanelBundle 의 구조적 최소면.
 * contracts 는 의존 0 이라 surfaces 의 PanelBundle 을 import 하지 않는다 — surfaces PanelBundle 이
 * 이 형태를 구조적으로 만족하므로 그대로 인자로 넘어온다(structural typing).
 */
export interface ExportBundleLike {
	periods: string[];
	gridBySection: Map<
		string,
		Array<{
			blockLeaf: string;
			disclosureKey: string | null;
			scope: string | null;
			blockType: 'text' | 'table';
			cells: Record<string, string>;
		}>
	>;
}

/**
 * Export Port — 양식 CRUD + 파일 생성. public(브라우저 OOXML)·local(엔진 openpyxl 완전판) 분기.
 * 메서드 전부 required(runtime.ts §silent fallback 금지) — 미지원은 throw 가 아니라 정직한 빈/에러 산출.
 *
 * - `listExportableTables`: 순수 함수(fetch 0). 이미 로드된 PanelBundle 에서 추출(03 §4 — 별도 API call 금지).
 * - 양식 CRUD: public 은 StoragePort/localStorage + 동봉 PRESETS, local 은 /api/export/templates.
 * - `generate`: public 은 buildWorkbook → Blob, local 은 POST /api/export/excel → url(FileResponse).
 */
export interface ExportPort {
	listExportableTables(bundle: ExportBundleLike): ExportableTable[];
	listTemplates(): Promise<ExcelTemplate[]>;
	saveTemplate(template: ExcelTemplate): Promise<string>;
	deleteTemplate(id: string): Promise<boolean>;
	generate(input: ExportInput): Promise<ExportArtifact>;
}
