---
id: engines.derivatives
title: Derivatives (KOSPI200 옵션 + 파생상품)
category: engines
kind: curated
scope: builtin
status: drafted
purpose: KOSPI200 옵션 시장 4 축 (IV surface · put-call skew · VKOSPI · risk-neutral density) + 파생상품 분석 엔진. **status=drafted — D-track KRX `opt` API 권한 인프라 선결**. 트리거 — '옵션', '파생', 'derivatives', 'KOSPI200 옵션', 'IV', 'VKOSPI'.
whenToUse:
  - 파생
  - derivatives
  - 옵션
  - KOSPI200 옵션
  - IV surface
  - put-call skew
  - VKOSPI
  - risk-neutral density
  - 옵션 flow
capabilityRefs: []
knowledgeRefs:
  - start.dartlabSkillOs
  - engines.quant
  - engines.macro
sourceRefs:
  - dartlab://skills/engines.derivatives
requiredEvidence:
  - target
  - axis
  - dateRef
  - executionRef
  - sourceRef
runtimeCompatibility:
  server:
    status: limited
  localPython:
    status: limited
  mcp:
    status: limited
  webAi:
    status: limited
  pyodide:
    status: limited
failureModes:
  - 데이터 인프라 미가용 (KRX `opt` API 권한 401 또는 미신청)
  - 옵션 만기·strike 격자 cross-day 비교 시 격자 시점 정렬 미적용
  - VKOSPI 등 지수 single 값 답변 시 dateRef 누락
forbidden:
  - 데이터 인프라 미가용 상태에서 IV/skew 숫자 답변 금지 — drafted spec 명시.
  - 옵션 단일 strike 답변에서 만기·strike 명시 누락 금지.
  - put-call skew 단방향 해석 금지 (skew ↑ = 하방 헷지 수요지 절대 매도 신호 X).
linkedSkills:
  - engines.quant
  - engines.macro
  - engines.derivatives.vkospi
  - engines.derivatives.putCallSkew
  - engines.derivatives.ivSurface
  - engines.derivatives.riskNeutralDensity
---

## 엔진 역할

`derivatives` 는 KOSPI200 옵션 시장 forward-looking 신호 4 축 + 파생상품 분석. 한국 시장 세계 최고 옵션 유동성인데 dartlab quant 엔진 0 축 (quantGap Tier 1) — 본 엔진이 그 구멍 메움.

**status=drafted**: KRX OpenAPI `opt` 카테고리 권한 + HF backfill (`krx/options/`) 인프라 선결. velvet-hatching-puffin 플랜 Phase 2.C D-track 완료 시 status → tested.

## 공개 호출 방식

```python
import dartlab

# 1. 단일 axis (D-track 활성 시)
iv = dartlab.derivatives("ivSurface", date="2026-05-28")
skew = dartlab.derivatives("putCallSkew", date="2026-05-28")
vkospi = dartlab.derivatives("vkospi", date="2026-05-28")
rnd = dartlab.derivatives("riskNeutralDensity", date="2026-05-28")

# 2. 가이드 (인자 없음)
guide = dartlab.derivatives()
# → 등록된 4 axis DataFrame
```

## 호출 동작

`derivatives(axis, date=, ...)` — KRX 옵션 일별 데이터 (`_hfBulk.loadFilteredOption`) 로드 + axis 별 계산. 모든 결과에 `dateRef` + `expiry` (옵션 만기) + `underlying` (기초자산) 동행.

## 대표 반환 형태

| axis | 반환 | 단위 |
|---|---|---|
| ivSurface | DataFrame (strike × expiry × IV) | IV % |
| putCallSkew | dict (25Δ skew + smile metrics) | IV pt |
| vkospi | dict (VKOSPI level + regime) | index |
| riskNeutralDensity | DataFrame (strike × density) | 확률 |

## 기본 검증

- D-track 활성 후: `derivatives()` 가이드 + `derivatives(axis)` 4 종 호출 정상.
- 모든 결과에 `dateRef` + `expiry` 동행.
- IV / skew / VKOSPI / RND 결과의 unit (% / IV pt / index / 확률) 명시.

본 spec 은 공개 실행 문서다. 4 axis 반환 구조 변경 시 본 파일 + sub-spec 동시 갱신.

## 관련

- [engines.quant](/skills/engines.quant) — quant 엔진 52 축 (옵션 4 축 신설 후 56 축)
- [engines.macro.regimes](/skills/engines.macro.regimes) — VKOSPI regime 분류
