# Topic Roadmap

53편 + 신용분석 보고서, 6개 카테고리. 2026-04-18 갱신.

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

### 01 공시 읽기 (43편)

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
| 41 | revenue-structure-how-to-read | financial-context |
| 42 | asset-structure-how-to-read | financial-context |
| 43 | cashflow-how-to-read | financial-context |

### 02 DartLab 소식 (6편, 사용자 관리)

| # | slug |
|---|------|
| 01 | dartlab-easy-start |
| 02 | vscode-extension-install |
| 03 | scan-market-finance |
| 04 | company-one-stock-code |
| 05 | search-without-embeddings |
| 06 | magic-formula-korea |

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

- 01 SK하이닉스 (000660) — 2026-04-08 정직 정정 + IS/BS/CF 9년 시계열 표 + 사진 4장 추가 (16,000자, SVG 6장, 사진 4장) — [audit](https://github.com/eddmpython/dartlab/blob/master/.claude/audits/04-skhynix-anomalies.md), [영상 011](https://github.com/eddmpython/dartlab/tree/master/sns/video/output/011-skhynix)
- 02 삼양식품 (003230) — 2026-04-08 시계열 표 + 사진 5장 추가 (12,000자, SVG 5장, 사진 5장) — [audit](https://github.com/eddmpython/dartlab/blob/master/.claude/audits/02-samyang-anomalies.md), [영상 009](https://github.com/eddmpython/dartlab/tree/master/sns/video/output/009-samyang-buldak)
- 03 두산에너빌리티 (034020) — 2026-04-08 핵심 후킹 정직 재작성("9년 적자" 거짓 → "9년 다이어트") + 시계열 표 + 사진 4장 (12,000자, SVG 3장, 사진 4장) — [audit](https://github.com/eddmpython/dartlab/blob/master/.claude/audits/010-doosan-anomalies.md), [영상 010](https://github.com/eddmpython/dartlab/tree/master/sns/video/output/010-doosan-enerbility)
- 04 알테오젠 (196170) — 2026-04-08 단일 종목 깊이 기획 (블로그 + 영상 + 대사 한 세트). 8년 영업적자 → 머크 키트루다 SC 라이선스 → 2025 영업이익률 49.52%. 박순재 17년 인물 서사 (16,000자, SVG 7장 신규 제작, 사진 4장, 시계열 표 IS/BS/CF 3종) — [영상 012](https://github.com/eddmpython/dartlab/tree/master/sns/video/output/012-alteogen)
- 05 HMM (011200) — 2026-04-08 dartlab 3개 엔진 동시 사용 첫 글 (analysis + quant + credit). 9년 5번 사이클, 자본총계 31배 폭증, 베타 0.37/R² 10%/변동성 59% — "시장이 아니라 사이클이 주가를 결정하는 회사" (24,000자, SVG 4장, 사진 3장)

- 06 셀트리온 (068270) — 2026-04-09 인물 중심 서사 (서정진 25년). 5천만원 → 4조원 매출. 명동 사채·합병·무형자산 8.5배 (13,500자, SVG 8장, 사진 4장)
- 07 한화에어로스페이스 (012450) — 2026-04-09 폭약→방산→우주 72년 서사. K9 세계 점유율 52%, 폴란드 672문, CAGR 56.5%, 수주잔고 37조. 방산 자본구조 해설 (13,000자, SVG 7장, 이미지 3장)

- 08 HD현대일렉트릭 (267260) — 2026-04-09 적자→흑자 전환, 숙련공 해자, AI 전력 수요 (10,700자, SVG 2장, 이미지 3장)
- 09 고려아연 (010130) — 2026-04-09 경영권 전쟁이 재무제표에 찍히는 과정 12막 (11,900자, SVG 3장, 이미지 3장)
- 10 에이피알 (278470) — 2026-04-09 화장품+가전 DTC 마진 24% (13,100자, SVG 2장, 이미지 3장)
- 11 크래프톤 (259960) — 2026-04-09 PUBG 현금 추적 + ADK 인수 (10,400자, SVG 4장, 이미지 3장)
- 12 달바글로벌 (483650) — 2026-04-09 scan 발견 + 5A/2D 모순 + 러시아→북미 전환 (10,000자, SVG 2장, 이미지 3장)
- 13 경동나비엔 (009450) — 2026-04-10 scan 발견. 매총이익률 42% 제조업 + CAPEX→FCF 모순 + 연탄→보일러→온수기→퍼네스 72년 (10,500자, SVG 7장)
- 14 대한조선 (439260) — 2026-04-11 scan 발견. OPM 24%(조선업 역대급) + 3번 부도→턴어라운드 + 수에즈막스 올인 + 2,000억→3.3조 (10,500자, SVG 7장, 이미지 3장)
- 15 현대글로비스 (086280) — 2026-04-11 scan 발견. 물류OPM 7%(업종 1.6배) + PCC운임3배 + BYD운송 아이러니 + 보스턴다이내믹스 3.3조 + 지배구조 (12,200자, SVG 5장, 이미지 3장)
- 16 농심 (004370) — 2026-04-11 삼양식품(#02)과 비교. 같은 라면인데 OPM 5% vs 22%(4배). 1위의 저주+해외 질 차이+멀티vs불닭+신라면 툼바. 관통선 단일 인과 규칙 첫 적용. 독자 92점 (13,100자, SVG 7장, 이미지 3장)
- 17 한온시스템 (018880) — 2026-04-11 순이익7배 배당 + 차입11배 + 27년만 첫적자 + EV열관리 + 사모펀드→빅배스→회복. 독자 88점 (12,500자, SVG 5장, 이미지 3장)

- 41 삼성바이오로직스 (207940) — 2026-04-17 CMO 규모의 경제. OPM 13→45%, 매출 0.46→4.56조, 매총이익률 55%. "공장 자체가 제품" 관통선 (11,000자+, SVG 6장)
- 42 현대로템 (064350) — 2026-04-17 K2 전차 턴어라운드. 원가율 104→76%, OPM -11→17%, 부채 206%인데 차입금 608억. "만드는 것이 바뀌면 마진이 바뀐다" (12,000자+, SVG 5장, SEO 100%)
- 43 카카오 (035720) — 2026-04-18 자회사 지주 모델. 3,000만 DAU→자회사 100+→OPM 11%→5.8%→9%. SM인수 순손실 -1.82조. "트래픽 독점이 마진 독점이 아닌 구조" (13,400자+, SVG 5장, SEO 98%)
- 44 뉴스케일파워 (SMR) — 2026-04-18 NRC 인증 유일 SMR. 매출 $31M, 영업손실 -$690M (매출의 22배), 현금 $1.25B (자산 89%). 아이다호 $9.3B 취소→AI 전력 수요→OKLO 비교. "졸업장은 있다, 취업은 아직이다" (16,900자+, SVG 5장, SEO 98%)
- 45 CG인바이츠 (083790) — 2026-04-18 턴어라운드 BB등급. 7년 연속 적자, 매출 424→73→274억 급등-급락-반등. 유상증자로 자본잠식 회피. 자산 2,241억 vs 매출 274억(자산회전율 0.12). dCR-BB 투기등급. "마지막 기회" (17,800자+, SVG 5장, SEO 98%)
- 46 네이버 (035420) — 2026-04-18 검색 광고 지주 모델. 별도 OPM 75.7%→연결 18.3%, 57%p가 자회사+투자로 흡수. 2021Q1 LINE→Z Holdings 15.31조 일회성. OCF 3.1조, 순현금 4.6조, CAPEX 3.66배 공격 투자. 카카오(#43) OPM 2배 비교. "57%p는 비용이 아니라 투자" (15,300자+, SVG 5장, 이미지 3장, SEO 100%)
- 47 에스퓨얼셀 (288620) — 2026-04-18 수소연료전지 부실 위험 + 뉴스케일(#44) 비교. 매출 470→158억(-66%), OPM -95.1%, 매출원가율 127%, 현금 6억, Altman Z 0.20. vs 뉴스케일 현금 1.8조. "인증 없는 적자는 소멸, 인증 있는 적자는 투자" (15,000자+, SVG 5장, 이미지 2장, SEO 100%)
- 48 한화오션 (042660) — 2026-04-18 조선+방산 턴어라운드. OPM -39%→+9.1%, 자본 0.74→6.17조, 수주잔고 34.5조. 방산 16%인데 OPM은 상선 올인 대한조선(#14) 24%의 절반. "방산 프리미엄은 마진이 아니라 생존력에 찍힌다" (15,000자+, SVG 5장, 이미지 1장, SEO 100%)
- 49 오뚜기 (007310) — 2026-04-18 라면 빅3 완성편. 삼양 OPM 22% vs 농심 5.2% vs 오뚜기 4.8%. 원가율 84%(삼양 55%), 해외 15%(삼양 77%). "내수 식품의 OPM 천장은 5% — 탈출구는 해외" (15,100자+, SVG 5장, SEO 100%)

- 50 엔비디아 (NVDA) — 2026-04-18 팹리스 + AI 수요 독점. 매출 $27B→$131B(2년 5배), OPM 16→62%, GPM 75%(소프트웨어급), OCF $64B. TSMC 단일 제조 의존 + AI CAPEX 사이클. SK하이닉스(#01) HBM 공급자, 인텔(#33) IDM 비교. "칩을 설계만 하고 공장이 없는 반도체 회사가 왜 OPM 62%를 찍는가" (19,000자+, SVG 6장, SEO 98%)
- 51 SK바이오사이언스 (302440) — 2026-04-18 코로나 백신 사이클. OPM 51%(2021)→-19%(2025), GPM 61→12%, 매출 9,290→2,675→6,514억. 매출 2.4배 반등했지만 원가율 88% 고착. CAPEX 2,604억 역대 최대. 삼바(#41) OPM 45% 비교. "매출은 돌아왔다 마진은 안 돌아왔다" (15,000자, SVG 5장, SEO 100%)

이전 글들 (LG화학/KT&G/대한항공/삼성전자) 은 audit·영상 동반 없이 작성되어 2026-04-07 정리됨. 새 시리즈는 SK하이닉스부터 시작.

#### 다음 후보 (아이디어 풀)

회사 종합편:
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

### Topic Cluster 맵

pillar(종합편)이 중심, supporting(심화/비교편)이 교차 링크로 연결.

**반도체 클러스터**
- 🏛 Pillar: SK하이닉스 종합 (#01)
- Existing: **엔비디아 (#50, 팹리스 OPM 62% + SK하이닉스 HBM 공급자)**, 인텔 (#33, IDM 비교)
- Supporting 후보: 삼성전자 비교편, 메모리 사이클 심화, HBM 기술 해설

**턴어라운드 클러스터**
- 🏛 Pillar: 두산에너빌리티 (#03)
- Existing: HD현대일렉트릭 (#08, 적자→흑자), **CG인바이츠 (#45, 7년 적자 BB등급 게임사)**
- Supporting 후보: 엔씨소프트 턴어라운드

**식품/소비재 클러스터**
- 🏛 Pillar: 삼양식품 (#02)
- Existing: 에이피알 (#10, 같은 고정비 레버리지), 달바글로벌 (#12, K-뷰티), **농심 (#16, 1위의 저주 vs 삼양 비교)**
- Existing: **오뚜기 (#49, 라면 빅3 완성 — 내수 OPM 천장 5%)**
- Supporting 후보: 오리온 해외 비교편

**바이오 클러스터**
- 🏛 Pillar: 셀트리온 (#06)
- Existing: 알테오젠 (#04), **삼성바이오로직스 (#41, CMO 마진 45%)**
- Existing: **SK바이오사이언스 (#51, 코로나 사이클 — 매출 반등 마진 미회복)**
- Supporting 후보: 유한양행, 한미약품

**K방산/전력 클러스터**
- 🏛 Pillar: 한화에어로 (#07)
- Existing: HD현대일렉트릭 (#08, 수주잔고 메커니즘), **현대로템 (#42, K2 전차 OPM 17%)**
- Supporting 후보: 한화오션 (방산 vs 상선)

**지배구조 클러스터**
- 🏛 Pillar: 고려아연 (#09)
- Supporting 후보: 한화솔루션 (유증 논란)

**게임/콘텐츠 클러스터**
- 🏛 Pillar: 크래프톤 (#11)
- Supporting 후보: 엔씨소프트 (가치함정)

**제조/HVAC 클러스터** (신규)
- 🏛 Pillar: 경동나비엔 (#13)
- Supporting 후보: 귀뚜라미 비교편, 린나이 글로벌 비교

**조선 클러스터** (신규)
- 🏛 Pillar: 대한조선 (#14)
- Existing: HMM (#05, 해운 사이클 = 조선 수요의 근원), **한화오션 (#48, 방산+상선 턴어라운드 — 대한조선 대조편)**
- Supporting 후보: HD한국조선해양 비교편, 삼성중공업

**물류/해운 클러스터** (신규)
- 🏛 Pillar: 현대글로비스 (#15)
- Existing: HMM (#05, 해운 사이클)
- Supporting 후보: CJ대한통운 비교편, 팬오션

**에너지/원전 클러스터** (신규)
- 🏛 Pillar: 뉴스케일파워 (#44, NRC 인증 유일 SMR, 매출 $31M vs 현금 $1.25B)
- Existing: Oklo (#31, 매출 $0 시총 $13B), 두산에너빌리티 (#03, SMR 부품 공급), 한국전력 (#25, i-SMR 개발), **에스퓨얼셀 (#47, 수소연료전지 부실 — 뉴스케일 대조편)**
- Supporting 후보: Cameco (우라늄 공급), BWX Technologies (원자력 부품), 한수원 비교

**인터넷 플랫폼 클러스터** (신규)
- 🏛 Pillar: 카카오 (#43, 자회사 지주 OPM 9%)
- Existing: 네이버 (#46, 별도 OPM 75%→연결 18%, 카카오 대조편)
- Supporting 후보: 카카오뱅크 단독, 카카오엔터+SM 마진 해부

클러스터에 supporting이 부족하면 = 다음 글감 후보.

---

## 거짓 회귀 사례 (2026-04-08)

이번 라운드에 발견한 거짓 19건의 패턴은 [QUALITY_STANDARDS.md §8](QUALITY_STANDARDS.md#8-지난-거짓-사례)에 등록. 같은 패턴 미래 글 작성 시 반복 금지.

## 정리 이력

128편 → 47편 → 44편 → 45편
- 84편 삭제 (과잉 세분화, 템플릿 복사, 제품 설명서, dartlab 광고)
- 7개 → 3개 카테고리 → 4개 카테고리 (04-credit-reports 추가)
- 전역 순번 → 카테고리별 번호
- credit 보고서: docs/credit/reports/ → blog/04-credit-reports/ 이관 (2026-04-03)
