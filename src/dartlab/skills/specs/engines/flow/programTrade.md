---
id: engines.flow.programTrade
title: Flow — 프로그램매매 (programTrade)
category: engines
kind: curated
scope: builtin
status: drafted
purpose: 프로그램매매 일별 imbalance (매수 - 매도 / 거래량) + 차익거래 vs 비차익거래 분리. KRX 프로그램매매 통계 SSOT. **status=drafted — KRX `prog` 카테고리 인프라 선결**.
whenToUse:
  - 프로그램매매
  - program trade
  - 차익거래
  - 비차익거래
  - imbalance
capabilityRefs: []
knowledgeRefs:
  - engines.flow
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
linkedSkills:
  - engines.flow
---

## 엔진 역할

프로그램매매 일별 imbalance — 인덱스 차익거래 (현물 매수 + 선물 매도 또는 역) vs 비차익거래 분리. 차익거래는 시장 mispricing 신호, 비차익은 패시브 flow.

## 공개 호출 방식

```python
import dartlab
pt = dartlab.flow("programTrade", date="2026-05-28")
# → dict: arbitrageNet · nonArbNet · totalImbalance · z252
```

## 호출 동작

KRX 프로그램매매 endpoint → 일별 매수/매도 + 차익/비차익 분리. 시장 wide + KOSPI200 우선.

## 대표 반환 형태

```text
dict
  arbitrageNet : int          # 차익거래 net (매수 - 매도, 백만원)
  nonArbNet : int             # 비차익거래 net
  totalImbalance : int
  z252 : float
  dateRef : str
```

## 기본 검증

- arbitrageNet + nonArbNet = totalImbalance (분해 정합).
- 단위 백만원 명시.
- z252 단위 σ (정규화).

## 관련

- [engines.flow](/skills/engines.flow) — base SKILL
