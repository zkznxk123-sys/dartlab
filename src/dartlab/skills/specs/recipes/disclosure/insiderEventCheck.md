---
id: recipes.disclosure.insiderEventCheck
title: 내부자 거래·이벤트 점검 (insider scan + 공시 + 자본변동)
category: recipes
kind: recipe
scope: builtin
status: unverified
purpose: 회사의 내부자 거래·자본변동·임원 변경 같은 이벤트 신호를 시계열로 점검하는 절차. 거버넌스 점검의 보완. 트리거 — '내부자 거래', '임원 변경', '자본변동 이벤트'.
whenToUse:
  - 내부자 거래
  - 임원 매매
  - 자본 변동
  - insider trade
  - 임원 변경
  - 자기주식 매입 매도
  - 이벤트 신호
linkedSkills:
  - engines.company.researchStarter
  - engines.scan.insider
  - engines.scan.capital
  - engines.company.disclosureEvent
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - dateRef
visualRefs:
  - "engines.viz.evidenceCoverage"
  - "engines.viz.mermaidDiagram"
visualGuidance:
  - "근거 충족도는 engines.viz.evidenceCoverage로 검산/한계 섹션에만 배치하고 결론 차트처럼 해석하지 않는다."
  - "메커니즘 diagram은 engines.viz.mermaidDiagram으로 8노드 이하만 만들고 모든 edge에 문장·수치·sourceRef 근거를 둔다."

runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
    limitations:
      - browser 안에서는 disclosure 단일 호출만
forbidden:
  - 내부자 매도 1 건만 보고 회사 전망 부정 단정 금지 — 매매 의도 다양.
  - 자본변동 / 임원 변경 단일 이벤트로 가격 영향 단정 금지.
  - 공시 본문 (rcept_no / dartUrl) 없이 이벤트 의미 단정 금지.
  - 5% 룰 / 스톡옵션 행사 / 보유 의무 구분 누락 금지.
failureModes:
  - 임원 매수 / 매도 사유 (스톡옵션 / 상속 / 증여) 미구분
  - 단발성 매매로 추세 단정 — 6 개월~1 년 시계열 동반"
  - 자기주식 매입 vs 소각 동치 처리"
  - 임원 변경의 정상 (정년 / 승진) vs 위기 (경영권 분쟁) 구분
  - 5 일 보고 시한 무시한 실시간 인용
examples:
  - 삼성전자 임원 매매 + 자본변동 시계열
  - 자기주식 매입 / 소각 이벤트
  - 임원 변경 + 공시 본문 검증
  - 내부자 거래 + 거버넌스 결합
lastUpdated: '2026-05-13'
---

## 공개 호출 방식

```python
import dartlab

c = dartlab.Company("005930")

insider = dartlab.scan("insider")
capital = dartlab.scan("capital")
events = c.disclosure(days=180, type="자기주식")
holders = c.show("majorHolder")
```

## 호출 동작

내부자 매매 패턴 + 자본변동 (자사주 매입/매도, 유상증자, 무상증자) + 최근 공시 이벤트 + 최대주주 지분 변화.

1. 회사 진입
2. scan("insider") — 내부자 매매 횡단 (peer 대비 강도)
3. scan("capital") — 자본구조 변동 횡단
4. disclosure(days=180, type=...) — 최근 자본 관련 공시
5. show("majorHolder") — 최대주주 / 주요주주 변화

## 대표 반환 형태

- `tableRef` 4 개 (insider scan + capital scan + disclosure + majorHolder)
- `dateRef` 1 개

## 연계 절차

1. engines.company.researchStarter — 회사 진입
2. engines.scan.insider — 내부자 매매 횡단
3. engines.scan.capital — 자본구조 변동
4. engines.company.disclosureEvent — 자본 관련 공시 원문

## 기본 검증

- 내부자 매매 시점 명시 (filedAt) + 거래 종류 (매수/매도).
- 자본 변동은 변동 전후 지분율 함께.
- "내부자 매수 = 호재" 단정 X — 시점·규모·맥락 함께.
