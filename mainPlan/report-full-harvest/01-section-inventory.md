# 01 — 사업보고서 전 섹션 인벤토리 (spine taxonomy 실측)

> 출처: `src/dartlab/providers/dart/panel/spine/spineData.py` (정부 문서 표시순서 정본) + 8개 업종 panel parquet 실측(삼성전자·현대건설·삼성중공업·셀트리온·네이버·POSCO·LG화학·한화에어로).

## 사업보고서 12장 구조 → Tier 매핑

| 장 | 섹션 | Tier | 상태 |
|---|---|---|---|
| I. 회사의 개요 | 회사개요·연혁·자본금변동·주식총수·정관 | B/C | 일부 keyed(TOT_STK), 대부분 메타 |
| **II. 사업의 내용** | 1.사업개요 | C | narrative |
| | 2.주요 제품·서비스 | C | 자유서식 표 |
| | 3.원재료·생산설비(생산실적·가동률) | C | 자유서식, **가동률 data 0=컷** |
| | **4.매출 및 수주상황** (수주총액·기납품·수주잔고) | C | 자유서식 fragile 5/10 → **flow로 대체** |
| | 5.위험관리·파생 | C | narrative |
| | 6.주요계약·연구개발(R&D) | C | R&D비용 일부 acode·정성은 컷 |
| | 7.기타 참고 | C | narrative |
| **III. 재무에 관한 사항** | 재무제표(IS/BS/CF) | — | 별도 SSOT(financeSource) |
| | **연결/별도 재무제표 주석** (NT_D8xxxxx) | **A** | **회사당 179~507표 XBRL — 골드마인** |
| | 배당에 관한 사항(DIVIDEND) | B | dividend.parquet |
| | 증권발행 자금조달(INC_STAT·SUB_*) | B/C | capitalChange 일부 |
| IV. 이사 경영진단(MD&A) | 재무상태·유동성·부외거래 | C | narrative(정성, 컷) |
| V. 회계감사인 감사의견 | 외부감사·내부통제 | B | audit*.parquet |
| VI. 이사회 등 기관 | 이사회·감사제도·주총 | B | outsideDirector |
| VII. 주주 | 최대주주·5%이상 | B | major/minorityHolder |
| VIII. 임원·직원 | 인력현황·임원보수 | B | employee·executivePay |
| IX. 계열회사 | 계열현황 | B/C | 일부 |
| X. 대주주 거래 | 대주주거래내용 | C | narrative |
| XI. 투자자보호 | 공시진행·우발부채·제재·기준일후 | C | narrative |
| XII. 상세표 | 연결종속·계열·**타법인출자**·**연구개발실적** | B/C | investedCompany(B) |

## Tier A — 재무주석 XBRL 골드마인 (핵심 미활용 자원)

panel `xbrlClass`의 D-코드로 언어무관 식별(`xbrlCellsFromContent`가 acode/ACONTEXT 디코드). 실측 표 수: 회사당 **179(네이버)~507(한화에어로)**개. 이미 구현은 **2개뿐**(비용성격별·부문매출).

| 주석 | D-코드(예) | metric | 추출 |
|---|---|---|---|
| 비용 성격별 분류 ✅ | — | 원재료·인건비·감가·외주 비중 | **live** (noteSeries.cost) |
| 부문별 매출 ✅ | — | 부문 매출믹스 시계열 | **live** (noteSeries.segment) |
| 차입금 명세 | D822400 | 단기/장기·이자율·통화 | acode 직독(P1) |
| 사채 | D822450 | 만기·고정/변동 | acode 직독(P1) |
| 리스(사용권자산·리스부채) | — | 리스부채÷자본 off-BS 레버리지 | acode 직독(P1) |
| 충당부채 | — | 판매보증·소송·복구 잔액 추이 | acode 직독(P1) |
| 관계기업 투자(지분법) | — | 지분법손실·손상 | acode 직독(P1) |
| 매출채권 | — | DSO·대손충당률 | acode 직독(P2) |
| 재고자산 | D826380 | DIO·평가손실 | acode 직독(P2) |
| 종업원급여/확정급여 | D834480 | 연금 적립비율 | 단일표 직독(P2) |
| 법인세 | D835110 | 유효세율 | 단일표(IS 흡수, P2) |
| 재무위험관리(민감도) | D822380/90 | 환·금리 ±충격 | **횡단 비교 컷**(가정 불일치) |

> **인코딩 비대칭(segmentRnd 실측)**: 추출 품질은 데이터 유무가 아니라 *XBRL 인코딩 양식*으로 갈린다. **단일축 lineitem 표(부채만기·법인세·종업원급여)=고신뢰**. **다축 합성(부문×지표=영업이익률 매트릭스)=fragile**(행-라벨형 헤더 artifact). → 단일표 단위로만 surface, 다축 합성은 컷.

## Tier B — 이미 추출·배선 17종 (surface만 남음)

`reportSource.ts`가 전부 런타임 직독 배선 + scan parquet 횡단 격자 보유:
`employee`(160K rows)·`dividend`(638K)·`treasuryStock`(509K)·`investedCompany`(16MB)·`majorHolder`(436K)·`minorityHolder`(57K)·`executivePay*`(58K)·`auditContract/Opinion`·`corporateBond/shortTermBond/commercialPaper`·`capitalChange`·`outsideDirector`.

## Tier C — II.사업의 내용 자유서식 (휴리스틱·승인 게이트)

전업종 표 보유 실측이나 XBRL 태그 0·레이아웃 업종별 상이. **수주잔고**: 표본 10사 중 5사 클린(조선·방산 강, 건설·과분할 약). → 사업보고서 narrative 직접 긁기 대신 **수시공시 신규수주 flow**([[project_order_flow_scan]], 810사 ≥90% 파싱)가 신뢰선.
