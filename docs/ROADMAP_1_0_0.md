# Roadmap to 1.0.0 — 2027-02-28 목표

> dartlab 의 *beta → stable* 전환. [TODO.md](../TODO.md) 부록 C 1.0.0 게이트 + 본 ROADMAP 의 분기 마일스톤 통합.
> 짝 문서: [RELEASE.md](RELEASE.md) (12 체크리스트), [VERSIONING.md](VERSIONING.md) (0.x → 1.x 정책), [DEPRECATION.md](../DEPRECATION.md) (3 minor notice).

---

## 1.0.0 출시 게이트 (정량 + 정성)

### 정량 게이트 8 항목

| # | 게이트 | 측정 | 현재 |
|---|--------|------|------|
| 1 | 14 KPI 평균 ≥ 91 | `tests/audit/worldClassScorecard.py` | 67.6 (2026-05-23 baseline) |
| 2 | 모든 관점 ≥ 90 | 동상 | 운영 44 / 보안 52 가 최저 |
| 3 | test/prod LOC ≥ 80 percent | `tests/audit/testLocRatio.py` | 25 percent (2026-05-24) |
| 4 | mutation score ≥ 80 percent (30 모듈) | `mutmut results` | 3 모듈만 운영 중 |
| 5 | 커버리지 ≥ 70 percent | `coverage.py` xml | 약 40 percent (omit 33 percent) |
| 6 | SLO 4종 30일 ≥ 95 percent | metrics workflow (T1-2/T1-4) | 측정 0 (workflow 미가동) |
| 7 | benchmark baseline 5 시나리오 ±10 percent | T3-1/T3-2 | 시나리오 0 |
| 8 | CI Fast 통과율 30일 ≥ 90 percent | metrics workflow | 측정 0 |

### 정성 게이트 5 항목

| # | 게이트 | 측정 |
|---|--------|------|
| 9 | INCIDENTS.md 6개월 0 critical | `docs/INCIDENTS.md` grep |
| 10 | DEPRECATION.md 모든 deprecated 항목 정합 | `tests/audit/deprecationAudit.py` (T8-1) |
| 11 | public API docstring 9섹션 100 percent | `tests/audit/docstring9SectionAudit.py` (T10-4) |
| 12 | 외부 기여자 첫 PR 시도 성공률 ≥ 80 percent | GitHub PR 통계 + CONTRIBUTING.md 정합 |
| 13 | 사용자 사례 3 종 검증 | `docs/CASE_STUDIES.md` (T12-4) |

---

## 분기 마일스톤

### Q2 (2026-06 ~ 2026-08) — 약점 클러스터 깨기

**평균 67.6 → 76.6 (+9 점)** — 운영 / 보안 / 성능 / 확장성 / DX 클러스터.

핵심 트랙:
- 운영 44 → 65 (T1-1 ~ T1-5)
- 보안 52 → 72 (T2-1 ~ T2-5)
- 성능 62 → 78 (T3-1 ~ T3-3)
- 확장성 65 → 75 (T5-1 / T5-3 / T5-4)
- DX 64 → 72 (T4-1 ~ T4-4)

병행:
- CI/CD 78 → 84 (T13-1 / T13-3)
- 거버넌스 78 → 84 (T14-1 / T14-3)

**Q2 종료 시 점검**: 2026-08-31 worldClassScorecard 실행 + memory 시계열 갱신.

### Q3 (2026-09 ~ 2026-11) — 중급 정합 다지기

**평균 76.6 → 83.6 (+7 점)**

핵심 트랙:
- 테스트 75 → 85 (T6-1 hypothesis 20× + T6-2 mutmut 30 + T6-3 metamorphic 5)
- 확장성 75 → 82 (T5-2 plugin example + T5-5 introspection)
- API 74 → 82 (T8-1 ~ T8-5)
- 데이터 76 → 84 (T7-1 ~ T7-5)
- 운영 65 → 78 (T1-5 dashboard 공개)

### Q4 (2026-12 ~ 2027-02) — 최상위 도약

**평균 83.6 → 89.6 (+6 점)**

핵심 트랙:
- 아키텍처 84 → 90 (T9-1 providers 분해 + T9-2 importlinter 50 이하 + T9-3 SCC strict)
- 문서 85 → 90 (T10-1 다이어그램 + T10-4 9섹션 100 percent)
- DX 80 → 86 (T4-5 / T4-6)
- 1.0.0 게이트 통과 준비 (T14-2 / T14-4 / T14-5 완료)

### 출시 (2027-02-28)

**평균 89.6 → 91.7 (1.0.0 후보)**

체크리스트 ([RELEASE.md](RELEASE.md) 12 항목 + 본 ROADMAP 13 게이트) 모두 통과.

---

## 출시 후 (1.x 시리즈)

- **1.x release cadence**: 2-3 개월 minor / 무제한 patch
- **LTS 보장**: 1.0.0 시리즈 12 개월 보안 패치
- **API 호환성**: strict semver — public API 시그니처 변경 시 major bump
- **deprecated 제거**: 6 minor notice 선행 ([DEPRECATION.md](../DEPRECATION.md) 1.x 룰)

---

## 위험 / 비상 시나리오

| 위험 | 대응 |
|------|------|
| Q2 운영 클러스터 미달 (44 → < 65) | metrics workflow 우선 가동 → 측정 시작 후 1 month 안 catch-up sprint |
| benchmark 시나리오 5 종 baseline 수립 실패 | Q3 로 이동 + warn-only 게이트 유지 |
| 외부 기여자 PR 흐름 막힘 | CONTRIBUTING.md 5 시나리오 self-test + PR template 보강 |
| 1.0.0 출시 일정 슬립 | 정량 게이트 우선 → 정성 게이트는 1.1.0 까지 grace period |

---

## 진행 추적

- **세션 간 시계열**: `memory/project_plan_world_class.md` (운영자↔AI 약속)
- **공개 진척**: [TODO.md](../TODO.md) 부록 E 매트릭스 + [CHANGELOG.md](../CHANGELOG.md) Unreleased
- **분기 점검**: worldClassScorecard 실행 + 본 ROADMAP "분기 마일스톤" 섹션 갱신
- **외부 visibility**: [INCIDENTS.md](INCIDENTS.md) + [SLO.md](SLO.md) + 향후 [/health dashboard](../landing/) (T1-5)

---

## 관련

- [RELEASE.md](RELEASE.md) — 매 minor/major 출시 체크리스트
- [VERSIONING.md](VERSIONING.md) — 0.x → 1.x 정책
- [DEPRECATION.md](../DEPRECATION.md) — API 제거 3 minor notice
- [TODO.md](../TODO.md) — 14 KPI 부록 E 매트릭스 + 70 T 단위
- [CHANGELOG.md](../CHANGELOG.md) — Keep a Changelog 1.1.0
