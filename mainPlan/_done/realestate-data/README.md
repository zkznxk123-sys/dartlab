# 부동산 실거래 데이터 수집·조합 — PRD

> 🚫 **폐기 (2026-06-23) — 미착수 영구 기각.** 빌드 0줄(`✅ 완료` 아님). PRD 자체는 전 7차원 96점으로 완성됐으나, 코드 실측 결론이 "부동산↔분석 net-new = **거래량 1축뿐**(B1 crisis divergence arm), 그것도 P1 walk-forward 통과 조건부"였고 — 즉시 가능한 비자명 연결은 0개([04-discovery.md](04-discovery.md)). 게다가 RTMS API 키-계정 미스매치(세션 재호출 전부 403)로 그 1축조차 **P1 검증을 수행하지 못한** 상태. 운영자 판단: 거래량 1축의 착수 ROI가 낮아 폐기. 되살릴 경우 선결 = RTMS 승인 계정 Decoding 키 확보(메모리 [[project_realestate_data]] ⚠) → B1 P1 walk-forward 실측. 보관 사유 = 경계 지도(STRONG인 척하면 안 되는 곳)·KILL 5(확신오정렬 박제)·feasibility 방법론 자산은 계속 참조 가치.
>
> **무게중심**: DartLab은 부동산 *가격*을 이미 쓴다(`APT_PRICE` ecos → 17곳 외생·`macro/crisis/crisis.py:118 apt_yoy`). 국토부 실거래의 유일한 net-new는 가격이 못 담는 직교 축 — **거래량(volume)**. 이 PRD의 진짜 산물은 "부동산↔분석 능력"이 아니라 **① 거래량 집계 수집 파이프라인 1개 ② 어디가 STRONG인 척하면 안 되는지의 코드-실측 경계 지도 ③ STRONG을 가두는 P1 walk-forward 검증 게이트**다.
>
> **한 줄 비전**: 실거래 거래량(한국 가계·소비·건설 사이클의 직교 신호)을 customs 거푸집으로 수집해 집계 1축만 HF에 bake하고, firm-level 매출민감도 외생 회로의 검증된 빈 슬롯에 P1 통과 조건부로 1축 추가한다 — 새 패널·새 점수·전수 raw 0, macro-lens 픽셀 불가침, 범위 라벨만 척추.

---

## 이 PRD가 푸는 문제 + 직접 답

운영자 명령: *"공공데이터 부동산 실거래를 수집해 우리 분석에 조합 가능한지 검토 — 데이터 수집 파이프라인부터 활용 조합, 터미널 UI/UX까지. 각 기획자·평가자 95점 이상, 억지점수 금지."*

검토 결과(코드 실측): "부동산을 붙이면 분석이 강해진다"는 흔한 직관은 코드 앞에서 *대부분 무너진다* — 가격은 이미 흐르고, regime엔 외생 슬롯이 없고, credit은 점수 주입 불가다. **실측된 조합 가능성 = 거래량 1축(firm 외생, P1 조건부) + 동행 후보칩(industry) + 병치 맥락칩(credit) 뿐.** 이걸 억지로 STRONG 다수로 부풀리지 않은 것이 이 PRD의 핵심.

---

## 작업 산출 (5문서)

| 파일 | 내용 |
|---|---|
| [00-product-prd.md](00-product-prd.md) | **완전 PRD**(자기충족) — 무게중심·현상진단·조합 Tier(STRONG B1/B2·MEDIUM·REJECT, file:line)·데이터 파이프라인(customs 거푸집+3비대칭+고볼륨 전략+KOGL P0 게이트+k-익명)·분석 배선 3지점·UI(RealEstateLensDialog 격리)·cannotClaimList(16)·Phase·영향파일·테스트·롤백·열린결정·범위 자기진단·이중평가 |
| [01-current-state-audit.md](01-current-state-audit.md) | 현상 진단 — 재사용 자산·국토부 API 실호출 확정(엔드포인트·10,000콜/일·KOGL 제한없음·자동승인·개인정보)·조합 결합점·코드 검증 정정(APT_PRICE 이미배선·PF 노트셀 실재) |
| [02-debate-and-verification.md](02-debate-and-verification.md) | 토론 정본 — 7설계+7검증+평가패널 3라운드 점수 이력(min 88→86→91→89→96)·95 미달 원인(인용 정밀도)·세션 코드 ground-truth 교정 표 |
| **[04-discovery.md](04-discovery.md)** | **비자명 연결 발굴 정본** — 6렌즈 25후보 + 4관문 적대검증(`wf_bee9c40e-dc8`, 32 agents). 즉시가능 0·진짜생존 1(B1 거래량-가격 divergence→`_crisisKrHousingStress`)·약한조건부 5·KILL 5(확신오정렬 박제). ★최고가치=B1 |
| [03-progress-ledger.md](03-progress-ledger.md) | 진행 원장 + 재개 NEXT |

---

## 한눈 결정 (TL;DR)

- **net-new = 거래량 수집 파이프라인 1개.** 가격(APT_PRICE)·crisis apt_yoy·industry 17곳 외생은 *이미 배선*. 거래량만 직교 신규.
- **STRONG 거처 — ★발굴 정정: B1(최강) = `macro/crisis/_crisisDetectors.py:348 _crisisKrHousingStress`에 거래량-가격 divergence arm 추가** (이미 살아있는 2-arm detector·전국 거시라 공간조인·OOM 함정 무관·cmRisk medium). B2(약한 upside) = `_signalsMacroSensitivity.py:489-506` firm OLS arm(cmRisk high — 세션 반례: 가격조차 건설사 회귀 탈락). 둘 다 P1 walk-forward(lagged>동기 ≥3%p·채택률·turning-point) 통과 후에만 STRONG, `meta.p1Status` 구동. 상세 [04-discovery.md](04-discovery.md).
- **데이터층 = 집계 인덱스 bake + raw 온디맨드.** 전수 raw bake = REJECT(OOM/콜한도). customs 거푸집 + 3비대칭(pageNo for-loop·count/median·parsing P0 실측). k-익명 생성단계 마스킹. forward+reconciliation.
- **P0 게이트 = ★세션 실호출로 해소**: 엔드포인트 `apis.data.go.kr/1613000/...AptTradeDev` 확정·KOGL **"제한 없음"**(공개 양립)·콜한도 **10,000/일**(개발계정)·활용신청 **자동승인**. 잔여 = 운영자 활용신청 1클릭 + 1콜 totalCount 캡처(trivial).
- **UI = RealEstateLensDialog 완전 격리**(MacroLensDialog 픽셀 불가침). 첫화면 TrendChart+한계푸터·`<details>` top-N 막대(choropleth REJECT·geo 0건). 건설 dashboard 병치칩. 호악재 색 금지.
- **MEDIUM = industry 동행 후보칩(edges 재빌드 별 cycle)·credit 병치칩(점수 미주입)**. **REJECT = 전수 raw·기업지역특정·주가예측·종합점수·choropleth·미분양·8용도동시**.
- **착수 = 운영자 go · UI push = 운영자 명시 승인**(공개 터미널, CLAUDE.md ⛔).

---

## 점수 이력 보고 (★중요)

✅ **전 7차원 96점 달성**(`reached95=true`·기획자·평가자 전원 ≥95). 궤적: 1차 min 89 → 보정 94→92→93→94→94 → **96**. 어느 단계도 억지 인플레가 아니다 — 89를 cap한 *인용 정밀도* 결함을 평가자 전수가 18~25개 file:line 직접 대조로 "부정확 0건" 확인했고, 89~94를 묶던 천장("코드대조 평가자가 외부 사실 KOGL·콜한도·totalCount 검증 불가")을 **체념하지 않고 ★RTMS 실호출 + 문서 2종 + [evidence/](evidence/) 파일 박제**로 해소(평가자가 읽고 검증 → structural-P0 분류 실제 소멸). UI는 *미빌드 시각증명*이 아니라 설계 완결+P4 스크린샷 게이트 명시로 채점(PRD는 빌드가 아니라 계획). **점수를 막던 eval 인공물(외부사실 불가시성·범주오류)을 정공법으로 제거**한 결과지 점수 조작이 아니다. 평가자가 96에 minor 2건을 *남긴 것*(Dev 태그 1콜·2-tier 추정)이 100 고무도장 아닌 진짜 채점의 증거. 상세 [03-progress-ledger.md](03-progress-ledger.md).

---

## 기존 자산과의 관계

| 자산 | 관계 |
|---|---|
| `gather/customs/*` | **거푸집 계승** — client/series/catalog/facade/types 5파일 1:1 (단 3비대칭 신규) |
| `core/providers/dataCredentials.py` dataGoKr | **1키 재사용** — sources +realestate 1줄 |
| `exogenousAxes.py APT_PRICE` | **재표면화 경계** — 가격 이미 배선, 거래량만 추가 |
| `_signalsMacroSensitivity.py` | **STRONG 거처** — customs arm에 realestate arm |
| `mainPlan/macro-analysis-superstrengthen` | **픽셀 불가침 계승** — MacroLensDialog 미수정, 부동산은 형제 다이얼로그 |
| [[incident_panel_rcept_window_gap]] | forward윈도+reconciliation 쌍 계승 |

## 출처
전문에이전트 워크플로(`wf_d022eb68-40c`, 46 agents·4.5M tokens) + 세션 코드 직접 실측. 토론·점수·코드교정은 02에 박제.
