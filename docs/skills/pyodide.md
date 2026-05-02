---
title: DartLab Skills / Pyodide
---

# Pyodide 가능 Skill

브라우저에서 바로 가능하거나 제한 조건에서 가능한 skill 목록이다. live API 최신성이 아니라 사용한 snapshot의 asOf 기준으로 판단한다.

| skill | category | status | data sources |
|---|---|---:|---|
| [engines.analysisUsage](engines/engines-analysisUsage) | `engines` | `limited` | HuggingFace dartlab-data finance-lite |
| [engines.companyRouterUsage](engines/engines-companyRouterUsage) | `engines` | `limited` | HuggingFace dartlab-data snapshot |
| [engines.creditUsage](engines/engines-creditUsage) | `engines` | `limited` | HuggingFace dartlab-data finance-lite |
| [engines.gatherUsage](engines/engines-gatherUsage) | `engines` | `limited` |  |
| [engines.industryUsage](engines/engines-industryUsage) | `engines` | `limited` | packaged taxonomy snapshot |
| [engines.macroUsage](engines/engines-macroUsage) | `engines` | `limited` |  |
| [engines.quantUsage](engines/engines-quantUsage) | `engines` | `limited` |  |
| [engines.scanUsage](engines/engines-scanUsage) | `engines` | `limited` | HuggingFace dartlab-data dart/scan/finance-lite.parquet |
| [engines.storyUsage](engines/engines-storyUsage) | `engines` | `limited` |  |
| [engines.visualUsage](engines/engines-visualUsage) | `engines` | `supported` |  |
| [cashflowReview](finance/cashflowReview) | `finance` | `limited` | HuggingFace dartlab-data dart/finance/[stockCode].parquet; HuggingFace dartlab-data edgar/finance/[ticker].parquet; HuggingFace dartlab-data dart/scan/finance-lite.parquet |
| [companyCausalReview](finance/companyCausalReview) | `finance` | `limited` | HuggingFace dartlab-data dart/docs/[stockCode].parquet; HuggingFace dartlab-data dart/finance/[stockCode].parquet; HuggingFace dartlab-data dart/report/[stockCode].parquet |
| [companyResearchStarter](finance/companyResearchStarter) | `finance` | `limited` | HuggingFace dartlab-data dart/finance/[stockCode].parquet; HuggingFace dartlab-data edgar/finance/[ticker].parquet |
| [creditRiskReview](finance/creditRiskReview) | `finance` | `limited` | HuggingFace dartlab-data dart/finance/[stockCode].parquet; HuggingFace dartlab-data edgar/finance/[ticker].parquet |
| [damodaranValuationReview](finance/damodaranValuationReview) | `finance` | `limited` | HuggingFace dartlab-data dart/finance/[stockCode].parquet; HuggingFace dartlab-data dart/report/[stockCode].parquet |
| [dartlabStoryReview](finance/dartlabStoryReview) | `finance` | `supported` | HuggingFace dartlab-data dart/docs/[stockCode].parquet; HuggingFace dartlab-data dart/finance/[stockCode].parquet; HuggingFace dartlab-data dart/report/[stockCode].parquet |
| [disclosureEventReview](finance/disclosureEventReview) | `finance` | `limited` | HuggingFace dartlab-data dart/docs/[stockCode].parquet; HuggingFace dartlab-data dart/report/[stockCode].parquet |
| [dividendCapitalReturnReview](finance/dividendCapitalReturnReview) | `finance` | `limited` | HuggingFace dartlab-data dart/finance/[stockCode].parquet; HuggingFace dartlab-data dart/report/[stockCode].parquet; HuggingFace dartlab-data dart/scan/finance-lite.parquet |
| [governanceAuditReview](finance/governanceAuditReview) | `finance` | `limited` | HuggingFace dartlab-data dart/docs/[stockCode].parquet; HuggingFace dartlab-data dart/report/[stockCode].parquet; HuggingFace dartlab-data dart/scan/finance-lite.parquet |
| [macroMarketReview](finance/macroMarketReview) | `finance` | `limited` | HuggingFace dartlab-data macro snapshot; HuggingFace dartlab-data krx/indices parquet |
| [peerComparisonReview](finance/peerComparisonReview) | `finance` | `limited` | HuggingFace dartlab-data dart/docs/[stockCode].parquet; HuggingFace dartlab-data dart/finance/[stockCode].parquet; HuggingFace dartlab-data dart/report/[stockCode].parquet |
| [profitabilityReview](finance/profitabilityReview) | `finance` | `limited` | HuggingFace dartlab-data dart/finance/[stockCode].parquet; HuggingFace dartlab-data edgar/finance/[ticker].parquet; HuggingFace dartlab-data dart/scan/finance-lite.parquet |
| [quantSignalReview](finance/quantSignalReview) | `finance` | `limited` | HuggingFace dartlab-data krx/prices parquet; HuggingFace dartlab-data dart/scan/finance-lite.parquet |
| [usEdgarCompanyReview](finance/usEdgarCompanyReview) | `finance` | `limited` | HuggingFace dartlab-data edgar/finance/[ticker].parquet; HuggingFace dartlab-data edgar/docs/[ticker].parquet |
| [runtime.dataAvailabilityCheck](runtime/runtime-dataAvailabilityCheck) | `runtime` | `supported` | HuggingFace dartlab-data snapshot; browser uploaded parquet/csv |
| [runtime.pyodideBrowser](runtime/runtime-pyodideBrowser) | `runtime` | `supported` | HuggingFace dartlab-data snapshot; browser uploaded parquet/csv |
| [runtime.skillDevelopmentLoop](runtime/runtime-skillDevelopmentLoop) | `runtime` | `limited` |  |
| [runtime.workbenchEvidenceFlow](runtime/runtime-workbenchEvidenceFlow) | `runtime` | `limited` |  |
| [crossSectionStockScreen](screens/crossSectionStockScreen) | `screens` | `limited` | HuggingFace dartlab-data krx/prices parquet; HuggingFace dartlab-data dart/scan/finance-lite.parquet |
| [krxIndexStrengthReview](screens/krxIndexStrengthReview) | `screens` | `limited` | HuggingFace dartlab-data krx/indices parquet |
| [screens.findUndervaluedQualityStocks](screens/screens-findUndervaluedQualityStocks) | `screens` | `limited` | HuggingFace dartlab-data dart/scan/finance-lite.parquet |
| [start.useSkillsCatalog](start/start-useSkillsCatalog) | `start` | `supported` |  |
| [visuals.tableBackedChart](visuals/visuals-tableBackedChart) | `visuals` | `supported` |  |
