# Topic Roadmap

46편 + 신용분석 보고서, 6개 카테고리. 2026-04-08 갱신.

> 운영 문서 관계도:
> - 글 단위 품질 기준 → [QUALITY_STANDARDS.md](QUALITY_STANDARDS.md)
> - dartlab 데이터 활용 → [DARTLAB_USAGE.md](DARTLAB_USAGE.md)
> - SEO 체크리스트 → [SEO_PLAYBOOK.md](SEO_PLAYBOOK.md)
> - 자산/SVG 규칙 → [ASSET_POLICY.md](ASSET_POLICY.md)
> - 카테고리 구조 → [BLOG_STRUCTURE.md](BLOG_STRUCTURE.md)

---

## 주제별 블로그 사상 (`05-company-reports`)

**"회사 한 건 = 한 편"이 아니다.** 같은 회사로 종합편/마진 해부/자본배분 베팅/경쟁사 비교 등 여러 각도의 글이 자연스럽게 나올 수 있다.

원칙:
- 미리 "이 회사 5편 쓰자" 식으로 로드맵 박지 않는다 — 의무감 글이 됨
- 분석/영상/audit 작업 중 발견된 각도가 글이 됨
- 같은 회사 후속 글은 frontmatter `stockCode` 동일하게 묶음 (랜딩에서 회사별 자동 그룹핑)
- 새 글은 audit→블로그→영상 한 세트 (`memory/feedback_company_report_pipeline.md`)
- 글 작성 전 [QUALITY_STANDARDS.md](QUALITY_STANDARDS.md)와 [DARTLAB_USAGE.md](DARTLAB_USAGE.md)를 펴 놓고 시작
- 발행 직전 [SEO_PLAYBOOK.md](SEO_PLAYBOOK.md)의 12개 체크리스트 통과

(상세는 `memory/company_report_series.md`)

---

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

#### 글 추가 패턴

새 글 추가 전 다음 5가지 확인:

1. [QUALITY_STANDARDS.md](QUALITY_STANDARDS.md) §4 — 회사 종합편 6가지 데이터 단위
2. [DARTLAB_USAGE.md](DARTLAB_USAGE.md) §1 — dartlab 호출 8패턴
3. [SEO_PLAYBOOK.md](SEO_PLAYBOOK.md) §2 — 12개 SEO 체크리스트
4. audit 메모리(`.claude/audits/{nn}-{slug}-anomalies.md`) — 이 회사의 거짓 사례 회귀
5. 영상(010 두산 / 011 SK 등)과 핵심 후킹 동기화

같은 회사의 후속 글(예: "삼양식품 마진 해부")은 frontmatter `stockCode: "003230"` 동일하게 묶음.

#### 현재 발간

- 01 SK하이닉스 (000660) — 2026-04-08 정직 정정 + IS/BS/CF 9년 시계열 표 + 사진 4장 추가 (16,000자, SVG 6장, 사진 4장) — [audit](https://github.com/eddmpython/dartlab/blob/master/.claude/audits/04-skhynix-anomalies.md), [영상 011](https://github.com/eddmpython/dartlab/tree/master/video/output/011-skhynix)
- 02 삼양식품 (003230) — 2026-04-08 시계열 표 + 사진 5장 추가 (12,000자, SVG 5장, 사진 5장) — [audit](https://github.com/eddmpython/dartlab/blob/master/.claude/audits/02-samyang-anomalies.md), [영상 009](https://github.com/eddmpython/dartlab/tree/master/video/output/009-samyang-buldak)
- 03 두산에너빌리티 (034020) — 2026-04-08 핵심 후킹 정직 재작성("9년 적자" 거짓 → "9년 다이어트") + 시계열 표 + 사진 4장 (12,000자, SVG 3장, 사진 4장) — [audit](https://github.com/eddmpython/dartlab/blob/master/.claude/audits/010-doosan-anomalies.md), [영상 010](https://github.com/eddmpython/dartlab/tree/master/video/output/010-doosan-enerbility)

이전 글들 (LG화학/KT&G/대한항공/삼성전자) 은 audit·영상 동반 없이 작성되어 2026-04-07 정리됨. 새 시리즈는 SK하이닉스부터 시작.

#### 다음 후보 (아이디어 풀)

회사 종합편:
- 한화에어로스페이스 (012450) — K9/천궁 수출 사이클
- HMM (011200) — 코로나 호황 → 정상화 후 자본배분
- 하이브 (352820) — IP 회사의 운전자본 구조
- 롯데케미칼 (011170) — 중국 화학 사이클 다운 회복 추적

같은 회사 후속(스토리만 잡혔으면):
- 삼양식품 마진 해부 — 2024Q1 한 분기 +10%P 점프의 정확한 원인
- SK하이닉스 8개 분기 메커니즘 확장 — Q1~Q4 × 2년 분기별 사건 시간선
- 두산에너빌리티 자본 재구성 추적 — 2022 -3.98조 항목 해부
- 라면 빅3 9년 비교 — 농심 vs 오뚜기 vs 삼양

후보는 "써야 할 의무"가 아니다. 분석 작업 중 강한 한 줄이 잡히면 그때 글이 된다.

---

## 거짓 회귀 사례 (2026-04-08)

이번 라운드에 발견한 거짓 19건의 패턴은 [QUALITY_STANDARDS.md §8](QUALITY_STANDARDS.md#8-지난-거짓-사례)에 등록. 같은 패턴 미래 글 작성 시 반복 금지.

## 정리 이력

128편 → 47편 → 44편 → 45편
- 84편 삭제 (과잉 세분화, 템플릿 복사, 제품 설명서, dartlab 광고)
- 7개 → 3개 카테고리 → 4개 카테고리 (04-credit-reports 추가)
- 전역 순번 → 카테고리별 번호
- credit 보고서: docs/credit/reports/ → blog/04-credit-reports/ 이관 (2026-04-03)
