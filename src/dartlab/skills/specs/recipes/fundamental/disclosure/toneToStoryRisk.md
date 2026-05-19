---
id: recipes.fundamental.disclosure.toneToStoryRisk
title: 공시 tone change × 산업 stage → story.risk 블럭 자동 발행 (storyboard 우회)
category: recipes
kind: recipe
scope: builtin
status: drafted
purpose: MD&A tone change + 뉴스 헤드라인 tone + 공시 fundamental shift 3 신호 composite "narrative risk" 점수 임계 초과 시 storyboard 신설 부담 없이 story.risk 섹션에 injection 가능한 markdown 블럭 자동 발행. storyboard 추가 부담 회피하면서 기존 story 의 risk 부분 보강. quant ↔ gather ↔ analysis ↔ story 격리 메우는 4-engine 조합. 트리거 — 'story risk auto', '공시 tone story 발행', 'narrative risk score'.
whenToUse:
  - story risk auto
  - 공시 tone story 발행
  - narrative risk composite
  - 자동 risk 블럭
linkedSkills:
  - engines.quant
  - engines.gather
  - engines.analysis
  - engines.story
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
visualRefs:
  - "engines.viz.evidenceCoverage"
  - "engines.viz.mermaidDiagram"
  - "engines.viz.tableBackedChart"
visualGuidance:
  - "근거 충족도는 engines.viz.evidenceCoverage로 검산/한계 섹션에만 배치하고 결론 차트처럼 해석하지 않는다."
  - "메커니즘 diagram은 engines.viz.mermaidDiagram으로 8노드 이하만 만들고 모든 edge에 문장·수치·sourceRef 근거를 둔다."
  - "표 기반 순위·추세는 engines.viz.tableBackedChart만 사용하고 tableRef/evidenceBinding이 없으면 차트 대신 검산 표로 낮춘다."

runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  pyodide:
    status: limited
gap:
  primary:
    - quant
    - story
  secondary:
    - gather
    - analysis
testUniverse:
  market: KR
  stockCodes:
    - "005930"
    - "000660"
    - "035420"
    - "051910"
    - "055550"
  asOfPolicy: latest
falsifier:
  description: "narrative risk score 가 trigger 된 종목의 forward 60d realized vol 이 base 보다 낮으면 신호 inverted"
  pythonCheck: |
    assert realized_vol_60d(triggered) > realized_vol_60d(non_triggered)
expectedNovelty:
  - narrativeRiskScore
  - storyRiskBlock
forbidden:
  - 단일 신호 (예 toneChange 만) 로 risk block 발행 금지 — 3 신호 composite 임계 필수.
  - 자동 발행된 risk block 을 운영자 review 없이 production 에 노출 금지.
failureModes:
  - tone change 정의 (LM dictionary vs FinBERT) 차이.
  - 뉴스 sentiment 가 공시 tone 과 시차 (lead/lag) 무시한 단순 합산.
examples:
  - 삼성전자 narrative risk composite
  - HMM 공시 tone + 뉴스 + 펀더멘털 동시 약화
lastUpdated: '2026-05-13'
---

## 공개 호출 방식

```python
import dartlab
import polars as pl

c = dartlab.Company("005930")

# 1. quant tone change — MD&A 사업의 내용 변화
tone = c.quant("toneChange") if hasattr(c, "quant") else None
tone_delta = tone.get("delta", 0) if isinstance(tone, dict) else 0
tone_z = tone.get("zScore", 0) if isinstance(tone, dict) else 0

# 2. 180 일 뉴스 sentiment
news = c.gather("news", days=180) if hasattr(c, "gather") else None
if isinstance(news, dict):
    news_sentiment = news.get("aggregateSentiment", 0)
elif isinstance(news, pl.DataFrame) and "sentiment" in news.columns:
    news_sentiment = float(news["sentiment"].mean() or 0)
else:
    news_sentiment = 0

# 3. 공시 fundamental change
disclosure = c.analysis("disclosureChange", "공시변화")
fundamental_shift = disclosure.get("shiftScore", 0) if isinstance(disclosure, dict) else 0

# 4. composite narrative risk score (가중)
narrative_risk = (
    0.4 * abs(tone_z)
    + 0.3 * abs(news_sentiment if news_sentiment < 0 else 0) * 2  # 음 sentiment 만 가중.
    + 0.3 * abs(fundamental_shift)
)
trigger = narrative_risk > 1.5

# 5. trigger 시 story.risk 블럭 markdown 생성
story_block = ""
if trigger:
    story_block = (
        "### narrative risk 자동 발행\n\n"
        f"- MD&A tone z-score: {tone_z:.2f} (delta {tone_delta:+.2f})\n"
        f"- 뉴스 180 일 평균 sentiment: {news_sentiment:+.2f}\n"
        f"- 공시 fundamental shift score: {fundamental_shift:+.2f}\n"
        f"- composite risk score: {narrative_risk:.2f} (임계 1.5)\n\n"
        "운영자 review 후 story 본문 내 risk 섹션에 inject 또는 별도 alert 처리.\n"
    )

emit_result(
    table=[{
        "stockCode": "005930",
        "toneZScore": round(tone_z, 2),
        "newsSentiment": round(news_sentiment, 2),
        "fundamentalShift": round(fundamental_shift, 2),
        "narrativeRiskScore": round(narrative_risk, 2),
        "trigger": trigger,
        "storyRiskBlock": story_block[:200] + "..." if len(story_block) > 200 else story_block,
    }],
    values={"narrativeRiskScore": narrative_risk, "trigger": trigger},
    date="2024-12-31",
)
```

## 호출 동작

1. `c.quant("toneChange")` — MD&A tone delta + z-score.
2. `c.gather("news", days=180)` — 뉴스 180 일 평균 sentiment.
3. `c.analysis("disclosureChange")` — 공시 fundamental shift score.
4. composite = 0.4 × |tone_z| + 0.3 × |neg news| × 2 + 0.3 × |shift|.
5. composite > 1.5 → trigger + markdown risk block 생성.

## 대표 반환 형태

`pl.DataFrame` — 단일 row:
- `toneZScore : float`
- `newsSentiment : float`
- `fundamentalShift : float`
- `narrativeRiskScore : float`
- `trigger : bool`
- `storyRiskBlock : str` — markdown (truncated to 200 char)

## 연계 절차

1. 본 recipe → narrative risk score + (trigger 시) story risk block.
2. trigger = True → 운영자 review → 기존 story.risk 섹션에 markdown inject (수동).
3. 동시 다발 종목 → `recipes.credit.distressCandidateScreen` 결과와 교집합 → 강한 사전 alert.
4. **storyboard 신설 우회** — 새 ReportType 추가 없이도 risk 분석 풍성도 증가.
