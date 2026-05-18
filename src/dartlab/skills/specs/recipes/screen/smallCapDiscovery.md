---
id: recipes.screen.smallCapDiscovery
title: 중소형주 발굴 (성장 + valuation + quality 교집합)
category: recipes
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
  - engines.scan
  - engines.analysis
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - dateRef
visualRefs:
  - "engines.viz.peerMatrix"
  - "engines.viz.tableBackedChart"
  - "engines.viz.priceChart"
visualGuidance:
  - "동종 비교는 engines.viz.peerMatrix를 사용하고 universe·peerCount·metric 결손률을 답변에 함께 노출한다."
  - "표 기반 순위·추세는 engines.viz.tableBackedChart만 사용하고 tableRef/evidenceBinding이 없으면 차트 대신 검산 표로 낮춘다."
  - "가격·수급 반응은 engines.viz.priceChart로만 그리며 OHLCV 기간·벤치마크·latestAsOf가 맞지 않으면 본문 차트로 쓰지 않는다."

runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
    limitations:
      - browser 안에서는 multi-scan 메모리 부담
forbidden:
  - 시가총액 하위 종목 발굴 결과를 자동 매수 추천으로 단정 금지.
  - 성장 + valuation + quality 3 축 교집합 명시 없이 후보 단정 금지.
  - small-cap 발굴 결과의 유동성 위험 (낮은 거래량) 검토 누락 금지.
  - 5 년 흑자 + 부도 위험 회피 게이트 누락 금지.
failureModes:
  - small-cap 의 유동성 부족으로 거래 비용 폭증
  - 신규 / 비공시 / 폐업 종목의 시계열 길이 부족
  - 산업 sub-segment 동질성 검증 부족
  - 시총 정의 (보통주 vs 우선주 / 자기주식 차감 vs 미차감) 차이
  - 유동성 risk premium 의 valuation 영향 미반영
examples:
  - KR 중소형주 발굴 후보
  - 시총 하위 + 성장 + 저평가 + quality
  - small-cap + distress 필터
  - small-cap discovery + 깊이 분석
gap:
  primary:
    - scan
    - analysis
lastUpdated: '2026-05-13'
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

1. engines.scan — 성장
2. engines.scan — 저평가
3. engines.scan — 수익성
4. engines.scan — 시가총액 + 매출 필터
5. engines.analysis — quality 검증

## 기본 검증

- 시가총액 하위 + 매출 규모 하한 (예: 매출 1000 억) 으로 micro-cap 잡음 제거.
- 3 축 교집합 — AND 조건 명시.
- quality 등급 D/E 후보는 제외 또는 표시.
- "발굴" 단정 X — 분석 가설 + 모니터링 트리거 함께.
