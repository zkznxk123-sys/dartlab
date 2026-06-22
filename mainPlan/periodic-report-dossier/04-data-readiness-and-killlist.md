# 04 — 데이터 준비도 + 컷 목록

> 모든 숫자는 그 DART 공시 + as-of 로 역추적. 결측은 `—`/미공시/해당없음/부분, 절대 0 아님.

## 1. 데이터 준비도 4분류

### STRUCTURED-READY (P0/P1, 새 fetch 0)
| 데이터 | 출처 | 커버리지 | 주의 |
|---|---|---|---|
| `rcept_no` (모든 report 행) | report parquet 전 행 | ~100%(접수 보고서) | browser 경로에서 SELECT 누락 — 추가만 |
| `ShareholderReturnYear[]` 전체(소각/취득/처분/기말) | `report.shareholderReturn` | 보통주·총계·4분기 filers | **소형주 다수 null → 빈상태가 default 렌더** |
| lossPct = lossBook/bookTotal | `HoldingsDialog` L120 즉석 | 전 2,800사(장부가 항상 존재) | 시장조회 불필요, 가장 깨끗 |
| control-shift (`shPeriods named[]` diff) | `buildShareholderPeriods` 전 기간 | 법인·기관(개인 익명 집계) | 연/반기 축(Q1/Q3 sparse), 명시 기간 라벨 |
| 멀티연도 `wf[]` 자기이력 | 이미 메모리 | 임직원 공시사 | 연 단위, 평균급여 4분기만 |

### NEEDS-PARSING (P1/P2, 엔진 + CI bake)
| 데이터 | 상태 | 커버리지 | 진짜 작업 |
|---|---|---|---|
| R&D 집약도 | `calcRndExpense` **완성 엔진**(재graduate 금지) | 59.7%(IS 50·SGA 774·both 50). 40.3%=진짜부재(NAVER/현대차 자본화·금융사) + 미공시 | **CI-baked rndIntensity 컬럼** + reportSource 5번째 read + `report.rndIntensity(code)`. 로컬=`calcRndExpense` live, 동일 parquet fallback |
| 인적자본 백분위 | `scanValueAdded`/`computeSalaryVsRevenue` dead-wired | **교집합 N**(payroll∩employee∩opIncome, 소형주 먼저 탈락). 글로벌 N 아님 | baked 분위 배열{N,asOfYear,gate} + 단일시점 1행. cross-universe-percentile 패턴 |

### NARRATIVE-ONLY (P3, 원문 인용만)
| 데이터 | 상태 |
|---|---|
| 가동률/생산능력/생산실적 | 구조화 컬럼 0, scan parquet 없음, `sectionMappings rawMaterial` 자유 텍스트 → **원문 발췌 + as-of, 절대 수치화 안 함**. zero 추출일 때만 ship |

### BLOCKED (범위 밖, parked)
| 데이터 | 이유 |
|---|---|
| 세그먼트 매출 mix | 4.6%(67사)만 axis-tagged clean, 8.3% low-trust, 87% unusable → 범용 카드=95% 쓰레기. `segmentRndExtraction` _attempts 잔류 |
| 원재료 가격변동 표 | 섹터별 표 형태 상이, 신뢰 범용 컬럼 아님 |
| 자사주 취득원가 | 컬럼 없음(소각 "가치" 추정만 가능) |
| 질권/담보(pledge) | gather 데이터에 필드 없음 → 침묵 |

## 2. 컷 목록 (이미 토론에서 죽인 것 — 부활 금지)

| 컷 | 이유 |
|---|---|
| 통합 "기업 실체" 6번째 레일 | 덕지덕지 누적·중복 fetch·FinFullscreen 와 경쟁 |
| 범용 세그먼트 카드 | 4.6%만 clean = 95% 회사 쓰레기/`—` |
| 가동률/생산능력 숫자·추세선·차트 | 구조화 데이터 0 = 날조 |
| 원재료 가격 패널 | 섹터별 비신뢰 |
| 시총분모 총주주환원율(P1 헤드라인) | gov price T+1·2020+ = stale·거짓정밀. FCF 분모(returnToFcf)는 P3(CF 배선) |
| `contribShare` (mktcap/PER 함축 순익 분모) | 추정의 prime fact 둔갑. 보고 `fin.is.net` 재배선 또는 삭제 |
| 우측 레일 스파크라인(R&D·출자 장부가합) | 레일 그래프 금지 + 장식. 텍스트 추세(↑/↓/→)로 |
| 상호출자 K건 헤더 배지 | "순환출자=K" 오독(다단 미탐지) → 다이얼로그 ↔ 안에서만 |
| `capitalChanges.reduction` 교차검증 사용자向 | 두 숫자 노출=덕지덕지 → 침묵 데이터품질 게이트로만 |
| same-year "취득의 X% 소각" 비율 | buybackQty=0·buybackCancel>0 케이스 undefined → 누적 취득vs누적 소각 |
| 섹터 분포 사실("소각하는 회사 X곳") | v1 defer(industry-lab 경계 한 발) |
| 임원/직원 보수배율 카드/섹션 | PEOPLE 디테일 한 줄로만(거버넌스 톤 유혹) |
| 4줄 패널 헤더 | 2줄 cap(lossPct 항상 + 1) |
| 모든 종합점수/등급/레이더 | NEVER-CLAIM. credit/eco 축이 이미 소유 |
| R&D vs payout 2축 scatter/결합 위젯 | 인접(인력 R&D 행 + 주주환원 payout)이 곧 기능, 결합 안 지음 |
| sector-median 밴드 *카드 내 재계산* | industry-lab `recipes.industry.rdIntensityTrend` 소비(fork 금지) |

## 3. NEVER-CLAIM (00 §5 SSOT 의 실행 가드)

- grep 가드(G3-style) 신규 키 확장: `우량`·`매수`·`매도`·`좋은 고용주`·`주주친화`·`강한`·`우수`·`건강한` = 차단 토큰.
- reads-as 문장 = non-null 토큰 + **고정 연결어 기계 조립**, 형용사 0.
- 글로서리 = 일반 서술, 절대 *이 회사* 품질 언급 안 함.
- baked 배열 = 축별 실제 교집합 N·asOfYear·gate(글로벌 N 금지).
- 결측 = first-class `—`/미공시, push 전 3/6 소형주·무배당·첫배당 데모로 빈상태 검증.
