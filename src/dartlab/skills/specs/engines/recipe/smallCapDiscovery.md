---
id: engines.recipe.smallCapDiscovery
title: 중소형주 발굴 (성장 + valuation + quality 교집합)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: 시가총액 하위 종목 중 성장 + 저평가 + 회계 quality 가 양호한 후보를 발굴하는 절차. small-cap value+growth thesis. 트리거 — '중소형주 발굴', 'small cap discovery', '소외 종목'.
whenToUse:
  - 중소형주
  - 소형주 발굴
  - small cap
  - 저평가 성장
  - value growth
  - 발굴 후보
  - 시가총액 하위
linkedSkills:
  - engines.scan.growth
  - engines.scan.valuation
  - engines.scan.profitability
  - engines.scan.crossSectionStockScreen
  - engines.analysis.earningsQuality
toolRefs:
  - engine_call
  - run_python
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
      - browser 안에서는 multi-scan 메모리 부담
lastUpdated: '2026-05-07'
---

## 공개 호출 방식

```python
import dartlab

growth = dartlab.scan("growth")
valuation = dartlab.scan("valuation")
quality = dartlab.scan("profitability")
# 시가총액 하위 + 3 축 교집합
```

## 호출 동작

3 축 스캔 결과 + 시가총액 필터 (하위 30%) 교집합으로 small-cap 후보 추출. 각 후보의 quality 등급 추가.

1. scan("growth") — 매출/영업이익 CAGR
2. scan("valuation") — PER/PBR/EV/EBITDA
3. scan("profitability") — OPM/ROE
4. crossSectionStockScreen — 시가총액 하위 + 매출 규모 하한
5. 교집합 + analysis("earningsQuality") 로 quality 검증

## 대표 반환 형태

- `tableRef` 4+ 개 (3 scan + 교집합)
- `dateRef` 1 개
- 답변 본문 markdown table — 후보 5~10 행 (시가총액 / 매출 CAGR / PER / OPM / quality)

## 연계 절차

1. engines.scan.growth — 성장
2. engines.scan.valuation — 저평가
3. engines.scan.profitability — 수익성
4. engines.scan.crossSectionStockScreen — 시가총액 + 매출 필터
5. engines.analysis.earningsQuality — quality 검증

## 기본 검증

- 시가총액 하위 + 매출 규모 하한 (예: 매출 1000 억) 으로 micro-cap 잡음 제거.
- 3 축 교집합 — AND 조건 명시.
- quality 등급 D/E 후보는 제외 또는 표시.
- "발굴" 단정 X — 분석 가설 + 모니터링 트리거 함께.
