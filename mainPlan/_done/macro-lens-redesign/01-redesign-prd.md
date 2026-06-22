# Macro Lens 다이얼로그 시각 재설계 PRD
## "계기판이지 판정기가 아니다 (Dashboard, not Verdict) — 전파사슬을 그린 노출 지도(Exposure Map)가 단일 주역"

> 거처: `ui/packages/surfaces/src/terminal/panels/MacroLensDialog.svelte` (기존 다이얼로그 EXTEND, 새 라우트·상주 패널·차트 복제 0). 모달 `min(960px,96vw) × 88vh`.
> 본 문서는 자기충족적이다. 이 문서만 보고 재조사 없이 구현 가능하도록 영향 파일·함수·필드 매핑·ASCII 목업·CSS 도형 칩·시각 토큰표·테스트·롤백을 모두 담는다. SSOT는 클래스명·함수명·콜사이트명이며 줄번호는 보조다(현 소스 실측 기준).

---

## 1. 한 줄 결론 + 제품 비전

**한 줄 결론:** Macro Lens 다이얼로그의 무게중심을 *"판정 엔진(verdict·score·100)"*에서 *"매크로 계기판(dashboard)"*으로 역전한다. 13개 섹션이 쌓인 한 탭을 폐기하고, 4블록 IA — **무엇이 움직였나 → 어느 채널에 닿나 → 증거가 무엇인가 → 언제 다시 보나** — 로 되돌린다. 새 데이터 fetch 0, 새 패널 0, 새 필드 0. 코드는 ~600줄 순삭감.

**단일 핵심 결정:** 첫 화면의 **시각 주역은 단 하나 — Exposure Map(노출 지도)**이다. 그 안의 읽기를 두 위계로 못 박는다:
- **읽기 1차 = 초점 전파사슬(focus chain)** — `[driver] ─(lag)─▶ [재무라인] ─(lever)─▶ [밸류레버]` 한 줄에, 증거 층위 칩(섹터관측/업종prior/템플릿)을 사슬 위에 얹는다. 0.5초에 잡히는 답 한 줄.
- **읽기 2차 = 닷그리드(dot grid)** — "어느 채널이 켜졌나"의 전체 지형. 옅게(opacity .82) 후퇴해 시선이 먼저 초점 사슬에 가고 그다음 지형으로 내려가도록 한다.

이 둘은 역할이 겹치지 않는다. 초점 사슬은 *그 채널이 어떻게·언제·어떤 증거로 닿나*의 해부, 닷그리드는 *어느 채널이 켜졌나*의 지형이다.

**왜 시각적 직관 재설계인가:** 현재 다이얼로그는 `regime` 탭 한 곳에 13개 섹션이 같은 무게의 작은 mono 박스로 쌓였다. 시각 위계(크기·여백·색 의미)가 사실상 없어 눈이 어디를 먼저 봐야 할지 모른다. `kill-chain`·`flip test`·`direction contest`·`evidence cockpit`·`verdict engine` 같은 전문용어 벽이 일반 사용자를 막는다. 강함은 쌓아서가 아니라 깎아서 나온다 — 정답은 추가가 아니라 제거다.

**무엇을 폐기하는가 (정보 자체를 없애는 진짜 삭제):**
- `score 0/100` 단일 macro 점수 — 단일 macro score·"판정" 금지 가드와 정면 충돌. 화면 맨 위에 점수를 올린 것이 모든 누적의 시작이었다.
- verdict 레이어 전부 (UI 13섹션 + view-model `buildMacroVerdict` + `MacroVerdict*` 타입군). OBS/PRIOR/TPL/LOCK 상태 계약을 다시 점수·방향·승패로 재포장해 "판정"으로 읽히게 만든 레이어.
- `pressureGrid`(상세 driver "우선 경로" 카드) — 그 driver들은 블록 B Driver Pulse가 `value/change/spark/asOf/source`로 더 풍부하게 보여주고, `pressureReason` 텍스트는 초점 사슬 + 셀 `title`/`aria-label`로 흡수된다. 순수 중복이므로 *이동이 아니라 완전 삭제*.
- `mlMobileDrillRail`(Map 모바일 카드 전환이 같은 역할) · `mlLegend`(범례는 각 채워진 칩에 한글 마이크로라벨로 직접 흡수) — 중복 삭제.

**verdict 삭제로 정보가 손실되는가?** 정보 존재 기준 손실 0, 단 일부는 접근 +1클릭. 기여도 분해(`buildContributionStacks`)·driver 방향(`change`)·5단계 서사(`evidenceGates`+`releaseRail`+`falsifiers`)는 전부 `경로`·`근거` 탭에 원본으로 살아 있다. 사라지는 것은 정보가 아니라 "판정 프레임"이다.

**비전 문장:** Macro Lens는 "경제지표를 보여주는 화면"이 아니라 **"매크로가 이 종목의 어느 재무 채널에, 언제(lag), 어떤 증거(섹터관측/업종prior/템플릿)로 닿을 수 있는지를 7초 안에 읽게 하는 검증 계기판"**이다. 화면은 판정하지 않는다. 화면은 *무엇이 닿고, 그 증거가 무엇인지*를 보여준다.

---

## 2. 현상 진단

현재 `MacroLensDialog.svelte`의 `regime` 탭 한 곳에 13개 섹션이 순차로 쌓여 있다.

| # | 섹션 | 대표 클래스 | 진단 |
|---|---|---|---|
| 1 | Verdict Hero (score/100) | `mlVerdictHero` `mlVerdictDial` | **단일 macro score** — 가드 위반. 가장 큰 글씨가 점수. |
| 2 | Verdict Main + Falsifier switch | `mlVerdictMain` `mlFalsifierSwitch` | "판정 강도"·"근거 수준" 판정 어휘. |
| 3 | Battle Board (방향 대결 미터) | `mlBattleBoard` `mlBattleMeter` | 승패 은유. 매수/매도 오독 위험. |
| 4 | Action Queue + Command Bar | `mlActionQueue` `mlCommandBar` | "다음 행동" 명령. 도구·결론 혼재. |
| 5 | Kill-chain Panel | `mlKillChainPanel` `mlKillStep` | 전문용어 5단계 박스. |
| 6 | Direction Contest | `mlContestPanel` | 같은 데이터를 점수 재포장. |
| 7 | A/B Compare Tray | `mlCompareTray` | "왜 1순위가 이기나" 승패. |
| 8 | Mechanism Rail | `mlMechanismPanel` | 상태를 점수 막대로. |
| 9 | Decision Grid | `mlDecisionGrid` | gate와 중복 3카드. |
| 10 | Evidence Cockpit | `mlEvidenceCockpit` | gate strip과 중복. |
| 11 | Verdict Drivers | `mlVerdictDrivers` | driver를 또 점수 막대로 — pulse 중복. |
| 12 | Phase Strip | `mlPhaseStrip` | **(계승 — 원본 자산)** |
| 13 | Pulse / Matrix / Gate / Release | `mlPulseStrip` `mlMatrix` `mlGateStrip` `mlReleaseRail` | **(계승 — 단, 2중 `<details>`로 접혀 묻힘)** |

**진단 (위계 역전):** 핵심 자산(11~13)은 2중 `<details>`로 접혀 화면 맨 아래에 묻혀 있고, 가드 위반 소지가 큰 verdict 레이어(1~10)가 화면을 점령한다. 위계가 뒤집혀 있다. 재설계는 이 위계를 정확히 뒤집는다 — verdict 1~10 삭제, 11~13을 첫 화면 주역으로 끌어올린다. 동시에 13섹션이 전부 같은 무게의 작은 mono 박스(8~11px)라 시각 위계 자체가 없는 문제를, §5 px 위계표·시각 토큰 SSOT·면적 강조로 닫는다.

---

## 3. 재설계 정보구조(IA)

### 3.1 탭: 5개 → 3개

| 현재(5) | 재설계(3) | 처리 |
|---|---|---|
| `regime`(판정) | **폐기** | verdict 레이어 전부 삭제. |
| `drivers`(지표) | `dashboard`(계기판) | 첫 화면 4블록. 기본 진입 탭. |
| `transmission`(전파) | `path`(경로) | MacroPathRail(full) + 셀/driver 클릭 드릴다운(chain·quality·contribution·co-move·source). 거의 계승. |
| `scenario`(시나리오) | **강등 → 경로 탭 `<details>`** | 시나리오는 edge에 없는 명시 충격 크기·`firstBreak`·`requiredEvidence`를 더하므로 순수 중복 아님 → 삭제 대신 `<details>` 강등. |
| `sources`(출처) | `근거`(출처·한계) | Quality Gate / Model Card / Missing Ledger / Falsifier / Source packet. 정량 게이트는 여기로 강등(§3.3). |

탭 내부 키는 `'dashboard' | 'transmission' | 'sources'`로 둔다(라벨만 한글 `계기판 · 경로 · 근거`, transmission/sources 키 유지 → 드릴다운 `goto('transmission', …)` 호출 무변경). "한계"는 탭 라벨에서 빼고 `근거` 탭 내부 섹션명(Missing Ledger="한계·결손")으로 둔다.

### 3.2 첫 화면(계기판 탭) 섹션: 13개 → 4블록 (전부 펼침, fold 0)

1. **블록 A — Phase Strip** (KR / US / Sector 국면 + 기준일). 계승 `mlPhaseStrip`. 얇은 스트립, 테두리 없음.
2. **블록 B — Driver Pulse** (움직인 driver 6개 미니 타일: 값+스파크+delta+asOf+source). 계승 `mlPulseStrip`. 얇은 상단 스트립, 6 tile 가로 1줄, 테두리 없음.
3. **블록 C — Exposure Map** (초점 전파사슬 + 닷그리드). 계승+재설계 `mlMatrix`→`mlMap`. **첫 화면 단일 시각 주역. 유일한 테두리 패널·최대 면적·내부 2단 위계.**
4. **블록 D — Evidence Gate(데이터·전파·동행·회사) + Release Rail**. 계승 `mlGateStrip`(quant 제외) + `mlReleaseRail`. 2열 얇은 스트립, 테두리 없음.

그 아래 가드 캡션 1줄(계승 `mlAlwaysNote`): "노출 점검표입니다. 정량 민감도·투자 결론·가격 산출은 표시하지 않습니다."

### 3.3 정량 게이트 첫 화면 제거 + 미래 배선 안전성

정량 게이트는 회사 macroExposure 회귀에 의존한다. 생산 경로는 `buildExposureQuality(co)` → `normalizeExposureQuality(co.macroExposure?.exposureQuality)`다. **실측: `co.macroExposure.exposureQuality`는 전 종목(2802사) 배선되어 있고**, `normalizeExposureQuality`가 그 `status`를 그대로 통과시킨다 — `co.macroExposure?.exposureQuality`가 없을 때만 도달하는 default fallback 브랜치(`status:'qualitativeOnly', coverage:'sectorOnly'`)는 라이브 0사로 dead branch다. **status 분포(`landing/static/dashboards/finance.json` 실측 2026-06-19, 2802사): `blocked` 2645(94.4%) · `qualitativeOnly` 157 · `quantCandidate` 0.** 지배 상태 `blocked`는 회사별 selected 회귀가 *부재*(`blockedReason:'selected macro regression absent'`, `coverage:'missing'`, `nObs:null`)라는 뜻이다 — 미배선이 아니라 회귀를 시도했으나 겹친 표본이 부족한 상태다. 분기 회귀 파이프라인이 미구현이라 `quantCandidate`는 0이고, **정량 게이트는 사실상 항상 LOCK**이다. 현실이나 첫 화면에선 무가치한 고정 셀이 면적을 잡아먹는다. IA 결정:

- **첫 화면 7초 질문은 4개**: (1)무엇이 움직였나(Pulse) (2)어느 채널에 닿나(Map) (3)증거가 관측/prior인가(Map 칩) (4)무엇 보면 바꾸나(Release). "정량 열렸나 잠겼나"는 현재 항상 같은 답이라 7초 핵심에서 뺀다.
- **D블록 Gate Strip = `evidenceGates` 중 quant 제외 4개**(데이터·전파·동행·회사). 정량 게이트는 `근거` 탭 Model Card 상단으로 강등하고 거기서 2케이스 문구로 명시(§6.1).
- **첫 화면 정량 행 영구 없음 + 회사 닻 영구 없음.** quantCandidate 조건부 분기와, OBS 칩에 회사 회귀를 표시하는 `companyAnchor ::after` 닻은 둘 다 영구 제거한다(dead code·dead CSS 방지). 정량이 실제로 배선되는 미래에 한 곳에 다시 추가하는 것이 두 곳을 유지하는 것보다 깨끗하다.
- **미래 배선 silent-drop 가드:** `normalizeExposureQuality`는 quantCandidate를 통과시키므로, 미래에 분기 회귀가 채워져 quantCandidate가 생기면 첫 화면 입력에 quantCandidate가 들어올 수 있다. 이때 `buildExposureMatrixRows`·Gate Strip이 **깨지지 않고 안전히 무시**(quantCandidate를 첫 화면 행으로 만들지 않고 근거 탭에만 흘림)함을 §9.1 회귀 가드 테스트로 고정한다 — "영구 제거"가 미래 데이터에서 조용한 데이터 손실(silent drop)이 되지 않음을 보증.

### 3.4 드릴다운(30초) + 경로 탭 누적 가드

계기판 Map 셀 클릭 = `goto('transmission', edge.driverId)` → 기존 `mlDrill` 4카드(전파 chain / 품질 gate / contribution / source) + `mlContributionPanel` + `mlCoMovePanel`(scatter)을 `경로` 탭에서 연다(새 코드 0). 닷그리드 칩은 클릭 가능 어포던스(`cursor:pointer` + hover 시 테두리 강조)를 칩 차원에 둔다(§5.1).

누적 가드: 경로 탭 펼친 섹션 ≤ 2(MacroPathRail + 활성 드릴다운 1개), 강등 항목(scenario·상세 driver 표)은 전부 `<details>`(기본 닫힘) 안. **`<details>` 상한 = 2개** — 3번째 강등은 anti-clutter 위반으로 거부(§13 grep 게이트).

---

## 4. 첫 화면 ASCII 목업

### 4.1 데스크톱 (1280×800, 모달 960×88vh)

위계 표기: `███`=대(초점 사슬 마디 14px), `▓`=중(라벨), `░`=소(메타). `╔═╗`=테두리 패널(Map만). 칩은 CSS 도형(§5.1)이며 ASCII에서는 형태군 근사 글리프로 표기. **빈 열은 비대칭 collapse**(폭 0~점선)되어 채워진 채널만 격자에 존재한다(§5.3).

```
┌─ MACRO LENS ─────────────────────────────────────────────────────────────┐
│ 삼성전자  005930  반도체            macro 2026-06-18 · price 06-19 · fin 1Q26 │  헤더
├──────────────────────────────────────────────────────────────────────────┤
│  [ 계기판 ]   경로    근거                                                   │  탭
│  노출 점검표입니다. 정량 민감도·투자 결론·가격 산출은 표시하지 않습니다.(░)    │  캡션
├──────────────────────────────────────────────────────────────────────────┤
│ A 국면  KR ▓스태그(성장↓물가↑)  US ▓리플레(성장↑물가↑)  업종 ▓반도체 +0.31░  │  ← A 얇은 스트립(테두리X)
├──────────────────────────────────────────────────────────────────────────┤
│ B 무엇이 움직였나  USD/KRW░1,386 ╱╲  금리░3.50 ─  CPI░+2.7 ╲  수출░-5.1 ╲╲ │  ← B 얇은 스트립(테두리X)
│                    WTI░71.2 ╱╲  HYsprd░+38 ╱   (값 13px tabular)            │     6 tile 1줄
├──────────────────────────────────────────────────────────────────────────┤
│╔═ C 어느 채널에 닿나 (Exposure Map) ═══════════════ 단일 주역·테두리 패널 ═╗│  ┐
│║ ┌─ 초점 채널 [읽기 1차·중립 배경 강조·좌측선] ──────────────────────────┐ ║│  │ 읽기 1차
│║ │ ███ 수출(EXPORT) ──1~6M──▶ 매출 성장률 ──growth──▶ 성장                 │ ║│  │ 전파사슬
│║ │   증거: ● 섹터 관측(edge OBS·회사 회귀 아님)   -5.1% ░ 06-18 ECOS      │ ║│  │ 한 줄
│║ │   셀 클릭 → 경로 드릴다운(전파·품질·기여·동행·출처)                    │ ║│  │
│║ └─────────────────────────────────────────────────────────────────────┘ ║│  │
│║  ───────────────── [읽기 2차·전체 지형·옅게 opacity .82] ─────────────── ║│  │ 읽기 2차
│║  채널 열 클러스터 — 켜진 채널만 열·그 아래 닿는 driver 칩(빈 셀 없음)     ║│  │ 닷그리드
│║   매출            마진             차입           밸류                     ║│  │ (점도:
│║   ● 수출(관측)    ● PPI반도(관측)  ◌ 금리(템플)   ● HYsprd(관측)          ║│  │  켜진 채널
│║   ◖ 환율(prior)                                  ◌ DGS10(템플)           ║│  │  +driver)
│║   ░ 색=증거상태(방향 아님) · '현금흐름' 열=표준 경로 없음(열 collapse)     ║│  ┘
│╚══════════════════════════════════════════════════════════════════════════╝│
├──────────────────────────────────────────────────────────────────────────┤
│ D 증거 게이트 · 언제 다시 보나                                             │
│  데이터▓OPEN 전파▓OPEN 동행▓WATCH 회사▓LOCK │ Release CPI░07-02 · 금리░07-11 │  ← D 2열
│  ░ (정량 게이트는 근거 탭. 첫 화면 정량 행 없음)                             │
└──────────────────────────────────────────────────────────────────────────┘
```

**CSS 도형 칩 4상태 — 색 없이 형태만으로 변별 (단색 가정 근사):**

```
 OBS(관측)      PRIOR(업종)     TPL(템플릿)     LOCK(정량잠금)
┌──────────┐  ┌──────────┐   ┌──────────┐   ┌──────────┐
│  ●●●  +  │  │  ◖◗   ±  │   │  ◌◌◌  −  │   │  ▨▨▨  🔒 │
│ 꽉찬 원  │  │ 좌반 원  │   │ 점선 빈원 │   │ 빗금 사각 │
└──────────┘  └──────────┘   └──────────┘   └──────────┘
   원·채움       원·반채움       원·빈           사각·빗금
```

OBS(꽉 찬 원)·PRIOR(좌반 원)·TPL(점선 빈 원)은 *원 내부 채움량*으로 단조 변별, LOCK은 *원이 아닌 사각+빗금*으로 형태군이 분리된다. 색맹 사용자도 채움량+형태로 구분(색 무의존).

초점 사슬 주석: 사슬 마디(driver→재무라인→밸류레버)와 lag은 edge에 이미 있는 `financialLine`·`valuationLever`·`lagMonths`로 그린다(새 필드 0). 증거 칩은 edge 관측/업종 prior/템플릿을 표기한다. EXPORT→매출은 `evidenceLevel='observed'`라 초점 후보 1순위이고 lag `1~6M`·sign `positive`다. D블록 전파 게이트는 *계산값*이다(§6.2): 라이브 macro.json은 transmission payload를 포함해 `edgeSourceRef='dartlab://macro/transmission'`(template 아님)이므로, 관측 edge 보유 종목(반도체 등)은 `OPEN`이 정상이고 edge 0이나 source 결손 시에만 `WATCH/LOCK`이다 — 고정 디폴트로 그리지 않는다. 밸류 채널에 닿는 driver 2개(HY sprd OBS·DGS10 TPL)는 밸류 열 아래 세로 stack(§5.3 규칙 5).

### 4.2 모바일 (390×844)

데스크톱 닷그리드는 390px에 안 들어간다. `@media (max-width:560px)`에서 driver별 카드 리스트로 전환(채워진 칩만 인라인, 빈 채널 생략). 세로 스크롤 1회 허용. **Map 패널은 모바일에서도 유일한 테두리 블록으로 유지**해 주역성과 초점1차/카드2차 위계를 보존한다. 모바일 첫 화면 fold(첫 844px) 안에 A·B·C(초점 사슬)가 들어오고 닷그리드 카드 일부는 fold 경계에서 시작한다.

```
┌─ MACRO LENS  삼성전자 005930 ──────────[X]┐
│ [ 계기판 ]  경로  근거                      │
│ 노출 점검표입니다. (정량/결론/가격 미표시)  │
├────────────────────────────────────────────┤
│ A 국면  KR ▓스태그 · US ▓리플레 · 반도체+0.31│  ← 세로 줄바꿈 허용
├────────────────────────────────────────────┤
│ B 움직임 (가로 스와이프 ▶) USD/KRW░1,386 ╱╲ │  ← overflow-x:auto 1줄 스와이프
├────────────────────────────────────────────┤
│╔ C 어느 채널에 닿나 (테두리 패널 유지) ════╗│  ← 모바일도 Map만 테두리=주역
│║ [1차] 수출 ─1~6M─▶ 매출 ─growth─▶ 성장   ║│  ← 초점 전파사슬(중립 배경 강조)
│║       증거 ● 섹터 관측  -5.1% ░06-18      ║│
│║ ────────── [2차·옅게] ───────────────────║│
│║ 수출    매출 ● 관측                      ║│  ← driver별 카드. 채워진 칩만
│║ 환율    매출 ◖ prior                     ║│     나열, 빈 채널 생략
│║ PPI반도 마진 ● 관측                      ║│
│║ 금리    차입 ◌ 템플                      ║│
│║ HYsprd  밸류 ● 관측                      ║│
│╚══════════════════════════════════════════╝│
│ ░ 색=증거상태. 카드 탭→경로 드릴다운        │
├────────────────────────────────────────────┤
│ D 게이트 데이터OPEN 전파OPEN 동행WATCH 회사LOCK│  ← 2줄 wrap, 정량 행 없음
│ Release  CPI 07-02 · 금리 07-11             │
└────────────────────────────────────────────┘ (세로 스크롤 1회)
```

---

## 5. 시각 디자인 — CSS 도형 칩 + px 위계표 + 면적 강조

### 5.1 시각 토큰 SSOT + CSS 도형 칩

이 표가 dialog `<style>`의 단일 진실원이다. CSS 변수는 **실재 터미널 토큰**(`terminal.css`)만 재사용한다(새 색 토큰 0): `--panel`(=`--dl-bg-raised`, 패널 배경) · `--txt`(=`--dl-ink`, 본문) · `--dl-ink-dim`(흐린 텍스트) · `--dim`(보조) · `--up`(#34d399) · `--dn`(#f0616f) · `--amber` · `--bd`(rgba white .08). 증거 상태 색은 *방향이 아니라 강도/종류*다.

약어 정의(첫 등장 1회): **OBS=관측 · PRIOR=업종 추정 · TPL=표준 템플릿 · LOCK=정량 잠금.** UI 칩은 약어 대신 **한글 마이크로라벨**(8px, `--dl-ink-dim`)을 각 채워진 칩에 직접 동반한다(별도 범례 삭제 → 클러터 -1).

| 토큰 | 의미 | 값 |
|---|---|---|
| `--ml-block-gap` | 블록 경계 여백 | `12px` |
| `--ml-row-gap` | 블록 내부 행 간격 | `4px` |
| `--ml-map-panel` | Map 패널(유일 테두리) | `border:1px solid var(--bd); background:var(--panel); border-radius:8px; padding:8px` |
| `--ml-map-focus-bg` | 초점 사슬 배경(읽기 1차·**중립 강조**) | `background:color-mix(in srgb,var(--dim) 7%,var(--panel)); border-left:2px solid var(--amber)` — **방향색(--up/--dn) 금지, 중립 강조로 호재 오독 원천 차단** |
| `--ml-grid-recede` | 닷그리드(읽기 2차) 후퇴 | `opacity:0.82; border-top:1px solid var(--bd); margin-top:8px; padding-top:8px` |
| 초점 사슬 마디 텍스트 | 단일 대(███)·읽기 1차 | `font-size:14px; font-weight:700; line-height:1.3; letter-spacing:-0.01em` |
| 초점 카드 메타(asOf/source) | 소·읽기 1차 소속 | `font-size:9.5px; color:var(--dl-ink-dim); opacity:1` (닷그리드 .82 후퇴를 상속하지 않음 — §5.4) |
| Map 행 라벨(driver) | 중(▓) | `font-size:12px; font-weight:600` |
| Map 열 헤더(채널) | 중(▓)·읽기 2차 소속 | `font-size:11px; font-weight:600; color:var(--dl-ink-dim)` |
| Pulse tile 값 | 소-중 | `font-size:13px; font-weight:600; font-variant-numeric:tabular-nums` |
| 메타(닷그리드 사유) | 소(░) | `font-size:9.5px; color:var(--dl-ink-dim); line-height:1.3` |
| Map 칩 크기 | — | `min-width:40px; height:24px; border-radius:6px; display:inline-flex; align-items:center; gap:3px; cursor:pointer` |
| Map 칩 hover | 클릭 어포던스 | `box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--amber) 45%,transparent)` |
| Map 행 높이 | — | `28px` |
| Pulse tile | — | `min-width:104px; height:64px` |
| 부호(+/−/±) | 텍스트만 | `font-weight:700` — **셀 배경을 빨강/초록으로 칠하지 않는다** |
| 빈 셀/빈 열 | collapse | `opacity:0; width:0; border:none; background:transparent`(데스크톱 열 collapse·§5.3) |

**증거 상태 = CSS 도형 칩 (`::before` 16×16px, 유니코드 글리프 폰트 의존 0).** 4상태가 *형태·테두리·배경 3중 단서*로 색 없이 구분된다. 채움 위계 OBS>PRIOR>TPL은 원 내부 채움량으로, LOCK은 원이 아닌 사각으로 형태군을 분리한다.

| 상태 | CSS (`.mlMapChip.<state>::before`) | 형태 단서 |
|---|---|---|
| **OBS** (관측) | `border-radius:50%; background:var(--up); border:1.5px solid var(--up)` | **꽉 찬 원** — 가장 진함 = 관측 강도(좋음 아님) |
| **PRIOR** (업종 추정) | `border-radius:50%; border:1.5px solid var(--amber); background:transparent; box-shadow:inset 8px 0 0 0 var(--amber)` | **좌측 반채움 원** — inset box-shadow로 원 내부 좌반 채움(linear-gradient hard-stop 안 씀: 원 안 반달 보존) |
| **TPL** (표준 템플릿) | `border-radius:50%; background:transparent; border:1.5px dashed var(--bd)` | **점선 빈 원** |
| **LOCK** (정량 잠금) | `border-radius:3px; border:1px solid var(--dn); background:repeating-linear-gradient(45deg,transparent 0 2px,color-mix(in srgb,var(--dn) 30%,transparent) 2px 4px)` | **빗금 사각형**(원 계열 아님 — 형태 자체가 다름) |

**OBS 칩의 정확한 의미 — 'edge 관측'이지 '회사 관측' 아님:** `evidenceLevel='observed'`는 EDGE_TEMPLATES에 박힌 상수(예: EXPORT·BAMLH0A0HYM2)이고, 회사별 selected 회귀는 부재다(라이브 지배 status=blocked·§3.3). 따라서 OBS 칩은 '이 driver가 일반적으로 관측 가능한 전파 채널'이라는 **섹터 수준 단언**이지 '이 회사에 대해 관측된 노출'이 아니다. 칩 `aria-label`/`title`에 "driver 관측 가능(회사 회귀 아님)"을 명시한다. 회사 회귀를 시각 분리할 닻(`companyAnchor`)은 라이브 데이터에 quantCandidate가 0이므로 추가하지 않는다(§3.3 — dead CSS 방지).

**부호는 전파 가설이지 현재 손익 방향 아님:** 칩 옆 +/−/±는 driver의 *현재 변화 방향*이 아니라 EDGE_TEMPLATE의 정적 `sign` 상수다. `sign==='mixed'`(USDKRW 등)는 +/−로 강제하지 않고 **±(중립)로 고정**한다 — "원화 약세는 환산매출엔 유리하나 달러 원가·부채면 상쇄"라는 양방향성을 칩이 가짜 정밀화하지 않게 한다. Driver Pulse의 `change`(실제 최근 변화)와 Map 칩의 `sign`(전파 방향 가설)은 다른 의미이므로 시각적으로 섞이지 않게 한다(상관≠인과의 시각 가드).

**접근성 무손실:** 칩 `aria-label`에 "수출→매출, 섹터 관측(edge OBS·회사 회귀 아님), 부호 +, 지연 1~6개월"을 항상 둔다(스크린리더는 도형과 무관, 손실 0).

### 5.2 블록별 height 예산 (SSOT)

`.mlBody`는 헤더·탭·캡션 아래부터 시작하는 스크롤 영역이다 — 면적 게이트(§9.3)의 분모는 `.mlBody.clientHeight`이며, A~D + 블록 gap만 포함하고 헤더·탭·캡션은 제외한다.

| 블록 | height(px) | 스크롤 정책 |
|---|---|---|
| 헤더(`mlHead`) | 44 | 고정 (`.mlBody` 밖) |
| 탭(`mlTabs`) | 34 | 고정 (`.mlBody` 밖) |
| 캡션(`mlAlwaysNote`) | 22 | 고정 (`.mlBody` 밖) |
| A Phase | 52 | 고정 (wrap 금지 데스크톱) |
| B Pulse | 76 | 고정 (6 tile 1줄; 모바일 overflow-x) |
| **C Map 패널** (테두리/패딩 16 + 초점 사슬 64 + 구분 12 + 열헤더 24 + 닷그리드 168 + 외곽여유 12) | **296** | 6행 초과 시에만 닷그리드 `max-height:196px; overflow-y:auto` |
| D Gate(4칩)+Release | 60 | 고정 (2열 grid, 정량 행 없음) |
| 블록 경계 gap (A·B·C·D 사이 + 상하 ×6) | 72 | — |
| **`.mlBody` 합계** | **556** | C 296 / 556 = **0.53** (면적 주역) |
| 모달 상하 패딩 ×2 | 36 | — |
| 헤더+탭+캡션 | 100 | — |
| **모달 전체** | **692** (= 88vh×800 가용 704, 마진 12) | 데스크톱 무스크롤 |

블록 gap을 12px로 두어 가용(704) 대비 12px 여유를 확보한다 — 폰트 렌더 차이로 1~2px 넘쳐도 무스크롤 게이트(§9.3)가 안정적으로 통과한다. 스크롤 단일 지점: 첫 화면에서 내부 스크롤이 허용되는 유일한 곳은 Map 닷그리드(row>6일 때). 나머지는 모두 고정 높이.

### 5.3 Map sparsity — 채움 열만 존재하는 비대칭 지도

Map은 *균등 격자가 아니다*. 채움률이 전 종목 13~27%(반도체 7 edge·자동차 ~8·소프트웨어 ~4)이고 각 driver는 채널 1개에만 닿아, row=driver × col=channel 격자로 그리면 24칸 중 6칸만 켜진 "빈칸 많은 표(스프레드시트)"가 된다. 그래서 **데이터는 행=driver로 두되 렌더는 '채널 열 클러스터'로 한다** — 빈 셀을 아예 그리지 않는 점도(point map):

1. **채널 열 클러스터(핵심·스프레드시트 잔상 제거):** 채워진 채널만 열로 두고, 각 driver 칩을 *자기 채널 열 아래 세로로 모은다*. driver×channel 격자의 빈 셀은 렌더하지 않는다 → "켜진 채널과 그 채널을 켜는 driver들"의 점도로 읽힌다(24칸 중 빈 18칸이 사라짐). 각 driver는 채널 1개라 칩이 정확히 한 열에만 존재한다.
2. **빈 채널 열 collapse:** 채움 0 채널(예: 반도체 '현금흐름')은 열 자체가 없다 — "닿는 채널만 켜진 지형."
3. **채움 많은 채널 좌측·채움 driver만:** `buildExposureMatrixRows`가 `filledCount` 내림차순으로 정렬해 채움 많은 채널이 왼쪽. software 4채움도 "닿는 4지점 지도"로 강하게 읽힌다.
4. **초점 사슬이 1순위 텍스트:** 가장 강한 셀 1개(§6.2)를 초점 행으로 풀텍스트 전파사슬.
5. **동일 채널 복수 driver는 그 열 아래 세로 stack:** 밸류 채널에 닿는 driver 2개(HY sprd·DGS10)는 밸류 열 아래 칩으로 세로로 쌓인다(셀 충돌·빈칸 0).

반도체(삼성전자 005930) edge는 `buildEdges` **실호출 결과 기준**이다. `buildEdges`(2167)는 `buildEdgesFromTransmission`(transmission payload edge가 sector 매칭되면 우선)을 먼저 쓰고, 없으면 EDGE_TEMPLATES fallback을 `e.sectors.includes('all') || e.sectors.includes(co.industry)`(2173)로 필터 + `slice(0,8)`한다. 아래 표는 그 EDGE_TEMPLATES fallback 셋이며, transmission payload edge도 동일 shape(driver→channel→financialLine→valuationLever→evidenceLevel→lag)다:

| driver | channel | sign | evidence | lag (EDGE_TEMPLATES 실측) |
|---|---|---|---|---|
| EXPORT | 매출 | positive | **OBS** | 1~6M |
| USDKRW | 매출 | **mixed(±)** | **PRIOR** | 0~3M |
| PPI_SEMI | 마진 | positive | OBS | 0~3M |
| BASE_RATE | 차입 | negative | TPL | 3~12M |
| BAMLH0A0HYM2 | 밸류 | negative | OBS | 0~3M |
| DGS10 | 밸류 | negative | TPL | 0~6M |
| CPI | 마진 | mixed(±) | TPL | 1~6M |

→ 7 edge가 7 driver 행을 만들고 cap 6으로 1행이 준다. **닷그리드 행 = driver 키**(topPressures+secondary 랭킹·dedup·§8.2)이고 각 driver는 EDGE_TEMPLATE상 채널 1개라 행마다 `filledCount=1`(전 동률)이다. 따라서 cap에서 밀리는 1행은 EDGE_TEMPLATES 순서가 아니라 **입력 driver 랭킹(topPressures+secondary) + 안정 정렬**로 결정된다(§9.1 결정성 단언). 초점(EXPORT→매출)은 evidenceLevel+채널 우선순위로 뽑혀 cap과 무관하게 불변. 채널 4종(매출·마진·차입·밸류)만 켜지고 현금흐름 열은 collapse, 밸류 열은 BAMLH0A0HYM2·DGS10 두 driver가 서로 다른 행으로 분리(규칙 5).

**lagMonths=null 사슬 렌더 규칙(방어):** edge `lagMonths` 타입은 `[number,number] | null`이다. **현재 EDGE_TEMPLATES의 반도체 7행은 전부 non-null이라 라이브에서 null-lag 초점은 발생하지 않는다**(위 표 실측). 단 타입상 null이 가능하므로 방어적으로 규칙을 둔다: **`lagMonths === null`이면 사슬에서 lag 마디를 생략하고 `[driver] ──▶ [재무라인]`으로 직결한다(빈 괄호 `──(—)──▶` 금지).** lag이 있으면 `──(1~6M)──▶`. 닷그리드 칩은 lag을 표시하지 않으므로 영향 없다.

### 5.4 면적 강조 + 시각 원칙
1. **Map만 테두리 패널** (`--ml-map-panel`). Phase·Pulse·Gate 테두리 0 → 게슈탈트 closure로 시선 집중.
2. **초점 사슬 = 읽기 1차** (`--ml-map-focus-bg` 중립 배경 + amber 좌측선). **방향색 금지. 초점 카드는 `opacity:1` 고정** — 닷그리드의 .82 후퇴를 상속하지 않아 1→2 위계가 토큰 차원에서도 닫힌다(초점 메타도 dim 색만 쓰되 opacity는 1).
3. **닷그리드 = 읽기 2차** (`--ml-grid-recede` opacity .82 + 상단 구분선). **채널 열 클러스터 렌더(§5.3)로 빈 셀 0 — sparse 표가 아니라 '켜진 채널 점도'.**
4. **면적 비율 ≥40% 게이트**(§9.3) — 점유 면적이 주역성 보증.
- 위계: 큰 글씨 1종 = 초점 사슬 마디(14px)뿐. Pulse 값 13px, 그 외 9.5~12px. 점수 없음.
- 색 한정: 셀 배경 방향색 금지. 색=증거 상태. 초점 배경=중립 강조(방향 아님).
- 여백: 블록 경계 12px. 박스-in-박스 3중 금지. Map은 패널>(초점 사슬 + 닷그리드) 2중첩만.
- 모션: 진입 fade-in 1회(150ms). 점멸·게이지 금지.
- 타이포: 값·코드·날짜 mono(tabular-nums), 라벨 UI 폰트.

---

## 6. 데이터 계약 (기존 MacroLensSnapshot 재사용 — 새 fetch·새 필드 0)

생산자(`buildMacroLensSnapshot` / `buildMarketMacroLensSnapshot`)는 `verdict` 필드 생산만 제거하고 나머지 무변경(§8). 소비 필드 매핑:

| 블록 | 사용 필드 (이미 존재) | 결손 시 표현 |
|---|---|---|
| A Phase | `marketPhase.kr/.us`(`MacroPhaseView`), `sectorBinding.tailwind` | `?? '—'`, tailwind 없으면 `미산출` |
| B Pulse | `buildExposureMatrixRows().slice(0,6)` driver 또는 `topPressures`. tile당 `label/value/change/spark/asOf/source/sourceLineage` | spark 빈 배열이면 polyline 생략, asOf 없으면 `freshness.label`로 STALE 노출 |
| C Map | `buildExposureMatrixRows()`(§8.2). 셀=`{sign, evidenceLevel→OBS/PRIOR/TPL, confidence==='blocked'→LOCK}`. **filledCount 상단 정렬·빈 열 collapse** | edge 없으면 빈 셀, `missing`에 사유 |
| C 초점 사슬 | `pickFocusCell` rows(§6.2). 사슬 마디 = edge의 `driverId·financialLine·valuationLever·lagMonths`(null이면 lag 마디 생략·§5.3), 증거 = `evidenceLevel` | 셀 0개면 §6.2 fallback |
| D Gate | `evidenceGates` 중 **quant 제외 4개**(데이터·전파·동행·회사). status OPEN/WATCH/LOCK. **전파 게이트는 edge가 템플릿이면 WATCH/blocked가 정상**(§6.2) | gate.status==='blocked'→LOCK + 사유 |
| D Release | `releaseRail`(`MacroReleaseView[]`) | `status` fresh/watch/stale/unknown |
| 드릴다운(경로) | `transmissionEdges`,`exposureQuality`,`contributionStacks`,`sourcePackets`,`coMoveGates`,`exposureIndicators`,`falsifiers` | 기존 필드, 각자 LOCK/missing 라벨 |
| 근거 탭 | `exposureQuality`(nObs/R²/window/lag/coverage/sourceRef), `missing`, `falsifiers`, `releaseRail`, `sourceRefs`, `sourcePackets`. 정량 2케이스 문구(§6.1) | nObs<minObs면 LOCK + 사유 |

### 6.1 정량 LOCK — 2케이스 명시 분기 + 대체가치 (`근거` 탭 Model Card 상단)

실측: `co.macroExposure.exposureQuality`는 전 종목 배선되어 있고 status 분포는 `blocked` 2645 · `qualitativeOnly` 157 · `quantCandidate` 0이다(§3.3). 즉 라이브 지배 상태는 *미배선*이 아니라 회사 회귀가 **부재(blocked)**다. 분기 macroExposure 재계산이 미구현이라 `quantCandidate`=0이고, "분기 누적 시 OPEN"은 충족 불가 약속 — 금지한다. 따라서 첫 화면에 정량 행이 없고, `근거` 탭에서 `status`별로 있는 그대로 표시한다(`status` 필드 직접 분기 — UI 추론 0):

| status | 라이브 | 표시 |
|---|---|---|
| `blocked` (지배·2645·94.4%) | `coverage:'missing'`, `nObs:null`, `blockedReason:'selected macro regression absent'` | `정량 LOCK · 회사 회귀 부재` + 사유 그대로(`selected macro regression absent · 겹친 표본 부족`). **대체가치 1줄:** `대신 → 경로 탭 동행(co-move) 반증·업종 prior 경로로 확인`. |
| `qualitativeOnly` (157) | `coverage:'company'` | `정량 QUAL · 정성 경로만` + 사유. 대체가치 동일. |
| `quantCandidate` (0·미래 배선 시) | `nObs ≥ minObs` | 라이브 0. 미래에만 `근거` 탭에서 `OPEN · nObs/R²/window` 표시(첫 화면 행은 그래도 없음·§3.3). |

지배 상태가 `blocked`이므로 사유문은 `notWiredYet`(미배선)이 아니라 실제 `blockedReason`(회귀 부재)을 그대로 쓴다 — 둘은 다른 상태다(미배선=시도 안 함, blocked=시도했으나 표본 부족). "잠김=죽은 칸" 인상은 대체가치 문구가 차단한다. 진척 표기는 텍스트이지 gauge 아님. 구현: `status`로 직접 분기(`quantEvidenceBlocks`가 사유를 이미 생산 → status별 한글 라벨+대체가치 매핑만 추가, 새 계산 0).

### 6.2 초점 사슬 select + tie-break + 전파 게이트 명시 + fallback

**select (`pickFocusCell`):** `observed > sectorPrior > template` 우선. **tie-break(동순위 시):** `edge.confidence(high>medium>low) → 채널 우선순위(매출>마진>밸류>차입>현금) → driverId 사전순`. 반도체 OBS 후보 3개(EXPORT→매출·PPI_SEMI→마진·BAMLH0A0HYM2→밸류)는 confidence가 모두 medium이라, 채널 우선순위(매출 최우선)로 **EXPORT→매출이 결정적으로 초점**이 된다(§4.1 ASCII와 일치). *change 절댓값도, lag 길이도 select에 쓰지 않는다* — change는 모멘텀/뉴스 편향(움직임=신호 오독, 상관≠인과 위반 소지)을, lag 길이는 "빠른 채널이 더 중요하다"는 또 다른 가치판단을 주입한다. 채널 우선순위(매출이 사업 본질에 가장 가깝다)와 evidenceLevel·confidence는 전파사슬 타당성에 직결된 안정 기준이고, driverId 사전순 최종 정렬로 동일 입력=동일 출력을 보장한다(진입마다 흔들림 0).

**초점 사슬 렌더:** `[driver] ──(lagMonths)──▶ [financialLine] ──(valuationLever)──▶ [밸류 효과]` + 증거 칩(섹터관측/업종prior/템플릿) + driver의 `value·change·asOf·source`. lag이 null이면 lag 마디 생략(§5.3). 예: `수출(EXPORT) ─1~6M─▶ 매출 성장률 ─growth─▶ 성장 · 증거 섹터 관측(edge OBS) · -5.1% 06-18 ECOS`. lag·sign·evidenceLevel 모두 edge에 이미 존재(새 필드 0).

**전파 게이트(D블록) = 계산값(고정 디폴트 금지):** `buildEvidenceGates`는 `edgeSourceRef`가 template/missing이거나 edge 0이면 path를 `blocked`(LOCK), 관측 edge 있으면 `ok`(OPEN), 그 외 `watch`로 둔다. 라이브 macro.json은 transmission payload를 포함해 `edgeSourceRef='dartlab://macro/transmission'`(template/missing 아님)이므로 관측 edge 보유 종목은 `ok`(OPEN)가 정상이다. 즉 OPEN/WATCH/LOCK은 *낙관 디폴트가 아니라 edgeSourceRef + 관측 edge 수로 계산한 값*이며, ASCII도 계산값(반도체=관측 edge 보유→OPEN)을 표기한다.

**fallback (셀 0개 = Map 채움 0):** §5.3상 모든 sector ≥4 채움이라 빈도 매우 낮다. 진짜 0채움(macro.json 결손)에서만:
1. 초점 카드 "표준 전파 경로 없음 — 경로 탭에서 확인" 폴백(새 데이터 0).
2. 이 극단에서만 Driver Pulse를 2차 주역 승격(Pulse 값 13→15px, Map 테두리 흐리게).

**lineage:** 모든 숫자의 `asOf/source/unit/frequency/seriesId`는 `MacroDriverView`/`MacroSourcePacketView`에 이미 존재 → tile·셀 `title` + 칩 `aria-label` + `근거` 탭으로 노출(새 계산 0).

**없는 것(꾸미지 않음):** 실제 발표 캘린더/vintage(freshness 추정값만), per-company precompute, 분기 회귀용 장기 이력(→ §6.1 지배 status=blocked). fan chart·heatmap·gauge·donut 0.

---

## 7. 가드 체크리스트

**절대 금지 (위반 시 설계 무효):**
- [ ] 매수/매도, 목표주가, 수혜 확정, 피해 확정, 위기 임박 — 텍스트 0건.
- [ ] 단일 macro score(`verdict.score`,`/100`,`directionScore`,`evidenceScore`) — UI 완전 제거.
- [ ] "판정" 단어 — 탭명·섹션명·캡션 제거.
- [ ] gauge / donut / 출처 없는 heatmap / 모델 분포 없는 fan chart — 0개. 정량 진척은 텍스트 분수이지 gauge 아님.
- [ ] 셀 배경 빨강/초록(방향 색) · 초점 배경에 `--up`/`--dn` — 금지. 색=증거 상태, 초점=중립 강조.
- [ ] sign='mixed'를 +/−로 단정 — ±로 고정(수혜 확정 가드).
- [ ] OBS 칩을 '회사 관측'으로 표기 — 'edge 관측(회사 회귀 아님)' 명시.
- [ ] 전파 게이트를 *고정값*으로 그림 — edgeSourceRef + 관측 edge 수로 계산(관측 edge면 OPEN, template/missing·edge 0이면 LOCK, 그 외 WATCH).
- [ ] lagMonths=null인데 빈 괄호 `──(—)──▶` 렌더 — lag 마디 생략하고 직결(§5.3).
- [ ] "좋음/나쁨","방향 대결","이기는 경로" / kill-chain·flip test·direction contest·evidence cockpit·verdict engine — UI 0건.
- [ ] 충족 불가 약속 위장 — "분기 누적 시 OPEN" 금지(실제 status=blocked 라벨·회귀 부재).

**허용 상태 라벨만:** `OBS`/`PRIOR`/`TPL`/`LOCK`/`STALE`/`MISSING`/`OPEN`/`WATCH`/`QUAL`/`notWiredYet`. 색은 증거 상태 신호.

**구조 가드:**
- [ ] 모든 숫자에 lineage — title 또는 근거 탭 도달. 칩 `aria-label`로도 보존.
- [ ] 결손은 0이 아니다 — `missing`/`partial`/`notWiredYet`/`staleRisk` 명시. 빈 열=collapse.
- [ ] 상관은 인과 아님 — co-move scatter `경로` 드릴다운 "인과 아님" 라벨 유지. Pulse change(현재 변화)와 Map sign(전파 가설) 시각 분리.
- [ ] L2 경계 — macro 엔진은 analysis import 안 함. 결합은 view-model(`macroLens.ts`)만 → 경계 영향 0.
- [ ] 공통배선 — 로컬 :8400 없이 퍼블릭 HF 데이터만. `data/fetch`+`data/origins` 경유(생산자 입력 무변경 자동 충족).

---

## 8. 영향 파일·함수 (클래스/함수/콜사이트명 SSOT)

### 8.1 `MacroLensDialog.svelte` (주 변경)

**삭제 (template):** `{#if localTab === 'regime'} … {/if}` 전체 — verdict 섹션 1~11(`mlVerdictHero`/`mlVerdictMain`/`mlBattleBoard`/`mlVerdictAction`/`mlCommandBar`/`mlKillChainPanel` + fold 내 `mlContestPanel`/`mlCompareTray`/`mlMechanismPanel`/`mlDecisionGrid`/`mlEvidenceCockpit`/`mlVerdictDrivers`). **`mlMobileDrillRail`·`mlLegend`·`pressureGrid`(`mlGrid pressureGrid`) 완전 삭제.** `{:else if localTab === 'scenario'}`은 `경로` 탭 하단 `<details>`로 이동. 상세 driver 표(`mlDriverTable`)만 `경로` 탭 `<details>`로 강등.

**신규 (template) — `{#if localTab === 'dashboard'}`:**
- 블록 A: `mlPhaseStrip` 마크업 이동.
- 블록 B: `mlPulseStrip` 이동, tile 값 class 13px.
- 블록 C: `mlMap`(신규, 기존 `mlMatrix` 재설계) = 테두리 패널 > [초점 사슬 카드(읽기 1차) + 닷그리드(opacity .82·읽기 2차)]. 셀은 `::before` CSS 도형 칩(§5.1). **셀 색 인코딩 축 단일화** — 기존 `.mlXCell.high/.medium/.low/.blocked` 배경색 제거(아래 style 삭제), 셀은 `evidenceLevel→형태` 단일 축만. 초점 사슬은 §8.2 헬퍼 결과(lag null이면 마디 생략·§5.3). 빈 열 collapse(§5.3). **`mlMatrixDriver` 버튼의 `goto('drivers', row.driver.id)`는 `goto('transmission', row.driver.id)`로 교체**(driver 클릭 = 경로 드릴다운, 셀 클릭과 일관·§8.5 #6).
- 블록 D: `mlGateStrip`(**quant gate 필터 제외**) + `mlReleaseRail` 2열. **정량 행 없음**(§3.3).

**삭제 (script):** verdict 파생값(`verdict`/`verdictDrivers`/`verdictActions`/`topVerdictDriver`/`topKillStep`/`verdictFocusId`/`topVerdictRelease`/`modelClaimRows`), verdict 함수(`showVerdictOnChart`/`inspectVerdictPath`/`inspectVerdictSources`/`runVerdictAction`), `signedScore`/`killStatus`. `tabs` 배열에서 `regime`/`scenario` 제거, `drivers`→`dashboard`.

**계승 (script):** `T()`, `channels`, `signText`/`confidenceText`/`evidenceText`/`exposureQualityText`/`severityCls`/`readinessText`/`componentStatusText`, `cellTitle`(evidenceLevel·lag 포함하도록 보강), `sparkPoints`, `fmtR2`, `goto`/`selectTab`/`focusActiveTab`/`selectRelativeTab`/`visibleFocusableElements`/`onDialogKeydown`, `econBlocked`, drivers 파생 전부, 드릴다운 전부(`focusDriver`/`focusEdge`/`focusIndicator`/`focusFalsifiers`/`focusRelease`/`focusSource`/`focusContribution`/`focusCoMove`), `exposureRows`→`buildExposureMatrixRows` 호출로 교체, `gateRows`(quant 필터 추가), `modelMetricRows`/`modelSpecRows`(근거 탭), `corrLeft`/`motionLabel`.
- **`cellClass` 의미 변경:** 현재 `cellClass = edge.confidence`(none/high/medium/low/blocked → 색배경). 신규 `cellClass = edge ? edge.evidenceLevel : 'none'`(observed/sectorPrior/template) + blocked는 별도 `cellLabel`/칩 상태로. 칩 형태는 `.mlMapChip.<OBS|PRIOR|TPL|LOCK>::before`로 단일 축.
- **`inspectEvidenceGate` retarget:** 현 함수의 `id === 'macroData' ? 'drivers' : id === 'path' ? 'transmission' : 'sources'`에서 `'drivers'`는 삭제된 `MacroLensTab` 값이라 dangling이 된다. `'drivers'`→`'dashboard'`로 교체(macroData 게이트 클릭 = 계기판 탭). quant 게이트는 근거 탭으로 강등되므로 `id === 'quant' → 'sources'` 분기를 명시 추가(else 흡수와 동일하나 가독성).

**삭제 (style):** `.mlVerdict*`,`.mlBattle*`,`.mlKillChain*`,`.mlKillStep`,`.mlContest*`,`.mlCompare*`,`.mlMechanism*`,`.mlDecision*`,`.mlCockpit*`,`.mlCommandBar`,`.mlAction*`,`.mlScoreSplit`,`.mlFalsifierSwitch`,`.mlMobileDrillRail`,`.mlLegend`,`.mlPressure*`/`pressureGrid`. **그리고 `.mlXCell.high`/`.mlXCell.medium`/`.mlXCell.low`/`.mlXCell.blocked` 배경색 규칙 삭제**(이중 인코딩 제거 — 색=증거상태 단일 축 보존). **계승:** `.mlModal`,`.mlHead`,`.mlTitle`,`.mlKicker`,`.mlAsOf`,`.mlTabs`,`.mlAlwaysNote`,`.mlBody`,`.mlGate*`,`.mlReleaseRail`/`.mlRail*`,`.mlPhaseStrip`,`.mlDrill*`,`.mlContributionPanel`/`.mlEvidence*`,`.mlCoMove*`/`.mlScatter*`/`.mlCorr*`,`.mlSrc*`,`.mlQuality*`/`.mlModel*`,`.mlEdge*`,`.mlFocus`,`.mlBlock*`,`.mlCheck`,`.mlFalse*`,`.mlNote`,`.mlScenario`(경로 fold),`.mlDriver*`(경로 fold). **신규:** `.mlMap`(`--ml-map-panel`)/`.mlMapFocus`(`--ml-map-focus-bg`·opacity 1·읽기 1차)/`.mlMapGrid`(`--ml-grid-recede`·읽기 2차)/`.mlMapHead`/`.mlMapRow`/`.mlMapCell`/`.mlMapChip::before`(4상태), `.mlPulseStrip` 값 13px 변형, 블록 A~D 레이아웃(`--ml-block-gap`), 모바일 `@media(max-width:560px)` Map 카드 전환·Pulse 스와이프. (companyAnchor `::after` 추가 안 함 — §3.3.)

### 8.2 `macroLens.ts` (view-model 정리)

**삭제:** `MacroLensTab`에서 `'regime'|'scenario'` 제거 → **`MacroLensTab = 'dashboard' | 'transmission' | 'sources'`**(내부 키 transmission/sources 유지=드릴다운 goto 무변경, 라벨만 §3.1). verdict 타입군 전부(`MacroVerdictDirection`/`MacroVerdictClaimLevel`/`MacroVerdictComponentView`/`MacroVerdictDriverGateView`/`MacroVerdictKillStepView`/`MacroVerdictDriverView`/`MacroVerdictContestRowView`/`MacroVerdictContestView`/`MacroVerdictFlipView`/`MacroVerdictActionView`/`MacroVerdictView`). `MacroLensSnapshot`에서 `verdict` 필드 제거. 생산자 `buildMacroVerdict` + verdict 전용 헬퍼(`buildDriverGates`/`buildDriverKillChain`/`buildVerdictActions`/`verdictDirectionLabel`/`impactDirectionLabel`/`verdictComponent`/`contestSideLabel`/`verdictGateStatus`). `buildMacroLensSnapshot`/`buildMarketMacroLensSnapshot`의 `verdict:` 생산 라인 삭제. 삭제 후 `Grep '\.verdict'` 전 소비처 0 확인(컴파일 게이트가 잡음).

> `'drivers'`도 `MacroLensTab`에서 제거되나 `'dashboard'`로 *대체*다. transmission/sources 키 그대로.

**계승 (verdict 독립 — 무변경):** `buildDrivers`,`applyTransmissionDriverLineage`,`buildEdges`,`buildEdgesFromTransmission`,`buildExposureQuality`,`normalizeExposureQuality`,`buildEvidenceGates`,`buildReleaseRail`,`buildSourcePackets`,`buildContributionStacks`,`buildCoMoveGates`,`buildFalsifiers`,`buildMissing`,`buildScenarios`(경로 fold),`buildRegimeQuadrant`(좌측 입구용),`buildMacroPath`,`buildMacroGlanceView`,`phaseView`,`quantEvidenceOpen`/`quantEvidenceBlocks`.

**신규 (헬퍼 2개):** 현 dialog 안 `buildExposureRows()`를 view-model로 이관·export. **cap 8→6 축소(시각·테스트 영향):** 현 helper는 `drivers.slice(0, 8)`이라 8행을 만들고, 현 template은 그 결과를 `.slice(0, 6)`으로 6행만 렌더한다(소비단 축소). 이관 시 cap을 6으로 통일해 *생산단에서* 6행으로 자른다 — 이는 §5.3 6행 목업·§9.1 `row ≤ 6` 단언과 정합을 위한 *실변경*이다(no-op 아님). 8 유지 시 296px 높이 산식·면적 게이트가 어긋나므로 반드시 6으로 고정. 정렬·select·tie-break 포함:
```ts
export interface MacroExposureMatrixRow {
  driver: MacroDriverView;
  cells: (MacroTransmissionEdgeView | null)[]; // length === channels.length
  filledCount: number;                          // 정렬·sparsity용
}
export function buildExposureMatrixRows(
  drivers: MacroDriverView[], topPressures: MacroDriverView[],
  edges: MacroTransmissionEdgeView[], channels: MacroChannel[]
): MacroExposureMatrixRow[]   // filledCount 내림차순 정렬 후 slice(0,6)

export function pickFocusCell(
  rows: MacroExposureMatrixRow[]
): { driver: MacroDriverView; edge: MacroTransmissionEdgeView; channel: MacroChannel } | null
  // observed > sectorPrior > template;
  // tie-break: confidence(high>medium>low) → 채널 우선순위(revenue>margin>valuation>balanceSheet>cashFlow) → driverId 사전순 (change·lag 길이 안 씀);
  // 동일 입력 → 동일 출력 결정성 보장; 셀 0개면 null(→ §6.2 폴백).
```
(dialog는 이 export 호출. 새 데이터·새 필드 0, 순수 재배치+정렬+select.)

### 8.3 `TerminalSurface.svelte`
- `let macroLensTab = $state<MacroLensTab>('regime')` → `'dashboard'`.
- `openMacroLens(tab: MacroLensTab = 'regime', …)` → `= 'dashboard'`.
- `openMacroLens('regime', '')`(bootScreen) → `openMacroLens('dashboard', '')`.
- 나머지(snapshot 생산, `activeEcon`, `chartCtl.econ`) 무변경.

### 8.4 `panels/LeftRail.svelte`
- `onMacroLens?.('regime', 'KR')`(콜사이트 line 113) → `('dashboard', 'KR')`. RegimeQuadrant/MacroPathRail 마크업 무변경.

### 8.5 콜사이트 전수 SSOT
`MacroLensTab`에서 `'drivers'`/`'regime'`/`'scenario'` 제거 시 dangling 리터럴이 svelte-check/tsc를 깬다. 전수 교체(전부 commit 2). `'drivers'`/`'regime'`는 *유지되는 함수/버튼 안에도* 살아있으므로 외부 콜사이트뿐 아니라 dialog 내부 리터럴도 함께 닫는다:

| # | 파일 | 현재 | 교체 |
|---|---|---|---|
| 1 | `TerminalSurface.svelte` | `$state<MacroLensTab>('regime')` | `'dashboard'` |
| 2 | `TerminalSurface.svelte` | `openMacroLens(tab = 'regime', …)` | `= 'dashboard'` |
| 3 | `TerminalSurface.svelte` | `openMacroLens('regime', '')`(bootScreen) | `openMacroLens('dashboard', '')` |
| 4 | `panels/LeftRail.svelte` | `onMacroLens?.('regime', 'KR')`(line 113) | `('dashboard', 'KR')` |
| 5 | `charts/ChartMenus.svelte` | `onMacroLens?.('drivers')` | `onMacroLens?.('dashboard')` |
| 6 | `charts/ChartRibbon.svelte` | `onMacroLens?.('drivers')` | `onMacroLens?.('dashboard')` |
| 7 | `panels/MacroLensDialog.svelte` | `inspectEvidenceGate`의 `id === 'macroData' ? 'drivers'`(line 186) | `'dashboard'` |
| 8 | `panels/MacroLensDialog.svelte` | `mlMatrixDriver` 버튼 `goto('drivers', row.driver.id)`(line 548) | `goto('transmission', row.driver.id)` |

> 재현: `Grep "onMacroLens\?\.\(|openMacroLens\(|goto\('drivers'|\? 'drivers'" ui/packages/surfaces/src/terminal`. 이 grep은 `macroLens.ts`의 verdict 빌더 내부 `tab: 'drivers'`(`buildDriverKillChain`, line 1128)·`tab: gate.id === 'macroData' ? 'drivers' : 'transmission'`(`buildMacroVerdict`, line 1522)·`tab: 'drivers'`(`buildMacroVerdict`, line 1536)도 히트하나, **이 셋은 모두 §8.2에서 삭제되는 verdict 빌더(`buildDriverKillChain`/`buildMacroVerdict`) 내부라 verdict 레이어 삭제로 자동 소멸한다 — 별도 교체 불필요(8곳 표 대상 아님).** `CenterStack.svelte`의 `onMacroLens={…}`는 prop 전달일 뿐 탭 리터럴 호출 아님 → 교체 대상 아님. `goto('transmission', …)` 드릴다운은 키 유지(교체 대상 아님). 8곳 교체 + verdict 자동 소멸 후 `'drivers'`/`'regime'`/`'scenario'` 리터럴 0 → commit 2 이후 독립 빌드 통과.

### 8.6 무변경 (명시)
`RegimeQuadrant.svelte`, `MacroPathRail.svelte`(입구) · `terminal.css` `.scrModal`(min960×88vh) · 데이터 origins/fetch 레이어 · `CenterStack.svelte`(prop 전달만).

---

## 9. 테스트/검증 계획

### 9.1 vitest `macroLens.test.ts`
- **삭제:** verdict 케이스 전부(`verdict.score`/`claimLevel`/`killChain`/`flip`/`contest`/`actions`). verdict 타입 import 제거.
- **유지:** `buildRegimeQuadrant`/`buildMacroPath`/`buildMacroGlanceView`/`buildScenarios`(verdict 비의존).
- **신규:**
  - `buildExposureMatrixRows`: row ≤ 6, `cells.length===channels.length`, edge 셀 `evidenceLevel`∈{observed,sectorPrior,template}, blocked→LOCK, **filledCount 내림차순(동률 시 입력 driver 순서 안정 유지)**, **8개 이상 입력 시 정확히 6행 cap**, **filledCount 전 동률(=1) 입력에서 drop되는 행 = 입력순 마지막 행(결정성 단언 — EDGE_TEMPLATES 순서 비의존)**.
  - sparsity 실측 회귀: semiconductor fixture 채움 6~7, software fixture ~4(채움률 ≤27%). 동일 채널 복수 driver가 별도 행으로 분리됨(밸류 열 2 driver = 2 행).
  - `pickFocusCell`: observed 우선; **tie-break — 동일 OBS 다수(EXPORT·PPI_SEMI·BAMLH0A0HYM2, 전부 medium)일 때 채널 우선순위로 매출 채널 edge(EXPORT)가 초점(change·lag 길이 무사용 단언)**; **결정성 — 동일 입력 2회 호출 시 동일 driverId 반환(진입마다 흔들림 회귀 가드)**; 셀 0개 null.
  - 초점 사슬: 반환 edge에 `financialLine`·`valuationLever` 존재(사슬 렌더 입력 보장); **강제 주입 fixture로 `lagMonths===null` 초점 edge를 만들면 사슬 렌더 입력이 빈 괄호 없이 직결 처리됨(방어 규칙 단언 — 라이브 EDGE_TEMPLATES엔 null-lag edge 없음)**.
  - **정량 미래배선 silent-drop 가드:** `normalizeExposureQuality`에 `status:'quantCandidate'` payload를 강제 주입한 Company fixture로 snapshot을 만들었을 때 `buildExposureMatrixRows`·Gate Strip 입력이 **throw 없이 정상 생성되고, 첫 화면 행/Gate에 quantCandidate가 노출되지 않으며 근거 탭 경로(exposureQuality)에만 살아있음**. "영구 제거"가 미래 데이터에서 silent drop이 아님을 고정.
  - Pulse 소스: relevance!=='context' driver ≤ 6, 각 tile `value`+`asOf`+`source` 존재.
  - 정량 LOCK status별: `blocked`(지배)→`회사 회귀 부재` + 실제 blockedReason + 대체가치 문구 + 자동해제 약속 *부재*; `qualitativeOnly`→`정성 경로만`; `quantCandidate`→라이브 0 단언(분포 회귀 가드).
  - 정량 게이트 첫화면 비노출: Gate Strip 입력에서 quant id 제외(4개만), 첫 화면 입력에 정량 행 없음.
  - 가드: snapshot에 `verdict` 부재, JSON에 `score`/`directionScore`/`/100` 부재.
  - `MacroLensTab`에 `'regime'`/`'scenario'`/`'drivers'` 부재(tsc 게이트).

### 9.2 `tests/audit/checkUiDataWiring`
view-model만 건드리고 raw fetch·직접 URL·자체 캐시 Map 신설 0 → 통과 유지.

### 9.3 Playwright 첫화면 smoke
- overflow(데스크톱): 1280×800 `.mlBody scrollHeight <= clientHeight + 4`.
- 면적 주역: `.mlMap.offsetHeight / .mlBody.clientHeight >= 0.40`(목표 ~0.53). `.mlBody`는 헤더·탭·캡션 제외 스크롤 영역(§5.2).
- **CSS 도형 칩 존재:** `.mlMapChip` 4상태 각각 `::before` computed style이 기대 형태(OBS=border-radius 50%+filled background, PRIOR=inset box-shadow 반채움, TPL=dashed border+transparent, LOCK=repeating-linear-gradient+border-radius≤3px) — 글리프 폰트 무의존 검증.
- **초점 배경 중립 검증:** `.mlMapFocus` background에 `--up`/`--dn` 미사용(computed background-color가 초록/빨강 계열 아님), `.mlMapFocus` opacity가 1(닷그리드 .82 미상속).
- **셀 배경 단일 축:** `.mlMapCell`/`.mlXCell`에 confidence 기반 초록/주황/빨강 배경 부재.
- overflow(모바일): 390×844 가로 스크롤 0(`scrollWidth <= clientWidth + 1`).
- 7초 4요소 가시: (1)Pulse 6 tile 값 (2)Map 초점 사슬 텍스트 (3)닷그리드 OBS/PRIOR/TPL 칩 (4)Release next 날짜 `toBeVisible`.
- 금지 표현 0: `매수`/`매도`/`목표주가`/`/100`/`판정`/`kill-chain`/`flip`/`방향 대결`/`분기 누적 시 OPEN` 0건.
- 공통배선: :8400 없이(퍼블릭) 다이얼로그 렌더.

### 9.4 svelte-check / tsc
`MacroLensDialog.svelte` + `macroLens.ts` + `TerminalSurface.svelte` + `LeftRail.svelte` + `ChartMenus.svelte` + `ChartRibbon.svelte` 0 error. verdict 타입 + `'drivers'`/`'regime'`/`'scenario'` 리터럴(외부 콜사이트 + dialog 내부 포함) 삭제 후 dangling 0.

### 9.5 운영자 눈검수 체크리스트 (push 전 필수)
**렌더 스크린샷 첨부 의무:** 1280×800 + 390×844 실제 렌더 스크린샷 첨부. **진입 0.5초 정성 체크:** 5초 노출 후 "무엇을 먼저 읽었나" 1문항(면적 proxy가 첫 시선을 보장 못 함).
- [ ] 다이얼로그를 열 때 테두리 패널(Map)이 면적으로 먼저 들어오는가(Pulse 숫자가 아니라).
- [ ] 읽기 1→2가 작동하는가 — 초점 사슬 1줄이 먼저 잡히고 닷그리드가 옅게(2차)로 읽히는가(경합 없는가).
- [ ] Map이 표가 아니라 채널 지도로 읽히는가(채널 열 클러스터·빈 셀 0·채워진 칩 부각, software 4채움 포함).
- [ ] CSS 도형 칩 4상태가 24px에서 색 없이 즉시 구분되는가(OBS 꽉찬원 / PRIOR 좌반원 / TPL 점선빈원 / LOCK 빗금사각).
- [ ] 초점 사슬이 "무엇이 어떻게·언제·어떤 증거로 닿나"를 즉시 답하는가. lag 없는 초점에서 빈 괄호가 안 보이는가. tie-break로 진입마다 흔들리지 않는가.
- [ ] 색이 방향(수혜/피해)으로 오독되지 않는가(OBS 진함을 "좋음"으로, 초점 배경을 "호재"로 읽지 않는가).
- [ ] OBS 칩을 '회사 관측'으로 오독하지 않는가(섹터 관측 표기 확인).
- [ ] sign='mixed'가 ±로 보이는가(USDKRW→매출이 +로 단정되지 않는가).
- [ ] 정량 게이트가 첫 화면 D블록에 안 보이는가.
- [ ] 닷그리드 칩에 클릭 어포던스(cursor·hover 강조)가 있는가.
- [ ] 동일 채널 복수 driver(밸류 열)가 별도 행으로 깔끔히 분리되는가.
- [ ] 모바일 Map 카드 리스트가 가로 스크롤 없이 읽히는가, 첫 화면 fold 안에 A·B·초점 사슬이 들어오는가.
- 통과 후에만 UI push(운영자 명시 승인 "올려").

---

## 10. 롤백 전략

- **commit 경계 = 빌드 통과 단위(원자):**
  - **commit 1:** `macroLens.ts` verdict 타입/함수/필드 삭제(verdict 헬퍼 내부 `'drivers'` 리터럴 자동 소멸 포함) + `MacroLensTab` 3값 + `buildExposureMatrixRows`/`pickFocusCell` 이관·export(cap 6) **AND** `MacroLensDialog.svelte` `regime`/`scenario` 삭제 + `dashboard` 4블록 재조립(초점 사슬·lag null 처리·CSS 도형 칩·읽기 2단·셀 색 단일축·빈 열 collapse) + pressureGrid/mobileDrillRail/legend 삭제 + verdict style 삭제 + 신규 Map style + 정량 첫화면 제거 + dialog 내부 리터럴 교체. (타입 의존상 분리 불가 → 단일 commit.)
  - **commit 2:** 외부 콜사이트(TerminalSurface 3 + LeftRail 1 + ChartMenus 1 + ChartRibbon 1 = §8.5 #1~6) 전수 교체 → `'drivers'`/`'regime'`/`'scenario'` dangling 0, commit 2 이후 독립 빌드 통과. (commit 1이 dialog 내부 리터럴을 함께 닫으므로 commit 2는 외부만.)
  - **commit 3:** vitest 단언 교체(sparsity 실측·정량 2케이스+대체가치·tie-break 결정성·cap 6·정량 첫화면 비노출·silent-drop 가드·lag null). (테스트만 — 독립.)
- **무손실 롤백:** 데이터 생산자는 verdict 외 무변경 → revert 시 verdict 코드 + 콜사이트 리터럴 복원만으로 복귀.
- **feature 토글 불필요:** 격리 surface, UI 자동 push 금지 정책상 운영자 눈검수가 토글 역할.
- **git:** `git commit -o <명시 paths>`로 자기 변경만. UI 변경이라 commit까지만 자율, push는 운영자 "올려" 후.

---

## 11. Phase 분할

**MUST (Phase 1 — 깎기 + 첫 화면 + 시각 마감 일체):**
- view-model: verdict 타입/함수/필드 삭제, `MacroLensTab` 3값, `buildExposureMatrixRows`+`pickFocusCell`(정렬+select+confidence/lag tie-break+결정성, cap 6) export.
- dialog: `regime`/`scenario` 삭제, `dashboard` 4블록 재조립. pressureGrid·mobileDrillRail·legend 완전 삭제. verdict style 삭제. 셀 색 confidence 배경 제거(evidenceLevel 단일축).
- 초점 전파사슬(lag·재무라인·밸류레버·증거층위, lag null 직결)·CSS 도형 칩(글리프 의존 0·OBS=edge 관측 표기·mixed=±)·읽기 2단 위계(초점 opacity 1)·빈 열 collapse·정량 첫화면 제거(조건부 분기·companyAnchor 닻 둘 다 미추가).
- 콜사이트 8곳 전수 교체(외부 6 + dialog 내부 2). 탭 라벨 `계기판/경로/근거`.
- vitest + svelte-check 0err(6파일) + Playwright(overflow·면적주역·CSS도형칩·초점 중립배경·셀 단일축·7초 4요소·금지표현) + silent-drop 가드.
- 운영자 렌더 스크린샷 검수(§9.5) 의무.

**SHOULD (Phase 2 — 드릴다운·잔여 마감):**
- 셀 클릭→`경로` 드릴다운 정교화(기존 `mlDrill`/`mlContributionPanel`/`mlCoMove` 계승).
- `scenario` + 상세 driver 표를 `경로` 탭 `<details>` 강등 마감(상한 2).
- 모바일 카드 전환 미세 조정·`aria-label` 전수.

**WON'T (범위 아님):**
- 새 데이터 소스/per-company precompute/실제 발표 캘린더·vintage/분기 회귀 파이프라인(없으면 안 만든다 — notWiredYet).
- Sankey/country map/fan chart/peer comparator(보류).
- macro 엔진(`src/dartlab/macro`) 변경(view-model 재설계만).
- AI·verdict 재계산 부활(영구 금지).

---

## 12. 이중 평가

### 12.1 전문 개발자(시니어 프론트)
- commit 1이 큰 원자 단위(view-model+dialog+dialog 내부 리터럴). 타입 의존상 분리 불가 → svelte-check 안전망 + §10 명시.
- PRIOR 칩(좌측 반채움)을 linear-gradient hard-stop이 아니라 inset box-shadow로 그린다 — 일부 저해상에서 경계 흐림 가능하나 형태군(원 vs 사각)이 1차 단서이고 반채움은 보조. 운영자 스크린샷 확인.
- 초점 select null 극단(macro.json 결손) — §6.2 폴백 카드 + Pulse 2차 승격. 빈도 매우 낮음.
- cap 8→6은 실변경이므로 sparsity/면적 테스트가 6 기준으로 고정됨(§9.1) — 8 잔존 시 즉시 fail로 회귀 차단.
- `normalizeExposureQuality`가 quantCandidate를 통과시키므로 미래 배선 시 첫 화면에 quantCandidate가 들어올 수 있다 — §9.1 silent-drop 가드 테스트로 안전 무시를 고정(영구 제거 ≠ 데이터 손실).

### 12.2 PM
- 강등 2건(scenario·상세 driver 표)은 경로 탭으로 이동(정보 손실 0, 접근 +1클릭). pressureGrid·mobileDrillRail·legend는 실삭제(부분 승리). README 명시.
- 정량 지배 케이스 `blocked`(2645·94%·회사 회귀 부재) — 사용자가 "거의 다 잠겨있네"로 느낄 수 있으나 첫 화면에서 빠지고 근거 탭에 대체가치 문구(co-move·sectorPrior)와 함께 표시 → 가짜 OPEN보다 명확한 LOCK.
- 정량이 라이브에 0이라 첫 화면 분기·회사 닻을 영구 제거 — 미래 배선 시 한 곳에 다시 추가하는 비용은 받아들인다(dead code 무존속이 더 깨끗).
- 초점 tie-break에서 change 절댓값을 의도적으로 배제한 결정은 "움직임=신호 오독" 차단이다 — 미래 세션이 "change 큰 driver를 초점으로"라고 회귀 제안하면 이 가드가 막는다(상관≠인과의 select 단계 적용).
- UI push 게이트 리드타임 — 시각 회귀 가드는 의도된 비용.

---

## 13. 성공/실패 기준 (측정 가능 — 7초 가독성 최상위)

**성공 (전부 충족):**
1. **[최상위] 운영자 7초 눈검수(§9.5) 통과 + 렌더 스크린샷 첨부** — 테두리 Map 면적 우선, 읽기 1→2 작동, 채널 지도(빈 열 collapse·software 4채움 포함), CSS 도형 칩 4상태 24px 변별, 색 방향 오독 없음, OBS=섹터 관측 오독 없음, 정량 첫화면 비노출, lag 없는 초점 빈 괄호 없음.
2. 면적 주역 `.mlMap.offsetHeight / .mlBody.clientHeight >= 0.40`(Playwright, `.mlBody`=캡션 아래 스크롤 영역).
3. 첫 화면 4질문 `toBeVisible`: 무엇이 움직였나(Pulse)·어느 채널(Map)·관측/prior(칩)·무엇 보면 바꾸나(Release).
4. 첫 화면 섹션 ≤ 4블록, 탭 ≤ 3개, 경로 탭 펼친 섹션 ≤2·`<details>` ≤2(grep). 첫 화면 fold 0.
5. 화면 텍스트에 `매수/매도/목표주가/판정/score/100/kill-chain/flip/방향 대결/분기 누적 시 OPEN` 0건.
6. `.mlBody` 데스크톱(1280×800) 무스크롤, 모바일(390×844) 가로 스크롤 0.
7. svelte-check/tsc 0 error(6파일), checkUiDataWiring 신규 위반 0, vitest green(silent-drop·lag null 가드 포함).
8. CSS 도형 칩 `::before` computed style 단언 PASS + 초점 배경 중립(--up/--dn 미사용·opacity 1) + 셀 색 단일축(confidence 배경 부재) PASS.
9. [부차] 신규 Map/chain/chip 마크업·tie-break·정량 2케이스 매핑 추가분을 상쇄한 뒤 코드 순삭감 ≥ 400줄.

**실패 (하나라도 재작업):**
- Map 면적 비율 <40% / 읽기 1→2 미작동(경합·과부하 재현) / Map이 스프레드시트로 읽힘(채널 열 클러스터 미작동·빈 셀 잔존).
- CSS 도형 칩 4상태 24px 변별 안 됨.
- 단일 점수·"판정"문 잔존 / 셀 색이 빨강·초록 방향으로 읽힘(confidence 배경 잔존) / 초점 배경이 호재(초록)로 읽힘.
- OBS 칩이 '회사 관측'으로 오독됨 / sign='mixed'가 +로 단정됨 / 전파 게이트가 템플릿인데 OPEN으로 그려짐 / lag null 초점이 빈 괄호로 렌더됨.
- 정량 LOCK이 충족 불가 약속 위장 / 정량 게이트가 첫화면 점유 / dead 조건부 분기·companyAnchor 닻 잔존 / 미래 quantCandidate가 첫 화면에 silent drop 또는 오노출.
- 콜사이트 dangling으로 svelte-check 에러(`'drivers'`/`'regime'`/`'scenario'` 잔존) / 경로 탭 `<details>` 3개 이상.
- 데스크톱 88vh 초과 스크롤 / 모바일 가로 스크롤.
- 코드가 추가로 끝남(삭제 없이 또 패널).

---

## 부록 — 채택/폐기 요약 (한눈)

| 항목 | 결정 |
|---|---|
| verdict score/100 · battle board · flip · command bar · kill-chain · contest · A/B · mechanism · cockpit · verdict drivers · decision grid | 폐기(삭제 ~600줄) |
| pressureGrid · mobileDrillRail · legend | 완전 삭제(중복·정보 손실 0) |
| `판정`(regime) 탭 | 폐기 → 탭 3개(계기판·경로·근거, 키 dashboard/transmission/sources) |
| `시나리오` 탭 | 강등 → 경로 탭 `<details>` |
| Phase · Driver Pulse · **Exposure Map(단일 테두리 주역·초점 전파사슬+닷그리드 2단·CSS 도형 칩)** · Gate(quant 제외 4) · Release | 첫 화면 승격(계승) |
| 정량 게이트 | 첫 화면 제거 → 근거 탭(status별 분기: 라이브 blocked 2645·qualitativeOnly 157·quantCandidate 0. companyAnchor 닻 영구 미추가·미래 배선 silent-drop 가드) |
| 셀 색 축 | confidence 색배경 삭제 → evidenceLevel→형태 단일 축 |
| OBS 칩 의미 | 'edge 관측(회사 회귀 아님)' 명시 표기 |
| sign='mixed' | ±(중립) 고정(가짜 정밀 차단) |
| lagMonths=null 초점 | lag 마디 생략·직결(빈 괄호 금지) |
| 전파 게이트 디폴트 | 템플릿 edge면 WATCH/blocked(OPEN 디폴트 금지) |
| 초점 tie-break | confidence→채널 우선순위(매출>마진>밸류>차입>현금)→driverId 사전순 (change·lag 길이 배제·결정성) |
| `buildExposureMatrixRows`(cap 6) + `pickFocusCell` | 신규 2개(재배치·정렬·select, 새 필드 0) |
| 콜사이트 8곳 전수 교체(외부 6 + dialog 내부 2, verdict 헬퍼 내부 리터럴은 자동 소멸) | commit 1·2 빌드 통과 필수 |
| 입구(RegimeQuadrant/MacroPathRail) · 모달 크기 · 공통배선 · 상태 라벨 | 불가침 유지 |