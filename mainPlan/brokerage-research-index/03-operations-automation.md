# 03 — 운영 자동화 (Operations Automation) 정본

> "수집해 놓고 끝"이 아니라 **방치해도 안 썩는 인덱스**를 만든다. 정본 오케스트레이션 = `dartlab.pipeline`(별도빌드 금지). 기존 레일을 100% 재사용하고, **신규 인프라는 §4 "깨짐 감지" 하나뿐**(기존 부재 — 스크래핑 용례의 최대 리스크).

## 0. 원칙

- brokerageReports = `dartlab.pipeline` **새 stage 1개**로 등록. GitHub Actions 워크플로는 stage **호출만**(스크랩·파싱 로직 재구현 금지 — CLAUDE.md ⛔ 공동작업대 SSOT).
- 재사용(신설 0): cron 워크플로 골격 · registry · changed manifest · `hfUpload` · circuit breaker · quota tracker · telemetry 채널.
- 본문 다운로드 없음 — allFilings 와 달리 **메타만** 수집(Phase 2 가 본문 fetch 가 아니라 ticker 해소). 가볍고 빠름.

## 1. Pipeline Stage 등록 (정본 진입점)

```
src/dartlab/pipeline/stages/brokerageReports.py
  def runBrokerageReports(*, category, mode, codes, upload, token) -> StageResult

src/dartlab/pipeline/registry.py  (StageSpec 추가)
  StageSpec("brokerageReports",
            run=brokerageReports.runBrokerageReports,
            uploadCategories=("brokerageReports",),
            label="증권사 리서치 메타 (일별 증분)")
```

- `mode`: `"recent"`(증분 날짜윈도) · `"full"`(과거 백필) · `"reconcile"`(갭 메움). allFilings stage 의 recent/full/backfill 패턴 동형.
- **RECENT_SET 합류는 보류** — 초기엔 독립 stage(`dartlab.pipeline brokerageReports`), 수율 안정화 후 `RECENT_SET` 합류 판단.
- 실행 = 로컬·CI **동일 명령**: `uv run python -X utf8 -m dartlab.pipeline brokerageReports`.
- 실패 격리 = `StageResult.report.failures` 누적, 다른 stage 안 죽인다(orchestrator 패턴).

## 2. 수집 라이프사이클 (3 Phase · allFilings 동형)

| Phase | 동작 | 산출 |
|---|---|---|
| **1. 메타 수집** | 증권사별 게시판 list 페이지 파싱 → 제목·url·날짜·증권사·report_type | `{YYYYMM}_meta` 행 |
| **2. ticker 해소** | 제목 → `gather/dart/corpCode.py` 매퍼 (실패 시 null) | `ticker` 컬럼 |
| **3. HF push** | `dist/changed_brokerageReports.txt` → batch commit (300파일/commit) | HF parquet |

- **파티션 키**: `pub_date` 월별(YYYYMM). **dedup**: `report_id`(url 해시) — 재수집 idempotent.
- **증분 윈도**: `BROKERAGE_LOOKBACK_DAYS`(기본 7). recent 모드는 최근 N일만 재파싱 → 신규 url 만 changed manifest 적재.

## 3. Cron 스케줄

- **워크플로**: 신규 `.github/workflows/brokerageSync.yml` (또는 `dataSync.yml` job 추가). 기존 워크플로 골격 복제.
- **주기**: 일 2회 권장 — **KST 08:00**(조간 리포트) + **KST 19:00**(장 마감 후 당일 리포트). cron UTC 환산(23:00, 10:00 UTC).
- **concurrency group**: `hf-research-push` (DART/EDGAR push 그룹과 분리 → 동시 허용·취소연쇄 방지).
- **timeout**: 30~45분(메타만이라 경량). `workflow_dispatch` 로 수동 백필(full/reconcile).
- **회복**: idempotent HF push — 실패해도 다음 run 자연 회복, 영구 실패상태 없음.

## 4. 깨짐 감지 (신규 설계 — 이 PRD 운영 핵심)

스크래핑이라 **HTML 셀렉터·게시판 구조 변경이 최대 운영 리스크**. 기존 circuit breaker 는 "연속 예외"만 잡고 **"200 OK + 0행"(조용한 깨짐)을 못 잡는다.** 그래서 stage 안에 경량 health 체크를 둔다:

1. **수율 가드(yield guard)** — 증권사별 일간 신규행 수를 baseline(직전 14일 중앙값) 대비. 평소 N건/일인데 **0건 또는 임계 이하** → 깨짐 의심.
2. **파싱 성공률** — 필수 필드(`title`·`url`·`pub_date`) non-null 비율 < 임계(예 90%) → 셀렉터 변경 신호.
3. **자가치유 액션** — 깨진 증권사를 자동 `enabled=False` 강등(**전체 stage 는 계속**) + `StageResult.failures` 기록 + GitHub Step Summary 경고. 운영자가 `config.py` selector 고치고 재활성.
4. **구현 최소** — stage 안 함수 + 기존 `telemetry.emit`(`gather:fetch:done` 패턴) 재사용. 새 모니터링 인프라 신설 금지.

> **구현됨 v1 (`664e8b50c`)**: `_detectBroken` — enabled 0행 증권사 stdout 경고(단순).
>
> **구현됨 v2 (헬스 게이트, 2026-06-27)**: `_detectBroken` → **`fetch.py::_healthProblems(catCounts, completeness, enabledCats, minCompleteness=0.9)`** 로 격상. 3 신호 감지: (1) **증권사 전체 0행**(전 report_type 합=0 → 사이트 차단/다운/전체 셀렉터 깨짐) (2) **카테고리별 0행**(증권사는 살아있으나 특정 보드 0 → 그 URL/셀렉터 깨짐. 단 **동적 report_type 브로커**[NH=행별 p.sort 재라벨]는 `dynamicReportType:True` 로 카테고리별 검사 생략·총량만 → 오탐 방지) (3) **파싱 완전성 < 90%**(필수필드 title·url·pub_date non-empty 비율 → 부분 셀렉터 깨짐). `syncBrokerageReports.py` 가 **업로드 후**(건강 데이터 보존) 헬스 판정 → **GitHub Step Summary 에 증권사×카테고리 수율·완전성 표 + 깨짐 사유** write + 깨짐이면 **`::error::` 주석 + exit 1 → 워크플로 RED → GitHub 가 운영자에게 자동 메일 알림**. 로컬=Step Summary env 부재라 stdout 만. *수율 baseline 대비(14일 중앙값)·자동 enabled=False 강등*은 후속(현재는 0행/완전성 임계 판정 — 보드는 항상 최신 N 반환이라 0=깨짐 신뢰 가능).

> 이게 "URL만 관리하면 된다"의 실제 운영 보장 — selector 가 깨지면 **시스템이 먼저 알려준다**, 사용자가 빈 화면 보기 전에.

## 5. Freshness / as-of 노출

- `collectedDates()` / `stats()` 동형 API — 증권사별 **최신 수집일 · 커버리지 N · 깨짐 상태** 노출.
- `dataConfig` 메타 또는 `_meta` 행에 as-of. 터미널 레일 라벨 = "as-of YYYY-MM-DD · N개사 · M건"(정기보고서 도시에 as-of 리본 패턴 재사용).
- **결측 first-class** — 미수집/깨진 증권사 = `—`, 절대 0-fill 금지.

## 6. 운영자 알림

- **1차**: GitHub Step Summary(워크플로 끝 요약 — 수집 N건 · 강등된 증권사 list · 수율 이상). 기존 dataSync 패턴.
- **2차(선택)**: 깨짐 임계 초과 시만 알림. 기존 채널 있으면 재사용, 없으면 Step Summary 로 충분 — **과설계 금지**([[feedback_always_check_clutter]]).

## 7. 가드 (CLAUDE.md ⛔)

- **별도빌드 금지**: 워크플로/스크립트는 stage 호출만, 스크랩 로직은 gather source.
- **online sync 전용**: brokerageReports 는 sync(외부→HF), prebuild(offline) 단계 **없음** → `enforceOffline()` 무관.
- **테스트**: `bash tests/test-lock.sh` 경유(Polars OOM 가드). **UTF-8**: `-X utf8`.
