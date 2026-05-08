---
id: engines.story
title: Story (보고서 빌더)
kind: curated
scope: builtin
status: observed
category: engines
purpose: Story 는 6 막 인과 구조의 회사 보고서를 조립하는 빌더 엔진이다. analysis · credit · scan · quant · macro · industry 의 결과를 블록 단위로 조합 — 11 reportType × 7 기업유형 템플릿. 트리거 — '보고서', '기업 이야기', 'story', '6 막 인과'.
whenToUse:
  - Story
  - story
  - 보고서 생성
  - 6 막 인과
  - 기업 종합 분석
  - reportType
  - scorecard
  - creditScore
  - narrative 블록
inputs:
  - 종목코드 또는 Company
  - reportType (선택 — full · executive · credit · valuation · ...)
  - 자유 조립 시 Block 리스트
outputs:
  - Story 인스턴스 (sections · summaryCard)
  - render 출력 (rich · html · markdown · json)
  - block list (scorecard · creditScore · narrative · valuationBand · ...)
capabilityRefs:
  - Story
  - Company.story
knowledgeRefs:
  - start.dartlabSkillOs
  - engines.company
  - engines.analysis
  - engines.credit
  - engines.macro
sourceRefs:
  - dartlab://skills/engines.story
requiredEvidence:
  - target
  - reportType
  - sections
  - tableRef
  - executionRef
expectedOutputs:
  - 6 막 구조 보고서
  - block 별 evidence 묶음
  - thesis · evidenceBlocks · riskBlocks · limits
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
    status: limited
failureModes:
  - 하위 엔진 (analysis · credit) 결과 ref 없이 narrative 만 생성
  - reportType 미지정 + 기업유형 자동 감지 실패 시 fallback 없음
  - block 자유 조립 시 evidence 없는 빈 섹션 발급
  - story 가 직접 숫자 계산 — 모든 숫자는 하위 엔진 결과 ref 에 묶어야
forbidden:
  - story 에서 직접 숫자 계산 또는 추정 금지 — 하위 엔진 결과만 인용.
  - thesis · risk 문장에 source ref 없이 단정 금지.
  - 옛 단일 reportType (`thesis`) 으로 새 보고서 생성 금지 — 명시 reportType 또는 자동 감지.
examples:
  - 005930 전체 보고서
  - 신용분석 전용 보고서 (reportType="credit")
  - 5 영역 scorecard A~F 평가
  - 20 등급 신용평가 함께 보기
  - 자유 블록 조립 (Story([blocks]))
procedure:
  - dartlab.Company(code).story() 가 가장 단순한 진입 — 자동 reportType + 기업유형 감지.
  - 명시 호출은 c.story(reportType="credit") 또는 c.story(section_name).
  - 자유 조립은 from dartlab.story import blocks, Story; b = blocks(c); Story([b["growth"], b["margin"]]).
  - 출력 형식 — story.render("markdown") / toHtml() / toMarkdown().
  - 하위 엔진 (analysis · credit · macro · industry) 결과의 ref 가 자동 묶임.
linkedSkills:
  - engines.company
  - engines.analysis
  - engines.credit
  - engines.macro
  - engines.industry
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-08'
---

## 엔진 역할

`story` 는 *해석하지 않고 다양한 관점의 근거를 배치* 하는 보고서 조립기다. analysis (재무 인과) · credit (신용 위험) · scan (횡단 비교) · quant (정량 신호) · macro (시장 환경) · industry (밸류체인 위치) 결과를 블록 단위로 조합해 6 막 구조 보고서를 만든다.

숫자 계산은 하위 엔진 결과 ref 에 묶고, story 자체는 *thesis · evidence · risk · limit* 의 문장 골격만 제공.

## 공개 호출 방식

```python
import dartlab

# 1. Company-bound — 가장 단순한 진입점
c = dartlab.Company("005930")
story = c.story()                          # 자동 reportType + 기업유형 감지
print(story.render("markdown"))

# 2. reportType 명시
credit_report = c.story(reportType="credit")
valuation = c.story(reportType="valuation")
exec_brief = c.story(reportType="executive")

# 3. 단일 섹션
revenue = c.story("수익구조")               # 수익구조 블록만

# 4. 자유 조립 (블록 단위)
from dartlab.story import blocks, Story
b = blocks(c)
custom = Story([b["growth"], b["margin"], b["cashflow"]])

# 5. 출력 형식 변환
print(custom.toMarkdown())
print(custom.toHtml())
print(custom.render("rich"))               # 터미널 색상
print(custom.render("json"))               # AI 소비용
```

## 호출 동작

`Company.story()` (인자 없음) → 자동 reportType 선택 + 기업유형 자동 감지 (template). reportType 후보: `full` · `executive` · `credit` · `valuation` · `governance` · `forecast` · `risk` 외 11 종.

기업유형 template: 일반 · 금융 · 지주 · 신생/성장 · 사이클 · 자원 · 플랫폼 7 종. analysis 의 `companyType` 함수로 판정.

`Story` 클래스 자체를 호출하면 `Story(itemsOrStockCode, *, stockCode=, corpName=, sections=, layout=)` — 자유 조립 또는 직접 종목코드. `dartlab.story` 가 클래스 자체이므로 *함수처럼 호출하지 않는다* (`dartlab.story(c)` 같은 호출은 `Story(c)` 가 되어 첫 인자 타입이 안 맞음).

블록 한 개의 evidence 가 비면 빈 섹션이 그대로 나간다 — story 는 채워주지 않음. 하위 엔진 호출 결과 부족 시 해당 블록 skip 또는 limits 에 명시.

## 2 축 체계 — reportType × template

```
reportType   (집중 시점)              template     (기업 유형 자동 감지)
────────────────────────────         ────────────────────────────────
full          종합                   일반          제조/서비스
executive     경영 요약              금융          은행/보험/카드
credit        신용 위험              지주          비순환 출자
valuation     적정가                 신생/성장     상장 5 년 이내
governance    지배구조               사이클        반도체/조선
forecast      매출 전망              자원          정유/철강/유틸
risk          리스크 점검            플랫폼        IT 서비스
disclosure    공시 변화
peer          peer 비교
sector        섹터 위치
custom        자유 조립
```

reportType × template = block list 결정. 각 block 은 하위 엔진 (analysis · credit · macro · industry · scan · quant) 호출 결과 ref 를 인용.

## 대표 반환 형태

```text
Story 인스턴스
   sections : list[Section]      # 6 막별 섹션
   summaryCard : SummaryCard     # 최상단 요약 (grade · 핵심 metrics)
   render(fmt) : str             # "rich" / "html" / "markdown" / "json"
   toHtml() : str
   toMarkdown() : str
```

```text
section dict
   thesis : str                  # 한국어 인과 문장 (analysis narrative 인용)
   evidenceBlocks : list[dict]   # tableRef / valueRef / dateRef
   riskBlocks : list[dict]       # 리스크 요인 + ref
   limits : list[str]            # 데이터 부족 · 가정 한계
   sourceRefs : list[str]        # dartlab://... 출처
```

## evidence 기준

story 답변은 `target` · `reportType` · `template` · 모든 block 의 `tableRef` / `valueRef` 를 남긴다. evidence 없는 thesis 문장은 *허용 안 됨* — block 자체를 skip 또는 limits 에 명시.

## docstring ↔ story 환류

엔진 docstring 의 Guide 섹션이 audit 통과 → story 블록 템플릿에 반영 (같은 해석 규칙 · 같은 임계값). 반대로 story 블록 중 재현 가능 + 해석 규칙 명확한 것 → 공개 함수로 추출해 엔진 docstring Guide 로 명시. AI · story 공용 호출.

## 기본 실행 순서

1. `Company(code).story()` 자동 보고서 — 가장 단순.
2. 신용 / 가치평가 / 거버넌스 등 집중 시점이면 `reportType=` 명시.
3. 자유 조립은 `blocks(c)` 로 block dict 받고 `Story([...])`.
4. 출력 형식 — markdown (LLM 답변), html (landing 임베드), json (AI 후속 처리).

## 기본 검증

`Story` 클래스 시그니처 · 11 reportType · 7 template · block list 가 바뀌면 본 skill + analysis · credit 응용 skill 동시 갱신. block 추가 시 evidence 묶음 helper (`tableRef` · `valueRef`) 계약 동기.
