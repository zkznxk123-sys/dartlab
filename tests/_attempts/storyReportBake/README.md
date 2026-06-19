# storyReportBake — 기업분석보고서 payload bake (_attempts)

PRD `mainPlan/company-analysis-report/` 의 **dev 구현**. story 엔진 산출을 퍼블릭 터미널용
단일문서 보고서 payload(JSON)로 굽는 직렬화기. 본진(`src/dartlab`) 미변경 — _attempts 단계.

## 무엇

`bakeStoryReport(code, bakedAt) -> dict | None`:
1. `buildStory(c, type="full", detail=True).render("json")` 로 base payload 획득.
2. 섹션 enrich — `getSectionMeta(key).act` → `act`/`actHeader`(catalog SSOT, PRD F1), `sourceEngine`(섹션→엔진 정적 맵), 표 단위 재스케일(`_rescaleManwon`), 모든 text/summary C-2 정화(`_cleanStr`), 빈/무의미 블록·차트·고아 heading 제거.
3. `evidenceFrame`(sixActScore — score 는 `_internalScore` 로 분리, NEVER-CLAIM 레이더 비노출) + `provenanceFrame`(실제 엔진 출처 집계 = 신뢰 가능한 정직 토대).
4. `narrativeOverview`(측정값 추출 + 신뢰 가능한 생애주기·피어) + `keyFindings`(판정어휘·환각 제거).
5. honest-skip reject-gate — 빈약 회사는 굽지 않고 `_skipped.json` 기록.

출력: `landing/static/story/report-{code}.json` → dev 라우트 `/lab/report` 가 fetch.

## 실행

```bash
POLARS_MAX_THREADS=2 MALLOC_ARENA_MAX=2 \
  uv run python -X utf8 tests/_attempts/storyReportBake/bakeStoryReport.py 005930 000660 035420
```

## 실측 결과 (2026-06-19)

| 회사 | 섹션 | act | 엔진 | bytes | label |
|---|---|---|---|---|---|
| 005930 삼성전자 | 9 | 1–6 | analysis | ~14.5KB | conditional |
| 000660 SK하이닉스 | 9 | 1–6 | analysis | ~14KB | conditional |
| 035420 NAVER | 9 | 1–6 | analysis | ~13.6KB | conditional |

- buildStory ~13초/회사(캐시 시). 9 재무분석 섹션(수익구조·성장성·수익성·현금흐름·안정성·자산구조·투자효율·가치평가·매출전망), 8개년 시계열·피어 백분위(~434사)·생애주기.
- ★전문에이전트 적대검증: 보고서 품질 47→68→**90**(신뢰도 킬러 박멸 — 단위버그 188조·환각 16.0%·모순 부채증가·판정어휘 C-2 정화·빈차트/판정/고아heading 제거), 완전성 **88**.
- ★★UI/UX + 기업분석 전문가 95점 라운드: **UI/UX 62→95**(방향성 컬러·인라인 스파크라인 0-baseline+endpoint dot·act 밴드+스파인 내비·섹션 엔진색 액센트·KPI 밴드·zebra·타입스케일) · **기업분석 88→93→95**(자기모순 파생값 드롭 FCF 0기/마진 contracting/피어 0%·영문→한글·부분결측 0% 둔갑 가드 `_guardMissingRatios`·일회성>100% 자동 플래그·변곡점 자동추출·강약점 채움). 잔여는 전부 본진(시변 WACC·None 전파 뿌리·정상화).

## 정직 한계 (실측)

- **단일 엔진**: fresh `Company` 경로에서 credit/quant/industry/macro 블록이 빈 반환 → provenance=analysis 만. `SECTION_SOURCE_ENGINE` 의 타 엔진 매핑은 해당 데이터 로드 시(P1 bake CI) 발동.
- **sixActScore evidenceFrame 빈약**: `c.insights=None`(분석 미수집) → 대부분 축 missing → provenanceFrame 으로 정직 대체.
- **상류 계산 잔여**(본진 미수정 원칙 = 범위밖): "FCF 양수 연속 0기", 2019 결측→0%, WACC 10% 고정 추정.

## 졸업 게이트 (본진 이관 전 선결)

본 디렉터리는 _attempts 단계. 본진 이관 시: block-level `sourceEngine`(catalog.BlockMeta 정적 필드, PRD 03 §4) · `representativeRceptNo`(간판5 딥링크) · storyValidation(plausibilityBand) 직렬화 · reject-gate 임계 spike 산출 · P1 bake CI 배선 필요. PRD 07문서 Phase 표 참조.
