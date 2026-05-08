---
id: engines.recipe.valuationCheck
title: 가치평가 점검 (DCF + 상대가치 + valuation band)
category: engines
kind: recipe
scope: builtin
status: unverified
purpose: 회사의 valuation 을 DCF 절대평가 + 상대가치 (peer multiple) + valuation band (역사 평균 대비) 3 축으로 종합 점검하는 절차. 트리거 — '밸류에이션 점검', 'fair value', '저평가 판단'.
whenToUse:
  - 가치평가
  - 적정주가
  - DCF 분석
  - PER PBR EV/EBITDA
  - 밸류에이션
  - 저평가 고평가 판단
  - 적정 주가 범위
linkedSkills:
  - engines.company.researchStarter
  - engines.analysis.valuation
  - engines.analysis.valuationBand
  - engines.scan.valuation
  - engines.quant.value
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
    limitations:
      - browser 안에서는 quant value 시계열 일부 한정
forbidden:
  - 적정주가 단일 값 단정 금지 — 범위 (best / base / worst).
  - DCF 가정 (할인율 / 성장률 / terminal multiple) 명시 없이 fair value 단정 금지.
  - peer multiple 비교 시 산업 동질성 + 단계 (성장기 / 성숙기) 일치 누락 금지.
  - 저평가 / 고평가 단정 금지 — 가정 시나리오 + 신뢰도 동반.
failureModes:
  - DCF terminal value 가 전체 가치의 70%+ 일 때 가정 의존성 무시
  - peer multiple 의 산업 / 단계 차이 무시한 단순 평균
  - valuation band 의 역사 평균 윈도우 (3Y vs 10Y) 임의 선택"
  - 4 방법론 (DCF / DDM / 상대가치 / RIM) 결과 불일치 시 단일 값 선택"
  - 시장 환경 변화 (금리 / 유동성) 미반영한 역사 mean 비교"
examples:
  - 삼성전자 4 방법론 종합 적정주가 범위
  - 가치평가 + valuation band 결합
  - peer multiple + 산업 단계 일치
  - DCF best / base / worst 시나리오
lastUpdated: '2026-05-07'
---

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

valuation = c.analysis("valuation", "가치평가")
band = c.analysis("financial", "밸류에이션밴드")
peer_band = dartlab.scan("valuation")
qval = c.quant("가치")
```

## 호출 동작

valuation 종합 (DCF·DDM·상대가치·RIM 4 방법론) → valuation band (역사 평균 ±σ 대비 현재 위치) → peer 횡단 비교 → 기술적 가치 신호.

1. 회사 진입
2. analysis("valuation", "가치평가") — 4 방법론 종합 적정주가 범위
3. analysis("financial", "밸류에이션밴드") — 역사 평균 대비 위치
4. scan("valuation") — peer 횡단 valuation
5. quant("가치") — 기술적 가치 신호

## 대표 반환 형태

- `tableRef` 3+ (valuation 4 방법론 + band 시계열 + peer scan)
- `valueRef` 5+ (DCF 적정가 / PER 적정가 / EV/EBITDA / 현재가 대비 % / band 위치)
- `dateRef` 1 개

## 연계 절차

1. engines.company.researchStarter — 회사 진입
2. engines.analysis.valuation — DCF + 상대가치 종합 적정주가
3. engines.analysis.valuationBand — 역사 평균 ±σ 위치
4. engines.scan.valuation — peer 횡단 멀티플
5. engines.quant.value — 기술적 가치 신호

## 기본 검증

- 적정주가는 단일 값 X — 범위 (best/base/worst).
- valuation 가정 (할인율·성장률·terminal multiple) 명시.
- peer 비교는 같은 산업 + 동등 단계 (성장기/성숙기) 만.
- "저평가" 단정 X — 가정 시나리오 + 신뢰도 함께.
