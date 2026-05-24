# builders.py 분해 계획 (T9-5)

> 6111 줄 + 181 함수/클래스 monolithic 분해 트랙. story 엔진의 가장 큰 god module.
> 본 문서는 *계획만* — 실제 분리는 별도 PR (3 commit).
> [TODO.md](../../../TODO.md) T9-5 추적.

---

## 현재 구조 (2026-05-24)

```
src/dartlab/story/
├── builders.py         # 6111 줄, 181 함수/클래스
├── catalog.py
└── ...
```

`builders.py` 안 함수 분류 (grep + 본문 검토 결과):

| 분류 | 함수 갯수 (추정) | 예시 |
|------|----------------|------|
| **profile / segment** | ~15 | `profileBlock` / `segmentCompositionBlock` / `segmentTrendBlock` / `breakdownBlock` |
| **revenue / growth** | ~12 | `revenueGrowthBlock` / `concentrationBlock` / `revenueQualityBlock` / `growthContributionBlock` |
| **capital / debt** | ~18 | `capitalOverviewBlock` / `capitalTimelineBlock` / `debtTimelineBlock` / `interestBurdenBlock` |
| **liquidity / cash** | ~14 | `liquidityBlock` / `cashflowBlock` / `workingCapitalBlock` |
| **margin / profitability** | ~16 | (TODO grep) |
| **risk / governance** | ~12 | (TODO grep) |
| **technical / market** | ~14 | (TODO grep) |
| **utility / helper** | ~80 | `_notesDetailBlocks` / `_unitForCurrency` / `_fmtAmtShort` / `_quarterlyRevenueTable` |

---

## 분해 전략

### 옵션 A — 토픽별 (권장)

```
src/dartlab/story/builders/
├── __init__.py         # facade — 기존 builders.py 의 모든 심볼 re-export
├── _helpers.py         # _notesDetailBlocks / _unitForCurrency / _fmtAmtShort (80 함수)
├── profile.py          # profile / segment (15 함수)
├── revenue.py          # revenue / growth (12 함수)
├── capital.py          # capital / debt (18 함수)
├── liquidity.py        # liquidity / cash (14 함수)
├── margin.py           # margin / profitability (16 함수)
├── risk.py             # risk / governance (12 함수)
└── technical.py        # technical / market (14 함수)
```

- 각 파일 ≤ 1000 줄 (현재 6111 → 평균 ~750)
- 사용자 영향 0 — facade `__init__.py` 가 기존 `from dartlab.story.builders import X` 호환
- 분해 commit 3 단계: (1) `_helpers` 분리 (2) 5 토픽 분리 (3) builders.py 폐기 + facade

### 옵션 B — 8 막 (story analysis 정합)

```
src/dartlab/story/builders/
├── 1_hook.py
├── 2_setup.py
├── 3_confrontation.py
├── ...
└── 8_close.py
```

- 8 막 분류는 *story.compose* 의 8 막 인과 트랙과 정합
- 단점: 같은 *재무 helper* 가 여러 막에서 호출되어 helper 중복 또는 cross import 발생 위험

→ **권장: 옵션 A (토픽별)**. 8 막 인과는 `compose.py` 에 두고 builders 는 단순 토픽 분류.

---

## 분해 commit 단위 (3 commit)

### Commit 1 — `_helpers` 분리 (이전 명령 검증)

- `src/dartlab/story/builders/_helpers.py` 신설 (80 함수 ≤ 2000 줄)
- `builders.py` 는 그대로 + `from ._helpers import *` 만 추가
- 27 게이트 통과 + import-linter contract 갱신

### Commit 2 — 5 토픽 분리

- `profile.py` / `revenue.py` / `capital.py` / `liquidity.py` / `margin.py` 등 신설
- 각 토픽 함수 이동 (15-18 함수씩)
- `builders.py` 안 함수 정의 제거 + `from .topic import *`

### Commit 3 — `builders.py` 폐기 + facade

- `builders.py` → `builders/__init__.py` 로 이전
- 기존 import 호환 유지 (deprecated 표시 + `DartlabDeprecationWarning` 안 띄움 — facade 라)
- 9 게이트 통과 + audit 검증

---

## 회귀 위험 + 대응

| 위험 | 대응 |
|------|------|
| 함수 이동 시 import cycle | 분류 시 helper / specific 분리 (helper 가 specific 호출 금지) |
| `from dartlab.story.builders import X` 호환 깨짐 | facade `__init__.py` 가 모든 심볼 re-export |
| 27 게이트 일시 fail | 각 commit 후 `tests/run.py preflight` 통과 보장 |
| import-linter contract 갱신 누락 | builders 의 하위 contract 추가 (story.builders.*) |

---

## 측정

- 분해 전: `tests/audit/moduleSizeAudit.py` 격차 ~92x (providers 73K vs channel 791)
- 분해 후 목표: story 안 max 파일 ≤ 1000 줄 (현재 6111 → 약 8 파일)

---

## 관련

- [TODO.md](../../../TODO.md) T9-5 트랙
- [src/dartlab/skills/specs/operation/architecture.md](../skills/specs/operation/architecture.md) — L3 story 위치
- [tests/audit/moduleSizeAudit.py](../../../tests/audit/moduleSizeAudit.py) (T9-4) — 격차 측정
