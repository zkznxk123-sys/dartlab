# Topic Roadmap

46편 + 신용분석 보고서, 4개 카테고리. 2026-04-03 최종.

## 카테고리

### 01 공시 읽기 (40편)

| # | slug | 시리즈 |
|---|------|--------|
| 01 | everything-about-dart | dart-foundations |
| 02 | everything-about-edgar | edgar-reading |
| 03 | risk-factors-and-mdna | edgar-reading |
| 04 | reading-business-reports | report-reading-foundations |
| 05 | business-section-changes-judgment | report-reading-foundations |
| 06 | how-far-to-trust-new-business-plans | report-reading-foundations |
| 07 | audit-report-and-kam | audit-and-governance |
| 08 | clean-audit-opinion-but-still-risky | audit-and-governance |
| 09 | internal-controls-and-audit-committee | audit-and-governance |
| 10 | restatement-before-audit-and-reaudit-signals | audit-and-governance |
| 11 | audit-fees-and-non-audit-fees | audit-and-governance |
| 12 | major-shareholder-and-related-parties | ownership-and-governance |
| 13 | executive-pay-disclosure | ownership-and-governance |
| 14 | shareholder-return-what-matters | ownership-and-governance |
| 15 | governance-red-flags | ownership-and-governance |
| 16 | how-to-read-agm-notice | ownership-and-governance |
| 17 | construction-company-filings | industry-reading |
| 18 | biotech-company-filings | industry-reading |
| 19 | financial-company-filings | industry-reading |
| 20 | samsung-vs-tsmc-capex-and-depreciation | global-comparison |
| 21 | hyundai-vs-toyota-inventory-and-receivables | global-comparison |
| 22 | celltrion-vs-amgen-rnd-and-intangibles | global-comparison |
| 23 | beyond-the-numbers | financial-context |
| 24 | why-rising-sales-can-still-be-risky | financial-context |
| 25 | development-costs-and-intangibles | financial-context |
| 26 | lease-liabilities-and-debt-maturity | financial-context |
| 27 | associates-joint-ventures-and-equity-method | financial-context |
| 28 | foreign-exchange-gains-and-derivatives | financial-context |
| 29 | sga-growth-vs-sales | financial-context |
| 30 | segment-reporting-interpretation | financial-context |
| 31 | ifrs18-income-statement-changes | financial-context |
| 32 | capacity-utilization-capex | capital-and-earnings |
| 33 | receivables-and-allowance | capital-and-earnings |
| 34 | operating-cash-flow-vs-net-income | capital-and-earnings |
| 35 | treasury-stock-third-party-allotment... | capital-and-earnings |
| 36 | opendart-material-events | data-pipeline |
| 37 | opendart-xbrl-notes-pipeline | data-pipeline |
| 38 | corp-code-to-filing-pipeline | data-pipeline |
| 39 | data-quality-validation | data-pipeline |
| 40 | dart-edgar-unified-structure | data-pipeline |

### 02 DartLab 소식 (6편, 사용자 관리)

| # | slug |
|---|------|
| 01 | dartlab-easy-start |
| 02 | vscode-extension-install |
| 03 | scan-market-finance |
| 04 | company-one-stock-code |
| 05 | search-without-embeddings |
| 06 | magic-formula-korea |

### 03 실전기업분석 (3편, 사용자 관리)

| # | slug |
|---|------|
| 01 | revenue-structure-how-to-read |
| 02 | asset-structure-how-to-read |
| 03 | cashflow-how-to-read |

### 04 신용분석 보고서 (프로그래매틱, publisher.py 관리)

자동 생성 카테고리. `blog/04-credit-reports/_registry.json`으로 번호/slug 관리.
`publishReport("005930")` → 블로그 포스트 자동 생성.

현재 발간: 삼성전자, SK하이닉스, NAVER, LG (4개사)

### 05 기업분석 보고서 (audit + 블로그 + 영상 한 세트)

`memory/feedback_company_report_pipeline.md` 강제 규칙 적용. **기업 한 건 = audit + 블로그 + 영상 한 세트**. 셋 중 하나만 만드는 것 금지.

현재 발간:
- 01 SK하이닉스 (000660) — 2026-04-07 (audit 04 fix 후 재작성, 11,000자, SVG 6장) — [audit](https://github.com/eddmpython/dartlab/blob/master/.claude/audits/04-skhynix-anomalies.md), [영상](https://github.com/eddmpython/dartlab/tree/master/video/output/011-skhynix)
- 02 삼양식품 (003230) — 2026-04-07 (audit 02 신규, 9,500자, SVG 5장) — [audit](https://github.com/eddmpython/dartlab/blob/master/.claude/audits/02-samyang-anomalies.md), [영상](https://github.com/eddmpython/dartlab/tree/master/video/output/009-samyang-buldak)
- 03 두산에너빌리티 (034020) — 2026-04-07 (audit 010 갱신, 9,500자, SVG 3장) — [audit](https://github.com/eddmpython/dartlab/blob/master/.claude/audits/010-doosan-anomalies.md), [영상](https://github.com/eddmpython/dartlab/tree/master/video/output/010-doosan-enerbility)

이전 글들 (LG화학/KT&G/대한항공/삼성전자) 은 audit·영상 동반 없이 작성되어 2026-04-07 정리됨. 새 시리즈는 SK하이닉스부터 시작.

다음 후보: 한화에어로스페이스 / 두산에너빌리티 / HMM / 하이브 / 롯데케미칼

## 정리 이력

128편 → 47편 → 44편 → 45편
- 84편 삭제 (과잉 세분화, 템플릿 복사, 제품 설명서, dartlab 광고)
- 7개 → 3개 카테고리 → 4개 카테고리 (04-credit-reports 추가)
- 전역 순번 → 카테고리별 번호
- credit 보고서: docs/credit/reports/ → blog/04-credit-reports/ 이관 (2026-04-03)
