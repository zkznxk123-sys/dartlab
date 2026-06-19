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

### ★★★ 보고서 문법 전환 + 95점 라운드 (2026-06-19, 적대검증 5R: 78→96/96)

운영자 거부("1막 2막 이건 왜하지? 진짜 보고서처럼") → 참조 HTML(`Downloads/경영성과 보고서`) 문서 문법 채택.
- **막(act) 구조 화면 폐기** → 표지(표제지 facts)·핵심요약(KPI밴드)·목차·**제목 섹션**(도메인 큰제목+질문 부제, " -- " 분리)·근거출처·서명푸터. UI 다크/화이트 토글 + A4 `@media print`.
- **UI/UX 78→86→88→92→96**: 6막 어휘 제거(라벨 오버라이드)·표제지화·인쇄 색보존(print-color-adjust)·다크 zebra/괘선·KPI 6칸 정렬·핵심발견 출처 컬럼 collapse·conclusion 압축·**스파크 추세색 시간순 정렬**(컬럼 신구순 혼재 무관·음수계열 중립색)·표 컬럼 오름차순 통일(`_sortYearCols`)·받침 동적 조사(을/를).
- **기업분석 78→88→82→88→96**: ★**ROIC−WACC 헤드라인=투자효율 표 측정 Spread(SSOT) 최신값 단일화**(삼성 -0.1·SK +19.8·NAVER -0.3%p, 헤드라인↔표 12/12 일치)·가치평가 metrics ROIC-WACC 칩 드롭·**표-텍스트 부호 모순 가드**(FCF "음수" 단정 vs 표 양수 / "ROIC≈WACC 수렴" enum vs Spread 5년음수 = 둘 다 표 부호 보고 제거)·마크다운/영문 enum/판정 프로즈 정화·NAVER 매출총이익률 결측 명시 고지·`_latestFromTables` max-year 보정.
- 두 전문가 최종: **표-텍스트 모순 화면 0건**. 잔여 = [본진] sixActScore evidenceFrame 빈약(provenanceFrame 대체)·생애주기 enum 템플릿이 측정값 미분리(케이스별 정규식 사후정화 = 구조 부채).

### ★★★★ 다엔진 완성형 + S급 (2026-06-19, 적대검증 78→A+→**S/S 96·96**)

운영자 goal: 단일엔진→다양한 데이터 완성형 + 터미널 보고서 버튼 + S급. 단일엔진(analysis)→**4엔진**(재무+신용+산업+시장):
- **신용분석(credit)**: `calcCreditScore` 등급(dCR-AA)·7축 가중치·핵심 신용지표(그룹·단위)·부도확률·현금흐름등급(eCR)·감사의견
- **산업비교(industry)**: `calcChainPosition`+`calcSectorMetrics` 가치사슬 위치·동종 N개사 백분위(영업이익률/CAGR/ROE)·동일공정 peers
- **시장주가(quant)**: `calcMarketBeta` 베타·CAPM·상대강도·R² (NEVER-CLAIM: 매수/매도/목표가 0)
- **종합 의견(closing)**: 재무/신용/산업/시장 4엔진 각 1줄 수렴 — 참조 보고서 회계사 종합의견 문법, 문서가 닫힘
- 결과: provenanceFrame 4엔진·**label=verified**·12섹션

**핵심 함정 2개(실측 해결)**:
- ① 엔진 calc은 buildStory **전** 호출 필수(buildStory 가 HTTP 클라이언트 닫음). ② credit/quant calc 이 *모듈 전역 상태*를 변형 → 같은 프로세스 buildStory 가 본진 `story/summary.py:147` ' / '.join tuple 버그(NAVER 등)를 밟음 → **엔진 섹션을 자식 프로세스로 격리**(`_engineSectionsIsolated`, `--engine-only` 모드)해 회피(본진 미변경).

**전문가 적대검증 라운드**(분석/UI): 78→88/92→82/88(FCF 본문 잔존)→88/92→93/95→**S 96 / S 96**. 정합 수정: 신용 단위(%/배)+레버리지/커버리지/유동성 그룹핑·왜곡 이자보상(금융비용 fallback) 제외·부채비율 안정성 소유(신용표 드롭)·그룹 컬럼 시각 병합·산업 백분위 단일화(상위 N%)·narrativeOverview 유니버스 충돌 제거·NAVER 매출총이익률 명시.

**실행(회사당 별도 프로세스 = OOM 가드 부합)**:
```bash
for code in 005930 000660 035420; do
  POLARS_MAX_THREADS=2 MALLOC_ARENA_MAX=2 uv run python -X utf8 \
    tests/_attempts/storyReportBake/bakeStoryReport.py $code
done
```
터미널: `ui/.../terminal/TerminalSurface.svelte` 헤더 `보고서` 버튼(amber) → `/lab/report?sym={code}` 새 탭(인쇄). svelte-check(landing·surfaces) 0err. **push = 운영자 UI 승인 대기.**

## 정직 한계 (실측)

- **단일 엔진**: fresh `Company` 경로에서 credit/quant/industry/macro 블록이 빈 반환 → provenance=analysis 만. `SECTION_SOURCE_ENGINE` 의 타 엔진 매핑은 해당 데이터 로드 시(P1 bake CI) 발동.
- **sixActScore evidenceFrame 빈약**: `c.insights=None`(분석 미수집) → 대부분 축 missing → provenanceFrame 으로 정직 대체.
- **상류 계산 잔여**(본진 미수정 원칙 = 범위밖): "FCF 양수 연속 0기", 2019 결측→0%, WACC 10% 고정 추정.

## 졸업 게이트 (본진 이관 전 선결)

본 디렉터리는 _attempts 단계. 본진 이관 시: block-level `sourceEngine`(catalog.BlockMeta 정적 필드, PRD 03 §4) · `representativeRceptNo`(간판5 딥링크) · storyValidation(plausibilityBand) 직렬화 · reject-gate 임계 spike 산출 · P1 bake CI 배선 필요. PRD 07문서 Phase 표 참조.
