---
id: engines.flow
title: Flow (공매도·대차·프로그램매매 KR 특화)
category: engines
kind: curated
scope: builtin
status: drafted
purpose: 한국 시장 flow factor 5 축 (공매도 잔고 · 대차잔고 · 프로그램매매 · 외국인/기관/개인 매매 · 블록딜) 엔진. quantGap Tier 1 미보유 영역. **status=drafted — KRX/금투협 보조 데이터 수집 인프라 선결**.
whenToUse:
  - flow
  - 공매도
  - 대차잔고
  - 프로그램매매
  - 외국인 매수
  - 기관 매수
  - 블록딜
  - flow factor
capabilityRefs: []
knowledgeRefs:
  - start.dartlabSkillOs
  - engines.quant
sourceRefs:
  - dartlab://skills/engines.flow
requiredEvidence:
  - target
  - flowType
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
forbidden:
  - 공매도 잔고 단방향 해석 금지 (단기 헷지·차익거래·인덱스 차익 등 사유 다양).
  - 외국인 매수 = 상승 신호 X (lag 큼, 학술 alpha 약).
linkedSkills:
  - engines.quant
  - engines.flow.shortInterest
  - engines.flow.programTrade
  - engines.flow.securitiesLending
---

## 엔진 역할

KR 시장 flow factor 엔진. 한국 시장 고유 데이터 (KRX 공매도 잔고 · 한국예탁결제원 대차잔고 · 금투협 프로그램매매 · KRX 투자자별 매매) 5 축 합성. quantGap Tier 1 미보유 영역 — D-track 인프라 완료 시 quant 52 축 → 57 축.

## 공개 호출 방식

```python
import dartlab
sl = dartlab.flow("shortInterest", code="005930")
pt = dartlab.flow("programTrade", date="2026-05-28")
inv = dartlab.flow("investorBalance", code="005930", days=30)
```

## 호출 동작

KRX OpenAPI + 금투협 / 예탁원 보조 endpoint 일별 데이터. 5 axis 별 별도 계산 + flow z-score (252 일 baseline).

## 대표 반환 형태

axis 별 DataFrame 또는 dict. 공통 `flowZ` (252 일 z-score) + `dateRef` 동행.

## 기본 검증

- 5 axis 별 반환에 `flowZ` (252 일 z-score) 동행.
- 단방향 해석 회피 — regime / z 동시 인용.
- 데이터 인프라 미가용 시 status=drafted 명시.

## 관련

- [engines.quant](/skills/engines.quant) — flow factor 흡수 시 53 축
- [engines.flow.shortInterest](/skills/engines.flow.shortInterest)
- [engines.flow.programTrade](/skills/engines.flow.programTrade)
