---
id: recipes.screen.peerBenchmark
title: peer 벤치마크 (산업 + 횡단 비교 + ratio)
category: recipes
kind: recipe
scope: builtin
status: unverified
purpose: 회사를 같은 산업 peer 5~10 종과 핵심 ratio (수익성/안정성/성장성/valuation) 4 축으로 벤치마크하는 절차. 트리거 — 'peer 비교', '동종 5~10 종 벤치마크', 'ratio 4 축'.
whenToUse:
  - peer 비교
  - 동종 비교
  - 벤치마크
  - 같은 업종 비교
  - peer benchmark
  - 동일 산업 비교
  - peer 5종
linkedSkills:
  - engines.company.researchStarter
  - engines.industry
  - engines.analysis.peerComparison
  - engines.scan.ratio
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - dateRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
    limitations:
      - browser 안에서는 multi-company 동시 로드 메모리 부담
forbidden:
  - peer 5~10 종 미만 통계 결과로 우열 단정 금지 — 통계 의미 부족.
  - 다른 분기 / 다른 회계 기준 (연결 vs 별도) peer 비교 금지 — 같은 시점 / 같은 scope 정렬.
  - peer median 대비 위치 (±σ) 명시 없이 우위 / 열위 단정 금지.
  - 서로 다른 통화 (KRW / USD) peer 환율 보정 없이 비교 금지.
failureModes:
  - 산업 분류 (KRX) 와 실제 사업 동질성 차이 무시
  - peer 시총 격차 (1 조 vs 10 조) 큰 경우의 비교 왜곡
  - 일회성 손익 (M&A / 매각) 영향 미보정 비교
  - 산업 sub-segment (반도체 메모리 vs 비메모리) 구분 없는 평균"
  - 외화 매출 비중 다른 peer 환율 영향 미분리
examples:
  - 삼성전자 vs 동종 5 peer 4 축 벤치마크
  - 4 대 금융지주 ratio 횡단
  - 산업 평균 대비 ±σ 위치 명시
  - 같은 size bucket peer 비교
gap:
  primary:
    - industry
    - analysis
  secondary:
    - scan
lastUpdated: '2026-05-07'
---

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

# 같은 산업 종목 추출
sector = c.sector
peer_codes = dartlab.industry(sector, "downstream")["stockCode"].head(5).to_list()

# 각 peer 분석 (sequential — 메모리 안전)
peers = []
for code in peer_codes:
    p = dartlab.Company(code)
    peers.append({"code": code, "ratios": p.show("ratios")})
```

## 호출 동작

회사 산업 → peer 5~10 추출 → 각 peer 의 핵심 ratio + 회사 ratio 비교 → 횡단 비교 표.

1. 회사 진입 + 산업 식별
2. industry(sector, stage) — peer 후보
3. 각 peer 의 c.show("ratios") — sequential
4. analysis("financial", "peer비교") — 횡단 표 생성

## 대표 반환 형태

- `tableRef` 1+5 개 (산업 + 5 peer ratio)
- `dateRef` 1 개
- 답변 본문 markdown table — 회사 + 5 peer × 핵심 ratio 5

## 연계 절차

1. engines.company.researchStarter — 회사 진입
2. engines.industry — 같은 산업 peer 추출
3. engines.analysis.peerComparison — 횡단 비교
4. engines.scan.ratio — peer ratio 일괄 (대안 path)

## 기본 검증

- peer 5~10 — 너무 적으면 통계 의미 X, 너무 많으면 산업 동질성 X.
- 같은 분기 + 같은 회계 기준 비교.
- "우위" 단정 X — peer median 대비 ±σ 위치 함께.
