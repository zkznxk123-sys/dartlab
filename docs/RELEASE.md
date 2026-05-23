# RELEASE 체크리스트

> dartlab 의 출시 (PyPI publish) 절차서. 매 minor/major release 시 본 체크리스트 12 항목 모두 통과 강제.
> 1.0.0 출시 (목표 2027-02-28) 시 [TODO.md](../TODO.md) 부록 C 1.0.0 게이트 추가 통과 필수.

---

## 12 항목 체크리스트

### A. 코드 정합

- [ ] **1. CHANGELOG 갱신** — `CHANGELOG.md` 의 `[Unreleased]` 섹션이 출시 버전으로 close + Added/Changed/Deprecated/Removed/Fixed/Security 분류 완비
- [ ] **2. 27 게이트 (full tier) 통과** — `uv run python -X utf8 tests/run.py full` exit 0
- [ ] **3. benchmark baseline 안정** — `tests/audit/_baselines/benchmarks.json` 대비 P95 ±10% 안 (T3-1/T3-2 트랙)
- [ ] **4. eval suite 통과** — `pytest tests/_evals/ -v` exit 0 (T11-2 트랙, smoke + full 둘 다)

### B. 보안

- [ ] **5. CodeQL 0 critical** — 최근 7일 CodeQL workflow 결과 critical/high 0
- [ ] **6. pip-audit 0 critical** — `uv run python -X utf8 .github/scripts/ops/securityAudit.py` exit 0 (T2-2 blocking 트랙)

### C. 문서

- [ ] **7. docstring 9섹션 (public API) 100%** — `tests/audit/docstring9SectionAudit.py` 통과 (T10-4 트랙)
- [ ] **8. SECURITY/LICENSE/CHANGELOG/DEPRECATION/VERSIONING 최신** — 5 문서 마지막 갱신 ≤ 30일 + 출시 버전 정합

### D. 배포

- [ ] **9. PyPI test 업로드 + 설치 검증** — `test.pypi.org/dartlab/{version}` 업로드 후 clean env `pip install -i https://test.pypi.org/simple/ dartlab=={version}` 통과
- [ ] **10. PyPI 본 업로드** — `twine upload dist/*` 또는 release workflow OIDC (T14-4)
- [ ] **11. GitHub Release notes 작성** — `gh release create v{version}` + body = CHANGELOG 의 해당 섹션 복제
- [ ] **12. landing dashboard + 공지** — `landing/static/metrics/` 시계열 갱신 + SNS 공지 (T12 트랙)

---

## 자동화

### release.yml workflow (T14-4)

git tag `v*.*.*` push 시 본 체크리스트 자동 단계:

```yaml
on:
  push:
    tags: ["v[0-9]+.[0-9]+.[0-9]+"]
jobs:
  release:
    steps:
      - 27 게이트 full
      - benchmark baseline
      - eval suite
      - wheel build
      - test.pypi 업로드 + smoke install
      - pypi 본 업로드 (OIDC trusted publisher)
      - gh release create
      - landing metrics 갱신 trigger
```

### release-readiness gate (T14-1)

PR 마지막에 수동 trigger 가능. 본 체크리스트 항목 1-8 자동 검증 (9-12 는 manual + release.yml).

---

## 1.0.0 게이트 추가 항목

1.0.0 출시는 본 12 + 추가 6 항목 모두 통과 (TODO.md 부록 C):

| # | 게이트 | 측정 |
|---|--------|------|
| 13 | 14 KPI 평균 ≥ 91 | worldClassScorecard.py |
| 14 | 모든 관점 ≥ 90 | 동상 |
| 15 | test/prod LOC ≥ 80% | testLocRatio.py (T6-5) |
| 16 | mutation ≥ 80% (30 모듈) | mutmut results (T6-2) |
| 17 | SLO 4종 30일 ≥ 95% | metrics workflow (T1-2/T1-4) |
| 18 | INCIDENTS 6개월 0 critical | INCIDENTS.md grep (T1-3) |

---

## 출시 실패 시 롤백

- PyPI: `pip install dartlab=={prev_version}` 강제, 본 버전 yank (`pip yank dartlab=={broken_version}`)
- HF dataset: 영향 없음 (별도 트랙)
- landing: 이전 commit 으로 revert
- INCIDENTS.md 항목 추가 + 24h 안 RCA

---

## 관련

- [DEPRECATION.md](../DEPRECATION.md) — 제거 정책
- [VERSIONING.md](VERSIONING.md) — SemVer + LTS
- [CHANGELOG.md](../CHANGELOG.md) — 변경 이력
- [TODO.md](../TODO.md) — 14 KPI 트래커 + 1.0.0 게이트
- 출시 권한: PyPI maintainer + GitHub release 권한 (Owner 또는 trusted publisher OIDC)
