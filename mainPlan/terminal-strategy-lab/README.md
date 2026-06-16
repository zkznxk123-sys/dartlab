# Terminal Strategy Lab — 주가차트=시간기계 전략 백테스팅 PRD

상태: v0.1 (2026-06-16 — 3라운드 전문 토론 + 적대 검증 수렴. **착수 = 운영자 go**)
범위: 메인 주가 차트 위에서 동작하는 **전문 백테스팅 전략 랩** — 다전략 동시 시각화·비교·조합·리플레이 walk·(단계적) 커서바인딩 리밸런싱·미래 시뮬 연속. 옛 `terminal-chart-suite/03-backtesting-strategy-tester.md`를 **supersede**(폐기·흡수)한다.

---

## 0. 한 줄 결정

**백테스팅은 차트 하단의 손님(strip)도, 별도 모달도 아니다 — 주가차트 *자체*가 전략을 검증하는 시간 기계다.** 차트 가운데 세로선이 "지금(asOf)", 왼쪽은 실현된 과거(리플레이로 전략이 *그 시점 데이터만으로* 결정), 오른쪽은 fan으로 펼쳐지는 미래. 전략 A·B·A+B가 같은 시간축·같은 가격축 위에 곡선과 마커로 겹쳐, "이 전략 이렇게·저 전략 이렇게·둘을 조합하면 이렇게"가 *눈으로* 증명된다. 이 시간 기계는 과거(백테스트)에서 미래(시뮬레이터)로 끊김 없이 이어진다.

## 1. 왜 이 PRD인가 (옛 03 폐기 사유)

운영자 판정: 현 백테스팅 = **"드롭다운 6개뿐"(능력 약함) + "안 읽힘"(UX)**. 옛 03은 ① 결과를 22px strip + 별도 모달로 *분산* ② 단일 전략 1개만 ③ 설정(사라지는 팝오버)·결과·상세가 한 화면에 못 모임 — 구조적으로 "전략을 눈으로 비교"가 불가능했다. 본 PRD는 *배치 개선이 아니라 개념 재정의* 다: 차트를 전략 검증의 표면(canvas)으로 승격하고, 다전략·조합·시간 walk·미래 연속을 차트 메커니즘으로 박는다.

## 2. ★단방향 시간축 규칙 (불가침 — 기존 아키텍처 승계)

```
 [과거: 실현 시계열]      asOf       [미래: 결정론 시나리오]
 ◀── 리플레이 walk ──┃── Play fan ──▶
   Strategy Lab(본 PRD)  ┃   scenario-simulator/05 (미래)
                         ┃
   같은 차트 · 같은 재생 엔진 · mode:live|simulate 상호배타
```
- **과거 replay** = "있는 시계열을 idx까지만 보여주기". **미래 Play** = "사전계산 결정론 path를 t까지만 보여주기". **메커니즘 동일**(scenario-simulator/05 §0). 재생 엔진(타이머·렌더·컨트롤) 공유, 별도 차트 인스턴스 0.
- **Strategy Lab ⟶ 시뮬 단방향**: 본 PRD는 시뮬을 *상류 의존으로 선언하지 않는다*. 시뮬 Play(05)가 본 랩의 포트 상태를 *초기조건으로 소비*한다(역참조 0).
- **미래 path 데이터는 시뮬 코어(`simulate/` DAG) 소유** — 본 랩은 mode 토글 + fan 렌더 *계약*까지, 실제 미래 path는 시뮬 코어 졸업 후(09 Phase 0).

## 3. ★로컬/퍼블릭 공동배선 (불가침)

- **퍼블릭(landing, 서버0, 브라우저)** = floor. 모든 단계가 브라우저 TS 엔진(`rt.price.loaded` 캔들, 동기 ms)으로 완결. `env.kind` 분기로 floor에서 사라지면 안 됨.
- **로컬(:8400 백엔드·Python)** = bonus. floor를 *대체 않고 보강*만(walk-forward·CPCV·다종목 정밀). DSR/PBO 등 folk-stat 수치는 로컬·다전략 게이트 뒤.

## 4. 단계 지도 (각 단계가 실한 목표진입 — 얇은 MVP 아님)

> 단계는 *기능을 깎아 줄인 MVP가 아니라*, 회귀위험을 시간축 단방향으로 격리한 **확실한 진입 경로**다. 종착 = 전문 전략 랩 전체.

| 단계 | 능력 | 엔진 영향 | 위험 | 산출 |
|---|---|---|---|---|
| **P1 다전략 캔버스** | N전략(≤3) 동시 마커+에쿼티 공유축, 동일가중 조합 곡선, 분산효과 시각증거, 정직 리플레이 walk | `runPass` 무수정·N회 호출 | 중(btLayer 공유축 draw) | "A·B·A+B 눈으로 비교" |
| **P2 포지션·거래 정밀** | 손절/익절/트레일링, 포지션 사이징(vol-target·fixed-frac), MAE/MFE·expectancy·R-multiple·롤링지표·월별 히트맵 | `runPass` 확장(stop·sizing) | 중~높 | "전문 거래 분석" |
| **P3 커서바인딩 리밸런싱** | 리플레이 walk 중 t까지만 보고 가중치 변경, append-only, 반복재생 카운터 | `runComboBacktest` 별도 패스 | 높(부분노출 일반화) | "그때그때 리밸런싱" |
| **P4 강건성(로컬 bonus)** | walk-forward(refit)·민감도 히트맵·Monte Carlo 거래 재배열·CPCV — 서술/곡선, DSR/PBO 수치는 게이트 | Python 배선 | 중(parity gate) | "과적합 진단" |
| **P5 미래 연속** | mode:live\|simulate, asOf 포트→시뮬 초기조건, 미래 fan band | 재생엔진 공유·시뮬 코어 소비 | 중(코어 졸업 의존) | "과거→미래 끊김 없음" |

상세 = 03-staging-roadmap.md. 각 단계 AC·타입계약·테스트매트릭스 동봉.

## 5. 문서 지도

- **[00-product-prd.md](00-product-prd.md)** — 제품 정의·사용자·"전문 백테스팅이란 무엇인가"(canon 개념 카탈로그 adopt/조건/reject)·목표 종착·성공지표(차트 수 아님).
- **[01-mechanism-architecture.md](01-mechanism-architecture.md)** — 메커니즘을 차트에 박는 법(extendData draw + 리플레이 절단 척추 + mode 토글)·엔진 재사용·데이터 계약·적대검증 정정 2함정.
- **[02-ui-ux-design.md](02-ui-ux-design.md)** — 확정 UI/UX(전략 콘솔·차트 오버레이·결과 표면·리밸런싱 UI·미래 연속)·타이포·ASCII 목업(단계별).
- **[03-staging-roadmap.md](03-staging-roadmap.md)** — 단계별 AC·타입계약·영향파일/함수·테스트·롤백·회귀위험.
- **[04-honesty-and-rigor.md](04-honesty-and-rigor.md)** — 통계 정직 SSOT(§0.6 승계 + 다전략/리밸런싱/selection 신규 가드)·look-ahead·folk-stat 천장·로컬 bonus 경계.

## 6. 경계 (불가침)

- **미래(Play·fan·드라이버 DAG·valuation)** = `scenario-simulator/`. 본 랩은 미래 path를 *생성*하지 않고 mode 전환으로 *연결*만.
- **공시 레일·지수 차트** = `terminal-chart-suite/01·02`. 본 랩은 백테스팅(옛 03)만 흡수.
- **DSR/PBO·RunSpec SSOT** = 본 PRD(04)로 이관, 시뮬이 재사용.
- **UI 토폴로지** = `ui/packages/surfaces/src/terminal/`(포트=contracts·런타임=runtime).

## 7. 착수 게이트

운영자 go 후 P1부터. UI 변경이므로 **commit 자율·push 운영자 명시 승인 후**(스크린샷 눈검수·공개 터미널 무중단). 본 트랙(PRD 작성)은 *문서만* — commit 자율.
