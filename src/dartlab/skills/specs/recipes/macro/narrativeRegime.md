---
id: recipes.macro.narrativeRegime
title: 시장 narrative regime + Pettitt change-point
category: recipes
kind: recipe
scope: builtin
status: drafted
graphTier: L2
cluster: macro
purpose: 시장 (KR/US) lookback 90 일 buildNarrativePulse 결과의 daily sentiment_mean 시계열에 Pettitt 1979 non-parametric change-point test 적용. regime shift 일자 자동 검출 + Mann-Whitney U_k 통계량 + exp 근사 p-value 의 유의성 검정. regime_label = score 평균 5 단 (긍정 / 약긍정 / 혼조 / 약부정 / 부정). topic group_by volume_total desc top N. 트리거 — '시장 regime 전환', 'narrative regime', 'Pettitt change-point'.
whenToUse:
  - 시장 narrative regime 전환 조기 검출
  - 90 일 헤드라인 시계열 change-point
  - hot topic 시장 비중 top N
examples:
  - KR 시장 narrative 90 일 regime + shift 일자
  - 최근 시장 sentiment 부정 → 긍정 전환 일자
  - 시장 hot topic top 5 (반도체/배터리/...) volume 비중
expectedOutputs:
  - regime_label / regime_score (volume-weighted daily mean)
  - regime_shift_date / regime_shift_significant (p<0.05)
  - pettitt_U / pettitt_pvalue
  - topics_hot (list[topic_label, volume_total, sentiment_mean])
linkedSkills:
  - engines.macro
  - engines.scan
  - recipes.sentiment.newsSentimentFactor
  - recipes.macro.qualityMacroBeta
toolRefs:
  - EngineCall
  - RunPython
requiredEvidence:
  - skillRef
  - tableRef
  - valueRef
  - dateRef
  - sourceRef
  - executionRef
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
testUniverse:
  market: KR
expectedNovelty:
  - narrativeRegime
  - pettittChangePoint
falsifier:
  description: "n_days < 10 이면 Pettitt 미실행 (p=1.0). regime_shift_significant=True 라도 그 일자가 *원인* 이 아닐 수 있음 — change-point 는 통계적 분포 변경 검출일 뿐. lookback 30 일 이내는 noise dominant — 90 일 권장. archive Phase B 미실행 시 sentiment_mean NaN 으로 결과 중립 fallback."
forbidden:
  - change-point shift_date 를 사건 원인 단정 금지
  - n_days < 10 에서 regime 단정 금지
failureModes:
  - narrativePulse 빌드 0 행 (Phase A/B 미실행)
  - 90 일 < 10 일 분산 (휴장·신규 시장)
  - Pettitt p-value 근사식 small-n 부정확
lastUpdated: '2026-05-28'
---

## 공개 호출 방식

```python
from dartlab.scan.narrativeRegime import scanNarrativeRegime

result = scanNarrativeRegime(
    market="KR",
    lookbackDays=90,
    changePointThreshold=0.05,
    topTopics=5,
)

print(f"regime: {result['regime_label']} (score={result['regime_score']})")
print(f"shift: {result['regime_shift_date']} (p={result['pettitt_pvalue']})")
print("hot topics:")
for t in result["topics_hot"]:
    print(f"  {t['topic_label']}: volume={t['volume_total']}, mean={t['sentiment_mean']:.2f}")
```

## 출력 schema

| key | 의미 |
|---|---|
| `regime_label` | 5 단 (긍정/약긍정/혼조/약부정/부정) |
| `regime_score` | volume-weighted daily mean (-1~+1) |
| `regime_shift_date` | Pettitt U_k argmax 일자 |
| `regime_shift_significant` | p < threshold 유의 |
| `pettitt_U` / `pettitt_pvalue` | Mann-Whitney U_k + exp 근사 |
| `topics_hot` | volume desc top N |

## L6 UI 차트 연동

`/analysis/$code/events` (PriceEventChart) 가 본 결과의 `regime_shift_date` ~ `end` 구간을 반투명 배경 band 로 차트에 표시 (`showRegime=True` toggle).

## 한계

- Pettitt 는 *one change* 검정 — multiple shifts 는 binary search 또는 sliding window 별도 필요.
- p-value 가 exp 근사식 (small n 부정확). n ≥ 60 권장.
- volume-weighted 가 noise topic (자동 재배포) 에 민감 — Phase C `repeatedHeadlineFrequency` 보정 권장.
