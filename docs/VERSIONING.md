# VERSIONING 정책

> dartlab 버전 체계와 호환성 약속. [Semantic Versioning 2.0](https://semver.org/spec/v2.0.0.html) 기반 + 추가 강제 룰.
> 짝 문서: [DEPRECATION.md](../DEPRECATION.md) (제거 정책), [RELEASE.md](RELEASE.md) (출시 체크리스트).

---

## 버전 형식

`MAJOR.MINOR.PATCH` 예: `0.10.2`

- **MAJOR**: 호환성 깨지는 변경 (현재 0.x 단계는 minor 증가가 같은 역할)
- **MINOR**: 호환되는 기능 추가 + deprecated 항목 제거 (0.x 한정)
- **PATCH**: 호환되는 버그 수정만

---

## 0.x 단계 룰 (현재)

**0.x 는 beta 단계**. minor 증가 시 *breaking change 가능*. 단:

1. breaking 변경은 **CHANGELOG 의 "Breaking" 섹션에 명시 강제**.
2. public API 제거는 [DEPRECATION.md](../DEPRECATION.md) 의 *3 minor notice* 룰 강제.
3. 매 minor 증가 시 외부 사용자 *마이그레이션 가이드* 필수.

### 0.x 의 release cadence

- minor: 2-4 주마다 (기능 추가 또는 deprecated 제거)
- patch: 무제한 (버그 fix 우선)

---

## 1.x 단계 룰 (목표 2027-02-28)

1.0.0 출시 후 **strict semver**. 변경 룰 강화:

| 변경 종류 | 1.x 룰 |
|----------|--------|
| public API 추가 | minor 가능 |
| public API 시그니처 변경 | major 필수 |
| public API 제거 | major 필수 + 6 minor notice 선행 |
| public API 동작 (semantic) 변경 | major 필수 |
| 버그 fix (semantic 보존) | patch |
| 의존성 버전 범위 확장 | minor |
| 의존성 버전 범위 축소 | major (사용자 환경 깨질 수 있음) |

### 1.x 의 LTS 보장

1.0.0 시리즈는 출시 후 **최소 12개월 보안 패치 보장** (critical CVE 대응).

### 1.x 의 release cadence

- minor: 2-3개월
- patch: 무제한

---

## 호환성 표

| 사용자 → | 현재 (0.x) | 1.x 출시 후 |
|---------|------------|-------------|
| 0.10.x 사용 중 | minor 마다 마이그레이션 검토 | 1.0.0 으로 한 번 마이그레이션 (큰 변경) |
| 1.0.x 사용 예정 | beta 종료까지 대기 가능 | 정상 운영 |
| LTS 필요 | 0.x 는 LTS 없음 | 1.x 시리즈 12개월 |

---

## 자동 검증

- `tests/audit/deprecationAudit.py` — DEPRECATION 항목 ↔ 코드 정합 (T8-1)
- `tests/audit/apiContractAudit.py` — public API 시그니처 변경 시 major bump 강제 (T8-5)
- `tests/audit/versionConsistency.py` (예정, T14-2 트랙) — pyproject.toml / __init__.py / CHANGELOG.md 의 버전 동기화

---

## 관련

- **현재 버전**: 0.10.2 (beta, dev status `4 - Beta` in pyproject.toml)
- **1.0.0 목표**: 2027-02-28 (KPI 평균 ≥ 91 + 14 관점 모두 ≥ 90, [TODO.md](../TODO.md) 부록 C 1.0.0 게이트)
- **CHANGELOG**: [../CHANGELOG.md](../CHANGELOG.md) (Keep a Changelog 1.1.0 형식)
- **PyPI**: https://pypi.org/project/dartlab/
- **LICENSE**: [Apache 2.0](../LICENSE)
