# Terminal Strategy Lab — panel을 두 방향으로 자른 백테스트 OS

상태: v0.2 (2026-06-18 — 8 전문에이전트 2라운드 토론 + 적대검증 수렴. **착수 = 운영자 go**)
범위: 한국 DART 공시·재무 **panel** 위에서 동작하는 **세계 최고 수준의 무료 EOD 백테스트 OS**. 두 입구 — ① 단일종목 시간기계(다전략·펀더게이트·미래연속) ② 유니버스 크로스섹셔널 랭킹(17년 가격보존). 옛 `_done/terminal-chart-suite/03-backtesting-strategy-tester.md`를 **supersede**(폐기·흡수)한다.

---

## 0. 한 줄 결정 (v0.2 — 무게중심 역전)

**세계급의 축은 *능력*이 아니라 *한계 표기*이다.** TradingView·QuantConnect·Bloomberg는 능력은 위지만 한계 표기는 toy다(생존편향 불투명·단일 path Sharpe를 유의인 양·folk-stat 숨김). 본 OS는 그들이 *상업적으로 숨기는 것*(생존편향 밴드·selection 카운터·OOS 강제·folk-stat 천장)을 1급 표면으로 박는다 — **그 자리는 비어 있다.**

제품은 **panel을 두 방향으로 자른 두 기계**다:
```
                    panel (전상장사 재무·가격 시계열 격자)
                            ╱                  ╲
              시간 방향 절단                     횡단면 방향 절단
        ┌─ 단일종목 시간기계 ─┐            ┌─ 유니버스 랭킹 기계 ─┐
        │ 과거 replay→asOf→fan │            │ 매 리밸 그날 데이터로 │
        │ "그 시점까지만 보고"  │            │ "전종목 랭킹→상위 보유"│
        └─────────┬───────────┘            └──────────┬──────────┘
                  │   단방향 drill-down (Q5 행 클릭 → /terminal?symbol=)   │
                  └───────────────◀──────────────────────────────────────┘
        공유 = PIT 공리(decisionT<fillT)·헬퍼6종·공유절대축 draw·"추천 아님" 봉인
```
"시간기계(주가차트 자체가 전략을 검증)"는 **세로 절단면의 이름**일 뿐, 전체를 묶는 서사가 아니다. 두 기계를 묶는 건 시간기계가 아니라 **panel 위의 동일한 PIT 공리**다.

## 0.1 ⛔ NEVER-CLAIM (레드팀 7선 — grep 게이트, 04 §6)

"세계급"이 *거짓이 되는* 선. 위반 = 04 §6 grep 차단:
1. **"세계급/기관급 백테스팅"** 단어 자체 (코드네임·UI·문서 0). G3 봉인의 우회 동의어. 자기규정 = "세계 최고 수준의 무료 EOD 백테스트 OS".
2. **"survivorship-clean/bias-free"** 무수식. 가격 봉은 보존이나 폐지 *사유* 미구분 → "가격 보존형 유니버스(사유 미구분)".
3. **"total return/실제 수익"** — 배당·정조정 제외 기본 → "가격수익(배당·정조정 제외)".
4. **단일종목 Sharpe/CAGR를 "전략 성과"로** — in-sample 한 path. → "이 구간·이 종목에서 이 규칙을 적용했다면(과거 가정)".
5. **유니버스 t-stat·IC·분위 단조성 *수치*** — 표본 ~72회. 밴드·계단·"눈으로(t-stat 아님)"까지가 천장.
6. **"이 팩터가 시장을 이긴다/검증된 팩터"** — 투자자문 규약(U-G8).
7. **펀더게이트를 "moat/가격 백테스터가 못 함"** — TradingView `request.financial()`이 한국 재무를 이미 엮음. 진짜 칼날 = "DART 계정 정규화 + 학술팩터 9개 사전구현 + PIT 근사 라벨".

## 1. 왜 이 PRD인가 (옛 03 폐기 + v0.1→v0.2 무게중심 역전)

옛 03 = "드롭다운 6개 + 안 읽힘". v0.1은 그걸 다전략 시간기계로 개념 재정의했으나, 8-에이전트 검토가 **무게중심 역전**을 발견: v0.1 헤드라인 "단일종목 다전략 가격 캔버스"는 *가장 commodity*(TradingView가 더 잘함)이고, 부록에 밀린 "유니버스 17년 가격보존"·"펀더게이트"가 유일한 진짜 차별이다. v0.2 = moat를 간판으로, commodity를 *세계급 마감의 살*로 역전(깎지 않고 순서만 뒤집음).

## 2. ★타깃 사용자 (교집합 — terminal-improvement 충돌 해소)

> **"무료 도구를 쓰는 한국 세미프로 — 펀더멘털로 회사를 판단하되, 그 판단이 *시간과 횡단면 위에서 실제로 작동했는지*를 규칙으로 검증하려는 사람."**

두 세그먼트의 합집합이 아닌 *교집합*. `terminal-improvement`의 "분기 공시 forensic 성향"을 상속(타이밍 트레이더 배제 = 두 PRD 일관), "규칙 트레이더"는 별도 세그먼트가 아니라 *forensic 사용자가 검증 모드에 들어간 상태*로 재정의. 순수 기술 트레이더(차트만, 재무 무관) = **2차 사용자**(commodity 캔버스만, moat는 forensic 겨냥). 펀더게이트(§4.10)가 두 모드를 잇는 **다리**.

## 3. ★단방향 시간축 규칙 (불가침 — 기존 아키텍처 승계)

```
 [과거: 실현 시계열]      asOf       [미래: 결정론 시나리오]
 ◀── 리플레이 walk ──┃── Play fan ──▶
   Strategy Lab(본 PRD)  ┃   scenario-simulator/05 (미래)
   같은 차트 · 같은 재생 엔진 · mode:live|simulate 상호배타
```
- 과거 replay = "있는 시계열을 idx까지만". 미래 Play = "사전계산 결정론 path를 t까지만". 메커니즘 동일, 재생엔진 공유.
- **Strategy Lab ⟶ 시뮬 단방향**: 시뮬 Play(05)가 본 랩의 asOf 포트 상태를 *초기조건으로 소비*(역참조 0). 미래 path 데이터는 시뮬 코어(`simulate/` DAG) 소유.

## 4. ★로컬/퍼블릭 공동배선 (불가침)

- **퍼블릭(landing, 서버0, 브라우저)** = floor. 모든 단계가 브라우저 TS 엔진으로 완결. `env.kind` 분기로 floor에서 사라지면 안 됨. **라벨은 capability-presence가 아니라 *데이터 출처*에 바인딩**(04 §2.9 — 라벨 증발 버그 차단).
- **로컬(:8400 백엔드·Python)** = bonus. floor를 *대체 않고 보강*만(일별 정밀·walk-forward·CPCV). DSR/PBO 등 folk-stat 수치는 로컬·게이트 뒤. dartlab은 이미 `_backtestAdvanced.py`에 walkForward/cpcv/PBO/DSR 보유 — floor toy성은 *무지가 아니라 의도된 제약*.

## 5. ★단계 지도 (무게중심 역전 — 간판 W / 살 S / 이연 D, 각 단계 출하가능)

> 단계는 *기능을 깎은 MVP가 아니라* 회귀위험을 격리한 진입 경로. moat 우선·두 트랙 병렬.

| 순서 | 단계 | 트랙 | 출하 가치 | 선결 |
|---|---|---|---|---|
| **기반** | persistent dock + 3단 tiering | 공통 | 깨진 드롭다운 루프 복구 + 권위 상승. 전 탭(단일·유니버스·게이트) 토대 | 없음 (현 엔진 위 UX) |
| **W1 (간판①)** | 유니버스 U1 (모멘텀12-1·5분위·분기·동일가중·이중벤치·폐지밴드·OOS강제) | 횡단면 | "17년 가격보존 유니버스 분위 스프레드 + 불확실성까지 명시" — *오직 dartlab* | 🔴 G-M1·M2 측정 + `buildUniversePanel.py` 데이터결함 2종 수정(05 §3.1) |
| **S1 (살A)** | 다전략 캔버스 (공유절대축·분산효과 음영·combo) | 시간 | "A·B·A+B 눈으로 비교" 세계급 마감 | 엔진 배선됨(`runPortfolioBacktest`). dock에 흡수 |
| **W2 (간판②)** | 펀더게이트 + 조건빌더 + 시간레인 | 시간 | "재무 튼튼할 때만 진입"을 배경음영+레인으로 — TradingView가 *구조적으로* 못 베끼는 panel 칼날 | `quant/alphas` 9개 PIT 시계열 + `rcept_dt` join |
| **S2 (살B)** | 거래 정밀 (stop·sizing·MAE/MFE·expectancy·R-multiple) + 한국 비용모델(호가·상하한가·비용밴드) | 시간 | "전문 거래 분석" | `runPass` 확장(stop=null이면 회귀 0) |
| **W3** | 유니버스 U2 (가격팩터 다양화·리밸 walk·drill-down 동선 완성) | 횡단면 | 깔때기 완성(유니버스→단일종목) + 동선 전환율 측정으로 "통합 서사" 검증 | U1 + S1 출하 후 |
| **이연 D1** | P3 리밸런싱 (부분노출 일반화) | 시간 | "그때그때 리밸런싱" | 高위험·ROI 재검 후 |
| **이연 D2** | P4 강건성 / U3 local 정밀 (multi-split OOS·민감도·MC·CPCV) | 양트랙 | "과적합 진단" | folk-stat 천장 게이트 |
| **경계 D3** | P5 미래연속 / U4 재무유니버스 | — | "과거→미래" / 재무랭킹 | 시뮬 코어 졸업 / 상폐사 재무 재수집 |

상세 = 03-staging-roadmap.md.

> **번호 매핑** (W/S/D ↔ 옛 P, 00 §4·04 판정과 cross): `기반=P0` · `W1=U1`(유니버스) · `S1=P1`(다전략 캔버스) · `W2=P1.5+펀더게이트` · `S2=P2`(거래정밀) · `W3=U2` · `D1=P3`(리밸런싱) · `D2=P4/U3`(강건성) · `D3=P5/U4`(미래·재무유니버스).

## 6. 문서 지도

- **[00-product-prd.md](00-product-prd.md)** — 제품 정의·타깃 사용자·canon 개념 카탈로그·never-claim·성공지표·데이터 실측판정.
- **[01-mechanism-architecture.md](01-mechanism-architecture.md)** — `decisionT<fillT` PIT 불변식 SSOT·3겹 메커니즘·엔진 재사용·한국 비용/체결 모델·적대검증 정정 함정.
- **[02-ui-ux-design.md](02-ui-ux-design.md)** — persistent dock·progressive disclosure(Glance→Compose→Decompose→Diagnose)·3단 tiering·시간레인 opt-in·ASCII 목업(단일·유니버스·게이트).
- **[03-staging-roadmap.md](03-staging-roadmap.md)** — 단계별 AC·타입계약·영향파일/함수·테스트·롤백.
- **[04-honesty-and-rigor.md](04-honesty-and-rigor.md)** — 통계 엄밀성 SSOT·never-claim grep 게이트·U-G1 합병식별 밴드·look-ahead·folk-stat 천장·"세계급" 단어 금지.
- **[05-universe-backtest.md](05-universe-backtest.md)** — 유니버스 백테스터(별도 객체·거처 `scan/universe/`)·`buildUniversePanel.py` 데이터결함 수정·합병식별·실측 게이트.

## 7. 경계 (claim 금지 — 세계급으로 키우되 넘지 않음)

- **미래(Play·fan·드라이버 DAG·valuation)** = `scenario-simulator/`. 본 랩은 mode 전환으로 *연결*만, 생성 0.
- **JUDGE(reverseDCF·compare·적정주가)** = `financial-statement-lab`. 펀더게이트 출력은 영구히 boolean 음영(초록/없음)이지 점수·등급·"저평가" 라벨 0.
- **egress(엑셀)** = `table-export`. 백테스트 거래 로그 CSV만.
- **공시레일·지수차트** = `_done/terminal-chart-suite/01·02`.
- **UI 토폴로지** = `ui/packages/surfaces/src/terminal/`(단일) + `ui/packages/surfaces/src/scan/universe/`(유니버스, 신규).

## 8. 착수 게이트

운영자 go 후 기반(dock)부터. UI 변경이므로 **commit 자율·push 운영자 명시 승인 후**(스크린샷 눈검수·공개 터미널 무중단). W1 유니버스는 `buildUniversePanel.py --skip-upload` 측정(G-M1·M2 + 데이터결함)으로 *코딩 첫 스텝* 게이트를 닫은 뒤 진입.
