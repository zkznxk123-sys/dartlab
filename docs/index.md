---
title: DartLab
---

# DartLab

종목코드 하나로 기업의 전체 이야기를 본다.

```python
import dartlab

c = dartlab.Company("005930")           # 삼성전자

c.show("BS")                            # 재무상태표
c.analysis("financial", "수익성")         # 14축 재무분석
c.credit()                              # dCR 신용평가
dartlab.scan("governance")               # 전종목 지배구조
dartlab.ask("삼성전자 분석해줘")           # AI 분석가
```

## Skill Catalog 중심 체계

모든 사용법과 분석 절차는 `src/dartlab/skills`와 [Skill Catalog](/skills)에서 먼저 찾는다. 자체 AI, 외부 AI, MCP, Web UI도 같은 skill resolver를 읽고, 세부 API 능력은 [CAPABILITIES.md](https://github.com/eddmpython/dartlab/blob/master/CAPABILITIES.md)로 연결한다.

## 엔진 체계

| 엔진 | 진입점 | 역할 |
|------|--------|------|
| [Company](https://github.com/eddmpython/dartlab/blob/master/CAPABILITIES.md) | `Company("005930")` | 데이터 조회 (show/select/sections) |
| [Financial Data](https://github.com/eddmpython/dartlab/blob/master/CAPABILITIES.md) | `c.show("BS")`, `c.show("ratios")` | 재무제표 + 비율 |
| [Analysis](https://github.com/eddmpython/dartlab/blob/master/CAPABILITIES.md) | `c.analysis()` | 14축 재무분석 + 6막 서사 |
| [Credit](https://github.com/eddmpython/dartlab/blob/master/CAPABILITIES.md) | `c.credit()` | 독립 신용평가 (dCR 20단계) |
| [Scan](https://github.com/eddmpython/dartlab/blob/master/CAPABILITIES.md) | `dartlab.scan()` | 전종목 횡단분석 |
| [Gather](https://github.com/eddmpython/dartlab/blob/master/CAPABILITIES.md) | `c.gather()` | 외부 시장 데이터 |
| [Story](https://github.com/eddmpython/dartlab/blob/master/CAPABILITIES.md) | `c.story()` | 보고서 렌더링 |
| [AI](https://github.com/eddmpython/dartlab/tree/master/src/dartlab/skills/specs/runtime) | `dartlab.ask()` | 적극적 분석가 |

## 시작하기

- [설치](getting-started/installation)
- [빠른 시작](getting-started/quickstart)
- [Skill Catalog](/skills) — AI와 사람이 함께 쓰는 검색 가능한 사용법·분석절차 카탈로그
- [Capability Reference](https://github.com/eddmpython/dartlab/blob/master/CAPABILITIES.md) — 공개 docstring 기반 API 능력 지도

## 신용분석 보고서

dartlab 독립 신용분석(dCR) 보고서가 정기 발간된다. [블로그에서 보기](/blog/category/credit-reports)
- [SK hynix — dCR-AA+](credit/reports/000660)
- [NAVER — dCR-AA](credit/reports/035420)
- [LG — dCR-AA](credit/reports/003550)

## 참고

- [안정성 정책](stability)
- [변경 이력](https://github.com/eddmpython/dartlab/releases)
- CAPABILITIES.md (GitHub 저장소 루트) — 전체 API 레퍼런스
