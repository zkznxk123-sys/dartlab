# 03. Surfaces & Contract — 3-표면 아키텍처와 ExportPort 계약

상태: v0.1
범위: 엔진·공개(landing)·로컬 터미널 3 표면을 한 계약으로 통제. `ui/packages` 런타임 어댑터 패턴 준수.

---

## 1. 표면 토폴로지

```
ui/packages/contracts/   인터페이스(Port) SSOT — viewer/services/source/evidence ... + 신 export
ui/packages/runtime/     public(static/HF) 어댑터 + local(API) 어댑터 — Port 구현
ui/packages/surfaces/    공용 Svelte 표면 — TerminalSurface, ViewerOverlay (터미널 이미 이관됨)
landing/                 영구 public shell — 현재 viewer 본체 보유(이관 진행 전)
```

- export는 viewer/company와 독립 도메인(양식 CRUD + 파일 생성)이라 **신 `ExportPort`**를 둔다.
- `ServiceGroup 'export'`는 `contracts/src/services.ts`에 **이미 존재** → command palette(⌘K "엑셀로 내보내기") 진입점으로 쓰고, 그 command의 execute가 `ExportPort.generate`를 호출 후 `ServiceCommandResult{kind:'toast'}` 반환. **두 계약 분업.**

---

## 2. 왜 신 `ExportPort`인가 (ServicesPort 단독 기각)

`contracts/src/services.ts`의 `ServiceCommandResult`는 `kind:'status'|'toast'|'panel'|'ask'`만 반환한다 — **Blob/파일 URL을 실어 나를 표면이 없다.** export에 욱여넣으면 `payload:unknown`에 Blob을 숨기게 되고 타입 안전·`feedback_public_contract_only` 위반. 15개 Port가 이미 도메인별 분리(`runtime.ts`)라 Port 추가가 일관. 02 §3 런타임 계약 규율(Port 메서드 required·silent fallback 금지) 준수.

```typescript
// ui/packages/contracts/src/export.ts (신규)
import type { PanelBundle } from './viewer';        // 또는 적절 위치
import type { ExcelTemplate } from './export';      // 스키마 동봉

export interface ExportableTable {
  id: string;                 // `${sectionKey}|${blockLeaf}` (disclosureKey 우선)
  sectionKey: string;
  blockLeaf: string;
  disclosureKey: string | null;
  scope: string | null;
  hasTable: boolean;          // blockType==='table'
  periods: string[];          // 이 행이 값을 가진 기간
}

export interface SheetSelectionDTO {
  id: string; sectionKey: string; blockLeaf: string;
  disclosureKey: string | null; scope: string | null;
  label: string;                          // 시트명(편집됨)
  mode: 'asFiled' | 'horizontalized';
  periods: string[] | 'all';
  order: number;
}

export interface ExportInput {
  code: string;
  selections: SheetSelectionDTO[];        // 임시 양식 = 선택 그대로
  grafts?: string[];                      // 회사 이식 대상 종목코드들
  includeProvenance?: boolean;
}

export interface ExportArtifact {
  filename: string;
  mime: string;
  blob?: Blob;                            // public(브라우저 생성)
  url?: string;                           // local(서버 FileResponse)
}

export interface ExportPort {
  listExportableTables(bundle: PanelBundle): ExportableTable[];   // 순수 함수, fetch 0
  listTemplates(): Promise<ExcelTemplate[]>;
  saveTemplate(t: ExcelTemplate): Promise<string>;
  deleteTemplate(id: string): Promise<boolean>;
  generate(input: ExportInput): Promise<ExportArtifact>;
}
```

`ExcelTemplate`/`SheetSpec`/`SheetSource` JSON 스키마는 엔진 `template.py`(01 §2)와 **동일**하게 TS로 미러(`contracts`). 이게 public↔local 패리티의 토대.

---

## 3. 어댑터 — public vs local

| 메서드 | public 어댑터 (브라우저) | local 어댑터 (API) |
|---|---|---|
| `listExportableTables` | 동일 순수 함수(공유 모듈) | 동일 순수 함수 |
| `listTemplates` | `StoragePort`(localStorage) + 동봉 PRESETS(정적 JSON) | `GET /api/export/templates` |
| `saveTemplate` | localStorage write | `POST /api/export/templates` |
| `deleteTemplate` | localStorage delete | `DELETE /api/export/templates/{id}` |
| `generate` | `buildWorkbook`(02) → OOXML `Blob` 반환 | `POST /api/export/excel`(selection) → FileResponse `url` 반환 |

패리티 계약: **같은 `ExcelTemplate`/selection JSON** 입력으로 public(브라우저)·local(엔진)이 **동일 시트 구조** .xlsx를 낸다(02 §3 골든 패리티). 서버 0인 public은 `~/.dartlab/templates`를 못 쓰므로 localStorage + 동봉 프리셋, 엔진 전용 양식은 로컬에서만.

---

## 4. 미리보기 데이터 출처 — 별도 API call 금지

뷰어는 회사 진입 시 `buildPanelBundle`로 `gridBySection`(섹션→PanelRow[])·`toc`를 **이미 메모리 보유**. 테이블 목록 = `gridBySection` 순회해 `blockType==='table'` 수집(+텍스트 블록 옵션). TOC→시트 구조는 `bundle.toc`에서 직접. `listExportableTables(bundle)`는 **순수 함수**(네트워크 0) — 추가 fetch는 중복 다운로드 + LRU 캐시 무효화 유발. public·local 동일 모듈.

---

## 5. command palette / AI 채널

- `ServiceGroup 'export'`에 command 등록: id `export.tablesToExcel`, group `'export'`, mode `'both'`. execute → `runtime.export.generate(currentSelection)` → `{kind:'toast', ok, message:'다운로드 완료'}`.
- (후속, 이번 범위 밖이나 아키텍처가 받음) 채팅이 뷰어를 조작하는 `viewerActions` 채널에 `{kind:'exportSelection', selections}` 액션을 추가하면 AI가 "삼성 손익이랑 배당 엑셀로 빼줘"를 selection으로 변환 가능. 계약이 미래 레버를 막지 않게 `ExportInput`을 직렬화 가능 DTO로 둔다.

---

## 6. 터미널 통합 — 뷰어 이관 편승

현재 viewer 본체는 `landing/src/lib/components/viewer/`에 있고, `ui/packages/surfaces`엔 `ViewerOverlay.svelte`·`SourcesModal.svelte`가 있다. 터미널(`TerminalSurface.svelte`)은 이미 surfaces로 이관됨.

- export의 **공유 모듈**(격자 파서·xlsx writer·selection 모델·`tableExtract`)과 **ExportPort 계약**은 표면 무관하게 작성한다. 
- Phase 2는 현 landing 뷰어에 직접 배선(오늘 동작). Phase 3는 viewer가 `landing→ui/packages/surfaces`로 이관될 때(`project_ui_platform_refactor`, 운영자 go 대기) **그대로 실려 간다** — ExportDrawer·selection 레이어가 surface 컴포넌트가 되고, public/local 어댑터가 `generate`를 분기.
- 터미널 우측 패널·command palette에서 export는 `ServiceGroup 'export'`로 노출. 로컬은 `availability:'available'`(엔진 완전판), 공개는 상위 스타일링을 `localOnly` 변형으로 `[설치]` hint(아래 §7).

---

## 7. tier UX — 숨기지 않고 라벨

`feedback_ui_rules`: 공개에서 로컬 전용 상위 기능을 *숨기지 말고* tier 표시 + 업그레이드 hint(funnel).

- 공개 ExportDrawer 하단 **항상**: "이 브라우저 내보내기 = 빠른 .xlsx. 자동너비·음수 빨강·풍부한 서식의 완전판은 로컬 터미널 dartlab. [설치 ↗]". 기능을 숨기지 않고 tier 라벨만.
- 로컬: hint 없음, `[완전판 .xlsx ⬇]`.
- 두 표면 **선택 인터랙션은 100% 동일**(셀/TOC 체크박스·드로어·드래그·모드 토글) — 산출 백엔드만 분기.

---

## 8. 영향 파일 / 함수

신규:
- `ui/packages/contracts/src/export.ts`(+ `index.ts`·`runtime.ts`에 `ExportPort` 등록).
- `ui/packages/runtime/src/adapters/public/sources/exportSource.ts`(브라우저 OOXML).
- `ui/packages/runtime/src/adapters/local/sources/exportSource.ts`(/api 프록시).
- 공유 모듈(표면 이식 가능 위치) — 격자 파서·writer·selection·tableExtract. Phase 2는 `landing/src/lib/viewer/xlsx/`·`export/`에 두고, 이관 시 `ui/packages`로 승격.

수정:
- `ui/packages/runtime/src/services/serviceRegistry.ts` — `export.tablesToExcel` command 등록(execute가 ExportPort 위임).
- `ui/packages/runtime/src/createRuntime.ts`(또는 어댑터 합성부) — `export` Port 배선.

불변:
- `services.ts`(ServiceGroup 'export' 이미 존재), 기존 viewer/source Port.
