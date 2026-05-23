# SLO — Service Level Objectives

> dartlab 의 서비스 수준 목표 4종. 측정 자동 (metrics workflow, T1-2) + burn alert (T1-4 후속).
> SLO burn 5% 초과 시 [INCIDENTS.md](INCIDENTS.md) 항목 자동 issue 생성.
> 1.0.0 출시 (목표 2027-02-28) 게이트 통과 기준: 4 SLO 모두 30일 ≥ 95%.

---

## SLO 1 — Company.show 정상 응답률

- **목표**: ≥ 95% / 30일 rolling
- **측정**: `tests/audit/companyShowSmoke.py` (예정) 가 7 종목 × daily 호출 → 성공/실패 count
- **error budget**: 5% × 30일 × 7 종목 × 1회/day = 약 10건/월
- **burn alert**: 30일 윈도우에서 누적 fail ≥ 7 시 GitHub issue 자동 + INCIDENTS 항목
- **데이터 소스**: metrics workflow (T1-2) 산출물 `landing/static/metrics/slo/companyShow.json`

### 정상 정의
- `Company("005930").corpName` 반환
- exception 0
- 응답 시간 ≤ 5초 (네트워크 변동 ±20%)

---

## SLO 2 — CI Fast 통과율

- **목표**: ≥ 90% / 30일 rolling
- **측정**: GitHub Actions `ci-fast.yml` workflow 결과 30일 집계
- **error budget**: 10% × 약 100 push/월 = 10 fail/월
- **burn alert**: 7일 윈도우 통과율 < 70% 시 알람
- **데이터 소스**: T1-2 metrics workflow 가 `gh api` 호출하여 산출

### 정상 정의
- exit code 0
- 모든 fast tier gate (12 개) 통과

---

## SLO 3 — HF dataset 동기화 성공률

- **목표**: ≥ 95% / 30일 rolling
- **측정**: `.github/workflows/sync-*.yml` (10+ workflow) 결과 집계 (DART/EDGAR/FRED/ECOS/Naver/KRX)
- **error budget**: 5% × 약 300 sync 실행/월 = 15 fail/월
- **burn alert**: 24h 안 동일 source 3회 연속 fail → 즉시 INCIDENTS + issue
- **데이터 소스**: T1-2 metrics workflow + T7-5 dataDriftCheck

### 정상 정의
- sync workflow exit 0
- HF upload 성공
- 데이터 row count baseline ±5σ 안

---

## SLO 4 — MCP server boot 성공률

- **목표**: ≥ 99% / 30일 rolling
- **측정**: `tests/run.py gate smoke` 안 MCP server import 시간 (P95) + tool call 첫 응답
- **error budget**: 1% (매우 엄격 — MCP 는 외부 LLM 진입점이라 첫 인상 결정)
- **burn alert**: 7일 윈도우 fail ≥ 1 시 알람 (단일 fail 도 critical)
- **데이터 소스**: T1-2 metrics workflow + smoke gate 결과

### 정상 정의
- import 후 5초 안 tool list 응답
- first tool call 응답 ≤ 10초
- exception 0

---

## 측정 파이프라인 (T1-2 + T1-4 통합)

```
GitHub Actions workflows
  ├─ ci-fast.yml (SLO 2)
  ├─ sync-*.yml (SLO 3)
  └─ ci-nightly.yml (SLO 1, SLO 4 smoke)
        │
        ▼
metrics.yml (workflow_run trigger, T1-2)
        │
        ├─ landing/static/metrics/slo/{name}.json (시계열, 30일 rolling)
        └─ landing/static/metrics/burnRate.json (실시간 burn %)
        │
        ▼
landing /health route (T1-5)
        ├─ SLO 4 종 sparkline
        └─ burn 5% 초과 시 INCIDENTS issue 자동 link
```

---

## error budget 정책

- **budget 50% 이내 소비**: 정상 운영. 신규 기능 추가 가능.
- **budget 50~80% 소비**: feature freeze 검토. 안정화 우선.
- **budget 80% 초과**: feature freeze 강제. 다음 minor release 까지 fix 만.
- **budget 100% 초과 (burn alert)**: INCIDENTS RCA 24h 안 + 재발 가드 박음.

---

## 관련

- [INCIDENTS.md](INCIDENTS.md) — 사고 기록 (T1-3)
- [RELEASE.md](RELEASE.md) — 1.0.0 게이트 항목 17 (SLO 4종 30일 ≥ 95%)
- [TODO.md](../TODO.md) — T1-4 트랙 + 1.0.0 게이트
- metrics workflow: `.github/workflows/metrics.yml` (T1-2 후속)
- 비교 벤치: anthropics/financial-services SLO 91 / Microsoft qlib SLO 95 / OpenBB SLO 90
