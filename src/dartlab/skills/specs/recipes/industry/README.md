---
id: recipes.industry.README
title: Industry 페르소나 — 산업 깊이 진입
purpose: 산업 단계·peer 매트릭스·CapEx wave·R&D 강도·마진 압축 등 *industry 분석가 시점* recipe 모음. fundamental 안 단일 회사 분석과 분리.
category: recipes
kind: curated
status: published
whenToUse:
  - 산업 분석 페르소나 진입
  - peer 비교 절차 선택
  - industry stage / capex / R&D 추세 확인
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
linkedSkills:
  - engines.industry
  - engines.scan
  - engines.company
---

# Industry 페르소나

회사 단일이 아닌 *산업 시점* 으로 보는 recipe. peers·stage·capex·R&D·마진 등 *cross-sectional* 신호 + *시계열* 추세 결합.

## 1 차 진입 5

| recipe | 역할 |
|---|---|
| [recipes.industry.industryStagePhase](/skills/recipes.industry.industryStagePhase) | 도입/성장/성숙/후행 단계 매핑 + ROIC-WACC spread |
| [recipes.industry.peerCapexWave](/skills/recipes.industry.peerCapexWave) | peer set capex 동조성 (lead/lag) |
| [recipes.industry.rdIntensityTrend](/skills/recipes.industry.rdIntensityTrend) | R&D / 매출 비율 추세 + cross-sectional rank |
| [recipes.industry.marginCompressionScan](/skills/recipes.industry.marginCompressionScan) | GP / OM 마진 압축 cluster (peer 대비) |
| [recipes.industry.supplyChainConcentration](/skills/recipes.industry.supplyChainConcentration) | 매출 상위 고객 / 매입 상위 거래처 비중 |

## 정체성

*generic industry analyst* 의 정성 narrative (성장기 vs 성숙기) 가 아닌, *peer set 정량 cross-section* 으로만 산업 시점 결론. 회사 단일 호출 (`Company.show`) 가 아닌 *industry universe* 위 비교 시점.
