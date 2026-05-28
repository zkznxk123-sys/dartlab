---
id: engines.macro.cycles
title: Macro — 경기 사이클 (cycles)
category: engines
kind: curated
scope: builtin
status: observed
purpose: 경기 사이클 4 phase (회복·확장·후퇴·수축) 시계열 분류 SSOT — Kitchin (재고 3~5y) · Juglar (설비 7~11y) · Kondratiev (혁신 45~60y) 다층 사이클 어휘. macro cycle axis 의 phase 라벨 정의 + 다층 사이클 결합 패턴.
whenToUse:
  - 경기 사이클
  - cycle
  - 회복·확장·후퇴·수축
  - Kitchin
  - Juglar
  - Kondratiev
  - 사이클 phase
  - 재고 사이클
  - 설비 사이클
sourceRefs:
  - dartlab://skills/engines.macro.cycles
capabilityRefs:
  - macro
knowledgeRefs:
  - engines.macro
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: supported
  pyodide:
    status: limited
linkedSkills:
  - engines.macro
  - engines.macro.regimes
---

## 엔진 역할

`macro` 엔진의 *cycle phase* 어휘 SSOT. base SKILL `engines.macro` 의 `cycle` · `inventory` axis 결과 phase 라벨을 단일화. 다층 사이클 (Kitchin / Juglar / Kondratiev) 정의 + 결합 패턴.

regime 분류 (`engines.macro.regimes`) 와 직교 — cycle 은 *경기 변동 단위*, regime 은 *시장 상태 단위*. cycle phase 가 regime 분류의 1 차 입력.

## 공개 호출 방식

```python
import dartlab

# 1. 단기 사이클 (Kitchin 재고)
inv = dartlab.macro("inventory", market="KR")
# → 재고 사이클 phase + indicator

# 2. 일반 경기 사이클
cycle = dartlab.macro("cycle", market="KR")
# → 4 phase + indicator + dateRef

# 3. 미국 사이클
cycle_us = dartlab.macro("cycle", market="US")
```

## 호출 동작

본 spec 은 *어휘 정의* — 실제 분류는 `dartlab.macro("cycle"|"inventory")` 가 KR/US 시장 OECD CLI · 한은 BCI · ISM PMI 등 indicator 결합으로 phase 라벨링.

1. `cycle` axis (Juglar 설비 사이클 ~7-11y) → 4 phase (회복·확장·후퇴·수축).
2. `inventory` axis (Kitchin 재고 사이클 ~3-5y) → 4 phase 같음, 다른 indicator 기반.
3. 두 사이클 phase 가 다를 수 있음 — 단기/장기 사이클 위상차가 정보.
4. Kondratiev (~45-60y 혁신 사이클) 는 정성 분석 — 코드 axis 없음, narrative 만.

## 4 phase enum 정의

| phase | 한글 | indicator 특징 (KR 기준) | 자산 추세 참고 |
|---|---|---|---|
| **recovery** | 회복 | OECD CLI 100 이하 + 상승, PMI 50 이하 + 상승 | 주식 ↑ / 채권 → / 원자재 ↗ |
| **expansion** | 확장 | OECD CLI 100 이상 + 상승, PMI 50 이상 + 상승 | 주식 ↑ / 채권 ↓ / 원자재 ↑ |
| **slowdown** | 후퇴 | OECD CLI 100 이상 + 하락, PMI 50 이상 + 하락 | 주식 ↘ / 채권 ↑ / 원자재 ↘ |
| **contraction** | 수축 | OECD CLI 100 이하 + 하락, PMI 50 이하 + 하락 | 주식 ↓ / 채권 ↑ / 원자재 ↓ |

phase 전환 임계: CLI 100 분기점 + 1 차 미분 (3 개월 이동평균) 부호. 임계 변경 시 본 spec 갱신 필수.

## 다층 사이클 결합

| 사이클 | 주기 | dartlab axis | 사용 |
|---|---|---|---|
| Kitchin (재고) | 3~5 년 | `inventory` | 단기 trading regime |
| Juglar (설비) | 7~11 년 | `cycle` | 중기 자산배분 |
| Kondratiev (혁신) | 45~60 년 | 없음 (정성) | 장기 narrative (혁명·기술전환) |

권장: 답변 시 Juglar (`cycle`) phase 1 차 + Kitchin (`inventory`) phase 2 차 결합. 위상차 (Juglar 확장 + Kitchin 후퇴 등) 는 답변 narrative 의 핵심.

## 대표 반환 형태

```text
dartlab.macro("cycle", market="KR")
→ dict
   axis : str               # "cycle"
   market : str             # "KR" / "US"
   phase : str              # 4 enum (recovery/expansion/slowdown/contraction)
   phaseLabel : str         # 한글
   indicators : dict        # OECD CLI / 한은 BCI / PMI 등 + 값 + 1 차 미분
   dateRef : str            # YYYY-MM
   confidence : float       # 0.0 ~ 1.0
```

## 기본 실행 순서

1. **현재 cycle phase** — `dartlab.macro("cycle", market=...)` 결과의 `phase` 인용.
2. **재고 사이클 별도** — `dartlab.macro("inventory", market=...)` 호출.
3. **다층 결합 narrative** — Juglar phase + Kitchin phase 위상차 답변.
4. **regime 분류 입력** — 본 phase 가 `engines.macro.regimes` 의 1 차 신호.

## 기본 검증

- `phase` 값이 4 enum 안.
- 같은 market·dateRef 재호출 시 phase 동일.
- `inventory` phase 와 `cycle` phase 가 다를 수 있음 — 다층 사이클 정합 (위상차 정상).
- Kondratiev 단언 시 정성 단언 + 시장 단위 narrative 명시 (코드 분류 없음).

본 spec 은 공개 실행 문서다. phase enum 또는 임계가 변경되면 본 파일을 같은 변경에서 갱신한다.

## 관련

- [engines.macro](/skills/engines.macro) — base SKILL (12 axis)
- [engines.macro.regimes](/skills/engines.macro.regimes) — regime 5 enum (cycle phase 가 1 차 입력)
- [recipes.macro.qualityMacroBeta](/skills/recipes.macro.qualityMacroBeta) — phase × QMJ 결합
