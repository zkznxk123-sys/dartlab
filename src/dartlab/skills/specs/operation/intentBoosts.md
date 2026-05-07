---
id: operation.intentBoosts
title: "Skill 검색 의도 가중치 SSOT"
kind: curated
scope: builtin
status: observed
category: operation
purpose: "skills.search() 가 사용자 query 를 특정 skill 로 라우팅하기 위해 적용하는 의도 매칭 가중치 규칙의 단일 정본. 코드에서 하드코딩된 값을 제거해 markdown SSOT 로 통합."
whenToUse:
  - "검색 가중치"
  - "intent boost"
  - "search ranking"
  - "query 라우팅"
  - "skill 검색이 의도와 어긋나"
inputs:
  - "사용자 query (자연어)"
outputs:
  - "추천 skill id 와 추가 score"
knowledgeRefs:
  - "start.useSkillsCatalog"
  - "start.dartlabSkillOs"
sourceRefs:
  - "dartlab://skills/operation.intentBoosts"
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: supported
  pyodide:
    status: supported
intentBoosts:
  - skillIds: ["start.useSkillsCatalog"]
    terms:
      - skills
      - skill
      - 스킬
      - 스킬스
      - catalog
      - 카탈로그
      - "어떻게 써"
      - 사용법
      - "뭐 할 수"
      - "할 수 있어"
      - 할수
      - 기능
      - "뭘 분석"
    boost: 16.0
  - skillIds: ["start.dartlabSkillOs"]
    terms:
      - 처음
      - 최초
      - 진입점
      - 입문
      - "전체 체계"
      - "문서 체계"
      - "skill os"
      - "스킬 os"
      - "어디서 시작"
      - "llm이 와도"
      - "외부 ai"
      - "운영 문서"
      - ops
    boost: 18.0
  - skillIds: ["operation.opsAsSkills"]
    terms:
      - "ops를 스킬"
      - "ops 문서"
      - "운영 규칙"
      - "규칙 통합"
      - "문서 중복"
      - ssot
      - sourceRefs
      - "문서 정리"
      - "체계 단순화"
    boost: 17.0
  - skillIds: ["operation.extendSkills"]
    terms:
      - "스킬 추가"
      - "스킬 확장"
      - "확장 규칙"
      - "새 skill"
      - "user skill"
      - "curated skill"
      - "공식 승격"
      - "독스트링 승격"
    boost: 16.0
  - skillIds: ["runtime.skillDevelopmentLoop"]
    terms:
      - "스킬 개발"
      - "skill 개발"
      - "엔진 조합"
      - "엔진에 없는"
      - "정의되지 않은"
      - 응용
      - 조합
      - "새 분석"
      - "audit 반영"
      - "독스트링 보강"
    boost: 15.0
  - skillIds: ["runtime.workbenchEvidenceFlow"]
    terms:
      - 근거
      - 검산
      - 마무리
      - evidence
      - ref
      - refs
      - finalize
      - 실행하고
      - 답변
    boost: 15.0
  - skillIds: ["runtime.dataAvailabilityCheck"]
    terms:
      - 데이터가
      - 데이터
      - dataset
      - 있는지
      - 가용
      - 최신
      - 기준일
      - 확인
    boost: 14.0
  - skillIds: ["engines.company.researchStarter"]
    terms:
      - "종목 분석"
      - "기업 분석"
      - "분석 시작"
      - "첫 단계"
      - 시작
      - "company research"
    boost: 13.0
  - skillIds: ["engines.data.foundation"]
    terms:
      - "데이터 엔진"
      - "데이터 기본기"
      - "기본 데이터"
      - "company gather scan"
      - "company/gather/scan"
      - "원자료 횡단"
      - "데이터 확보 순서"
      - "응용 분석 시작"
    boost: 15.0
  - skillIds: ["engines.scan", "engines.scan.growth"]
    terms:
      - 찾아
      - 찾아줘
      - 후보
      - 상위
      - 랭킹
      - 순위
      - 스크리닝
      - 스캔
      - screen
      - ranking
      - candidate
      - "growth company"
      - "성장하는 회사"
    boost: 16.0
  - skillIds: ["engines.viz.tableBackedChart"]
    terms:
      - 차트
      - 시각화
      - 그래프
      - "랭킹 차트"
      - "비교 차트"
      - chart
      - visual
    boost: 14.0
  - skillIds: ["engines.company.usEdgarReview"]
    terms:
      - 미국
      - 미장
      - edgar
      - filings
      - filing
      - 10-k
      - 10-q
      - ticker
      - 티커
    boost: 13.0
  - skillIds: ["engines.macro.marketReview"]
    terms:
      - 금리
      - 환율
      - 매크로
      - 거시
      - 경기
      - 유동성
      - macro
      - rates
      - fx
    boost: 12.0
  - skillIds: ["engines.credit.creditRisk"]
    terms:
      - 신용
      - 위험
      - 안정성
      - 부채
      - 이자보상
      - credit
      - risk
    boost: 11.0
  - skillIds: ["engines.analysis.profitability"]
    terms:
      - 수익성
      - 이익률
      - 마진
      - 영업이익
      - profitability
      - margin
    boost: 10.0
  - skillIds: ["engines.analysis.cashflow"]
    terms:
      - 현금흐름
      - 영업현금
      - fcf
      - cashflow
      - "cash flow"
    boost: 10.0
  - skillIds: ["engines.analysis.dividendCapitalReturn"]
    terms:
      - 배당
      - 주주환원
      - 자사주
      - dividend
      - buyback
    boost: 10.0
  - skillIds: ["engines.analysis.governanceAudit"]
    terms:
      - 지배구조
      - 감사
      - 내부통제
      - 분식
      - governance
      - audit
    boost: 10.0
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-07'
---

## 무엇을 하나

`dartlab.skills.search(query)` 가 query 와 skill 의 매칭 점수를 계산할 때, 본 skill 의 frontmatter `intentBoosts[]` 에 정의된 18 개 의도 규칙을 적용한다. 각 rule 은 `(skillIds, terms, boost)` 로 구성:

- `skillIds[]`: 가중치를 받을 대상 skill id 목록.
- `terms[]`: query 에 (case-insensitive substring) 등장하면 매칭으로 간주할 키워드 목록.
- `boost`: 매칭 시 점수에 더할 값.

추가로 `engines.company.usEdgarReview` 는 ticker 정규식 (`\b[A-Z]{1,5}\b`) 매칭 시 +8.0 boost — 이는 코드 (`registry.py`) 에 남는다 (정규식 정의는 markdown 으로 옮기지 않는다).

## SSOT 정책

본 파일이 의도 가중치의 단일 정본이다. `src/dartlab/skills/registry.py` 의 `_INTENT_SKILL_BOOSTS` 는 본 frontmatter 를 lazy 로드하는 wrapper 만 보유한다. 새 의도 규칙은 본 파일의 frontmatter 에만 추가한다 — 코드 수정 불필요.

## 다음 단계

- [start.useSkillsCatalog](/skills/start.useSkillsCatalog) — query → skill 검색 절차.
- [operation.opsAsSkills](/skills/operation.opsAsSkills) — 운영 문서가 어떻게 skills 로 흡수됐는지.
