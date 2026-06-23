# 비자명 연결 발굴 (Discovery) — 정본

> 운영자 goal(2026-06-21): *"사람들이 생각 못 한 데이터·연관정보 연결을 전문에이전트 토론으로 발굴해 PRD에 녹여라."*
> 본 문서 = 발굴 정본(02-debate 의 후속 트랙). 6렌즈 발굴 + 적대검증 + 종합. SSOT.

---

## 출처·방법

- 워크플로 `wf_bee9c40e-dc8` (32 agents · 2.7M tokens · 40분).
- **6 발굴 렌즈**(공간경제·charter / 가계레버리지·신용 / 선행지표·레짐 / 이사·내구재 / PF forensic / 횡단·메타) → 25개 후보.
- **4관문 적대검증**(isReal=인과 실재 / isFeasible=가진 데이터로 됨 / isNetNew=가격중복 아님 / isNonObvious=진짜 비자명) + **확신오정렬(cmRisk)** 기준선 = 세션 실측 반례(가격 APT_PRICE조차 현대건설·한일시멘트 firm 회귀에서 탈락, [02-debate-and-verification.md](02-debate-and-verification.md) §8 / [01-current-state-audit.md](01-current-state-audit.md)).
- 결과: **즉시 가능(KEEP) 0 · 조건부(CONDITIONAL) 10 · 기각(KILL) 5** (+ 이름정규화 누락 10은 약후보로 흡수).

## 세션 직접 검증 (load-bearing 코드, PRD 쓰기 전 실측)

| 주장 | 검증 |
|---|---|
| `_crisisDetectors.py:348 _crisisKrHousingStress(data)` 살아있는 detector | ✅ 실재. `:351 apt_yoy=data.get("apt_yoy")` → `:354 krHousingFinancialStress(apt_yoy)` |
| 라이브 콜이 *가격만* 전달(빈 다리 존재) | ✅ `krHousingFinancialStress(housePriceYoy, householdDebtYoy=None)` — `_detectorsMinsky.py:398`. 가계부채 arm 광고됐으나 라이브는 None |
| `_detectorTypes.py:105-106` housePriceYoy·householdDebtYoy 필드 | ✅ 실재 |

→ **B1(최고가치)의 거처가 실재하는 *2-arm 살아있는 detector*임을 확정.** 거래량 divergence arm을 추가할 자리가 코드에 비어 있음.

---

## 무게중심

발굴은 기존 PRD의 **"net-new = 거래량 1축"을 뒤집지 않고 *정밀화*** 한다. 매력적 후보 15개 중 즉시 가능 0, 진짜 생존 1(B1), 약한 조건부 5(B2~B6), 사실상 죽음 4(B7~B10), 기각 5. **"부동산을 붙이면 강해진다"는 환상은 비자명한 변형(charter·전세가율·PF·LEI 패리티)으로 재포장해도 같은 벽**(RTMS 403 · firm↔지역 매핑 결손 · 세션 반례)에 부딪힌다.

핵심 *정정*: 거래량의 **최강 거처가 firm OLS arm(B2)이 아니라 이미 살아있는 crisis divergence arm(B1)** 이다. firm arm은 그 위 약한 upside 로 강등.

---

## Tier A — 즉시 가능(가진 데이터): **비어 있음**

가진 데이터(`listing()` 지역 컬럼 · DART `adres`)만으로 net-new 를 내는 연결은 **0개**. 모든 RE-net-new 축(거래량·전세가율·해제율)은 RTMS 활용신청(현 403)을 선결로 한다. 가진 데이터만으로 시도하는 *공간* 연결은 전부 "본사≠매출지역" 함정. **이것이 발굴의 핵심 산출 — 부동산↔분석의 즉시 가능한 비자명 연결은 존재하지 않는다.**

---

## Tier B — 조건부 (선결: RTMS 활용신청 키 + P1 walk-forward)

| # | 연결 | 메커니즘 | 대상 | plugPoint | 생존 조건(fix) |
|---|---|---|---|---|---|
| **B1 ★최고가치** | **거래량-가격 divergence → 거시 stress** | 거래량이 가격에 *선행*, 거래절벽(가격 평평+거래량 급감)이 single-point 가격지수가 못 잡는 stress (thin-market 호가경직) | `_crisisKrHousingStress`(전국 거시, firm 아님) | `_crisisDetectors.py:348` 위 3rd arm | RTMS 키 → 전국 월 집계 count(전수 raw 금지) + **P1: divergence가 기존 apt_yoy arm 대비 *추가* lead-time 실증**(미통과=가격에 흡수→KILL) + 3개월 연속 급감·종합점수 붕괴 금지 |
| B2 | 거래건수 → 내구재 firm 'volume arm' | 손바뀜=이사≈가전/가구/인테리어 강제교체 수요(자산효과 아님) | 한샘·현대리바트·LX하우시스·KCC·코웨이 등 | `productIndicators.py` realestate source + `_signalsMacroSensitivity.py:489-506` customs arm 옆 | _attempts 측정: 거래량 \|corr\|이 그 firm APT_PRICE·IPI 이겨 greedy top-3 채택 + ≥3사 생존. **세션 반례(가격조차 건설 탈락) 넘는 증거 필수** |
| B3 | 해제율(cancel-rate) lead | 해제 스파이크가 고가 prints 제거 → 가격지수보다 선행 | macro/crisis KR | ★firm `:489` **오류** → `crisis.py:118` data + `_detectorsMinsky.py:398` arm | plugPoint 정정 + 키 + national walk-forward(cancel→APT_PRICE lead lag-corr/granger) |
| B4 | 도시가스 charter 권역 거래량 → 가구형성 | 공급권역 법 고정(본사=매출 예외)·신규계량기 모수 | 삼천리·서울도시가스·대성·경동·인천도시가스 | 가스 exogenous dict + sensitivity arm | ★**가정용 매출 분리추출**(전체매출이면 발전/산업용 희석=kill-point) + walk-forward + 신축거래비중 |
| B5 | 지방은행 charter 권역 거래량/전세가율 → 자산건전성 | 여수신 권역 고정·전세가율=NPL 선행 | BNK·JB·제주은행 | ★credit **macro 입력 0**(점수주입 불가) → **UI 병치 패널**로 재지정 | 1차 거래량만(전세가율은 전월세 수집 후) + credit 점수주입 영구포기 + **3사 walk-forward 선통과**(실패 가능성 최고) |
| B6 | 신축/구축·평형 mix → 가구/인테리어 매출구성 | 거래 *건수* 아닌 *구성*이 후속소비 종류 결정 | 한샘·현대리바트 | B2 별 mix 시리즈 | mix가 B2(총량)·APT_PRICE 통제 후 **부분상관/증분 R²** 유의 + lag≥1 선행. 공선성으로 둘 중 하나만 채택되면 독립가치 0→KILL |
| B7~B10 | charter/LEI PERMIT패리티/PF 변형 4종 | — | — | — | 전부 cmRisk=high·plugPoint 불일치 또는 baseline 역전 미입증. B1~B6에 흡수·격하 |

**Tier B 공통 한계:** 10개 전부 *측정 전*이다. RTMS 403 풀려도 **P1 walk-forward 가 실제 kill 장치** — 가장 강하고 이미 배선된 APT_PRICE 조차 firm 회귀에서 탈락했다. 더 sparse·noisy·짧은 거래량 파생이 그 문턱을 넘는다는 증거 0이며, "그럴듯한 메커니즘 + 0 측정" = 확신오정렬 프로파일.

---

## 기각 카탈로그 (확신오정렬 박제 — *매력적인데 왜 틀렸나*)

| KILL | 매력 | 치명상 |
|---|---|---|
| 가구·인테리어 **charter화** | "지역 거래량→지역 이사→가구수요" 공간 직결이 깔끔 | 한샘 등은 **전국 유통=본사≠매출**, charter 예외 아님. APT_PRICE 이미 배선(`exogenousAxes.py:225`)=net-new도 아님 |
| **전세가율→건설PF** 디폴트 선행 | 깡통전세→미분양→PF부실(둔촌주공/태영) 서사 강렬 | 미분양 RTMS **부재**(HUG 별도)·전세는 전월세 별도수집(스코프 밖)·`pfExposure`(`construction.py:110-112`)는 **키워드 카운트** 정량 아님 |
| 전세가율→PF **credit forensic** | file:line·노트코드 인용으로 *정밀해 보임* | `NT_D827580`은 PF전용 아닌 우발부채 *광역버킷*·credit 우발부채축은 *공시 부피*·전세가율↑ 부호 자주 **반대**(전세강세=매매 선행). 정밀 인용이 mis-spec 가림 |
| price-volume divergence **customs arm 복제** | "customs 옆 평행 복제" 공학적 깔끔 | 시멘트는 APT_PRICE가 **1순위** 이중배선(`:178`+`:293`). customs는 firm→HS(공간무관)라 거래량 시계열과 *메커니즘 다름* — '평행' 거짓. (단 B1은 crisis arm이라 별개로 생존) |
| **jeonseRatio**를 housingStress 슬롯에 | docstring이 "가격→전세→대출" 3링크 약속, impl 2-arm(빈 다리) | jeonse 데이터 전무(grep 0)·전월세+매매 단지조인(403+OOM)·전세가율은 가격 *파생*이라 기계적 공선·threshold-vote서 거의 항등식 |

**박제 교훈:** 5 KILL 이 같은 실수 — 메커니즘의 그럴듯함으로 강도를 매기고 (1) 데이터 실재(전세/미분양 부재) (2) 코드 실재(`NT_D827580` 정체·`pfExposure` 키워드카운트·credit macro입력 0) (3) 세션 반례를 grep으로 검증 안 함. **비자명함과 설명력은 별개 — 비자명할수록 부호 오류·데이터 부재를 숨기기 쉽다.**

---

## ★최고가치 1개 — B1 (거래량-가격 divergence → `_crisisKrHousingStress`)

**왜 유일 생존(dartlab만 가능·진짜 비자명·feasible 셋 충족):**
1. **dartlab만 가능** — `_crisisKrHousingStress`는 이미 housePriceYoy+householdDebtYoy 2-arm으로 *살아있는* detector(세션 검증). 거래량 divergence arm 추가 = 신규 발명 아닌 묻어둔 회로 확장. 외부 누구도 이 골격 없음.
2. **진짜 비자명** — 통념은 부동산을 "가격(자산가치)"으로 본다. "거래량이 가격에 *선행*하고, 거래절벽이 single-point 가격지수가 구조적으로 못 잡는 stress"가 load-bearing 비자명(thin-market 구조, folk 아님).
3. **feasible(다른 9개와 결정적 차이)** — B1은 firm→region 공간조인이 아닌 **전국 거시 arm**. 본사≠매출·시군구 결측·전수 raw OOM 함정 **전부 무관**(집계 count만 bake). cmRisk **medium**(유일) — 세션 반례는 *firm 횡단 OLS lane* 결과인데 B1은 *미회귀 stress-label lane*에 살아 직접 kill 적용 안 됨.

**주의 단서:** B1조차 무조건 KEEP 아님. RTMS 403 해제 + P1 walk-forward 로 divergence 의 *추가* lead-time 실증 필요(미통과=가격에 흡수→KILL). 단 *측정 가능 위치·함정 회피·별 lane* 유일 후보라 최고가치.

---

## 발굴 총평

CONDITIONAL 10 + KILL 5 = 15개 중 즉시 가능 0, 진짜 생존 1(B1), 약한 조건부 5(B2~B6), 사실상 죽음 4(B7~B10). **KILL 이 많은 것이 발굴의 실제 산출** — 부동산↔분석의 비자명 연결 대부분은 *비자명하기 때문에 더 잘 틀린다*.
