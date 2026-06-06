---
id: engines.company.docsInternals
title: Company Panel Internals
category: engines
kind: curated
status: observed
purpose: Company 의 DART panel 공시 본문 파이프라인 — original zip → panel parquet → topic wide view 내부 추적.
sourceRefs:
  - dartlab://skills/engines.company.docsInternals
knowledgeRefs:
  - engines.company
  - engines.panel
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: limited
  pyodide:
    status: limited
whenToUse:
  - Company panel 파이프라인 내부 추적
  - DART panel row identity 디버깅
  - panel topic 매핑 점검
---

## 엔진 역할

`docsInternals` 는 이름만 남은 호환 skill 이며, 현행 SSOT 는 DART `panel` 이다. 공개 사용자 API 는 `c.topics` / `c.panel(topic)` 이고, 서버/뷰어/AI 는 동일한 panel artifact 를 읽는다.

## 공개 호출 방식

내부 점검은 panel 모듈을 직접 호출한다.

```python
import dartlab
from dartlab.providers.dart.panel.text import panelTextWide

c = dartlab.Company("005930")
df = panelTextWide(c.stockCode)
view = c.panel("businessOverview")
```

## 호출 동작

- 원천 zip XML 은 `data/original/dart/docs` 계층에 남을 수 있지만, 분석/뷰어/검색의 read SSOT 는 `data/dart/panel` 산출물이다.
- panel build 는 `src/dartlab/providers/dart/panel/build` 가 담당한다. topic 매핑은 `src/dartlab/providers/dart/panel/mapper.py` 와 panel schema 계층에서 관리한다.
- row identity 는 panel 컬럼의 `topic`, `blockType`, `blockOrder`, `sectionLeaf`, `contentRaw`/`content` 조합으로 판단한다.
- DART `/api/company/{code}/sections` 와 DART docs parquet read path 는 현행 사용자/API 표면이 아니다.

## 대표 반환 형태

`panelTextWide(code)` 와 `c.panel(topic)` 은 topic/block 행과 period 컬럼을 가진 wide DataFrame 을 반환한다. 핵심 식별자는 stockCode, corpName, topic, blockType, blockOrder, period, content/contentRaw 이다.

## 기본 검증

- panel 계약 변경 시 `engines.panel`, `operation.dataLineage`, 서버 viewer 계약, landing viewer 검증을 함께 갱신한다.
- DART 본문 계층에서 오래된 docs parquet read path, `Company`의 폐기된 sections 표면, 폐기된 대량 다운로드 표면이 되살아나면 SSOT 회귀로 본다.
