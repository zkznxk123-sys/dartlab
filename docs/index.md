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

## Skill OS 중심 체계

모든 사용법과 분석 절차는 [Skills](/skills)에서 먼저 찾는다. 자체 AI, 외부 AI, MCP, Web UI, Notebook도 같은 Skill OS를 읽고, 사용자는 목적별 절차·필요 근거·실행 환경을 한 화면에서 확인한다.

## 엔진 체계

| 엔진 | 진입점 | 역할 |
|------|--------|------|
| Company | `Company("005930")` | 데이터 조회 (show/select/sections) |
| Financial Data | `c.show("BS")`, `c.show("ratios")` | 재무제표 + 비율 |
| Analysis | `c.analysis()` | 14축 재무분석 + 6막 서사 |
| Credit | `c.credit()` | 독립 신용평가 (dCR 20단계) |
| Scan | `dartlab.scan()` | 전종목 횡단분석 |
| Gather | `c.gather()` | 외부 시장 데이터 |
| Story | `c.story()` | 보고서 렌더링 |
| AI | `dartlab.ask()` | 적극적 분석가 |

## 시작하기

- [Skills](/skills) — AI와 사람이 함께 쓰는 검색 가능한 사용법·분석절차 카탈로그
- [설치](getting-started/installation)
- [빠른 시작](getting-started/quickstart)

## 신용분석 보고서

dartlab 독립 신용분석(dCR) 보고서가 정기 발간된다. [블로그에서 보기](/blog/category/credit-reports)
- [SK hynix — dCR-AA+](credit/reports/000660)
- [NAVER — dCR-AA](credit/reports/035420)
- [LG — dCR-AA](credit/reports/003550)

## 참고

- [안정성 정책](stability)
- [변경 이력](https://github.com/eddmpython/dartlab/releases)
