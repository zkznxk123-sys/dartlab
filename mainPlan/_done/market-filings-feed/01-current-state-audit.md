# 01 — 현 상태 실측 감사 (전체상장사 시장 공시 피드)

> 본 문서는 **측정값·코드 사실**만 담는다. 설계 결정은 전문에이전트 토론(`wf_9f54e359-0c8`) 종합 후 02~로 분리. 직전 정기보고서 PRD 교훈("데이터경로를 추적 없이 주장") 차단 — 모든 feasibility는 아래 실측 위에서만.

## 0. 과제 정의

운영자 명령: *"우측 공시는 기업 한 개 개념인데, 좌측 패널 산업쪽 높이 조금 줄이고 그 아래에 공시 최근 3개월꺼 리스트업. 이건 전체상장사고 카테고리별 탭을 세부적으로 — 특히 자기거래·내부자거래·연금·기관·주주변경 등 주가영향 공시."*

핵심 = **멘탈모델 전환**: 우측 = *선택한 한 회사*의 공시. 신규 = 좌측에 *시장 전체*(전상장사) 최근 3개월 수시공시 흐름을, 주가영향 카테고리로 세분.

## 1. 데이터 소스 실측 — `data/dart/allFilings/recent.parquet`

| 항목 | 측정값 |
|---|---|
| 경로 | `data/dart/allFilings/recent.parquet` (HF: `eddmpython/dartlab-data/dart/allFilings/recent.parquet`) |
| 크기 | 1.89MB (zstd) |
| 행 수 | 210,963 |
| row-group | 11개 (각 ~2만행) |
| 종목 수 | 2,659 (전상장사) |
| 컬럼(6, 전부 string) | `stock_code` · `corp_name` · `rcept_dt`(YYYYMMDD) · `report_nm` · `rcept_no`(14자리) · `flr_nm`(제출자명) |
| 본문 | **없음** — 메타만 (content_raw 제외, 일자별 원본 `{YYYYMMDD}.parquet`에만 있음) |
| 빌드 | `.github/scripts/sync/buildAllFilingsRecent.py` (정기공시=사업/분기/반기보고서는 이미 제외 → 자연히 수시공시) |

### ★ 결정적 제약 — 정렬 = `stock_code` (날짜 pruning 불가)

row-group 경계 실측 (각 RG의 stock_code min/max, rcept_dt min/max):

```
 rg     rows   sc_min   sc_max     dt_min     dt_max
  0    20000   000020   003530   20240902   20260612
  5    20000   060230   086900   20240902   20260612
 10    10963   439580   950250   20240902   20260612
```

- 11 row-group이 **stock_code로 단조분할** → 회사코드 filter는 해당 RG만 읽어 효율적.
- 그러나 **모든 RG의 `rcept_dt` min/max가 동일**(20240902~20260612) → **날짜 기준 row-group pruning 불가능**.
- ⇒ "전체 시장 최근 3개월"을 뽑으려면 **11 RG 전체(1.89MB, 210,963행)를 읽고 클라이언트에서 날짜 필터**해야 한다. 이게 이 기능 데이터층의 핵심 갈림길(02 §데이터층에서 옵션 A 전체읽기 vs B CI bake 결정).
- 코드 근거: [nonRegularFilingsSource.ts:1-4](../../ui/packages/runtime/src/adapters/public/sources/nonRegularFilingsSource.ts#L1-L4) 주석 — *"통합파일은 stock_code 정렬이라 filter pushdown 이 회사 row-group 만 읽음"*.

### 시간창 실측 (두 cutoff 정의 — PRD는 rolling 채택)

| cutoff 정의 | 행 수 | bake 크기(rg5000) | 비고 |
|---|---|---|---|
| 캘린더 today−3mo (`>=20260320`) | 33,686 | — | 데이터 7일 stale 시 누락 |
| **데이터max−90d rolling (`>=20260314`)** | **38,015** | **656.3KB** | ★PRD 채택(빈 피드 방지) |
| 데이터max−180d (6개월, `>=20251214`) | 79,167 | 1,322KB | 임계 1,536KB의 **86%**(가변·비권장) |

> ⚠ 적대검증 정정: 설계 초안의 "33,686행·562.9KB·0.3MB"는 캘린더 cutoff 기준 과소. **rolling 90일 = 38,015행 / 656KB**가 정본. 6개월은 "여유"가 아니라 임계 86% 근접.

## 2. 카테고리 분류 실측

### 기존 `classifyFiling`(eventRail.ts)을 적용 시 — 윈도가 결정적

[eventRail.ts:35-43](../../ui/packages/surfaces/src/terminal/lib/eventRail.ts#L35-L43) — reportNm 키워드 6버킷. **★적대검증이 진짜 `classifyFiling`을 3개월 윈도에 적용해 정정**:

| 버킷 | 3개월 윈도(정본) | 전체파일·간이복제(과장) |
|---|---|---|
| exchange(거래소) | 28.5% | 15.2% |
| equity(지분) | 26.1% | 27.4% |
| **etc** | **20.3%** | 36.6% ← 윈도 무시 over-claim |
| issue(발행) | 9.9% | 10.6% |
| major(주요사항) | 9.0% | 7.7% |
| audit(감사) | 6.2% | 2.6% |

→ etc는 1/3이 아니라 **1/5(20.3%)** — 게다가 etc 내용물은 IR개최·지배구조보고서·기준일설정 등 **약신호 행정공시**라 "숨겨진 신호" 아님. 진짜 문제는 **exchange 28.5%·equity 26.1% 두 거대 바구니가 주가영향을 뭉개는 것**: 자기주식이 major에, 최대주주·공급계약·잠정실적이 exchange에, 임원소유와 5%대량보유가 한 equity에 묻힘. ⇒ 시장피드 전용 분류로 **재투영**(etc 줄이는 만능분류기 아님). 단, `classifyFiling`은 시그니처가 `reportNm` only라 flr_nm 기관판정 불가 → 형제 함수 필요.

### 사용자 요구 카테고리 식별 가능성 (report_nm 텍스트, 최근3개월 건수)

| 카테고리 | 식별 패턴(report_nm) | 건수 |
|---|---|---|
| 내부자(임원·주요주주 소유) | `임원ㆍ주요주주특정증권등소유상황보고서` | 5,794 |
| 5% 대량보유 | `주식등의대량보유상황보고서` | 3,337 |
| 단일판매·공급계약 | `단일판매ㆍ공급계약체결` | 1,101 |
| 최대주주변경 | `최대주주…변동/변경` | 1,018 |
| 전환사채 | `전환사채…발행결정` | 652 |
| 유상증자 | `유상증자결정` | 592 |
| 자기주식 | `자기주식…` | 514 |
| 합병/분할 | `합병/분할…결정` | 428 |

상위 실제 제목(최근3개월): `임원ㆍ주요주주특정증권등소유상황보고서`(5367) · `정기주주총회결과`(2464) · `주식등의대량보유상황보고서(일반)`(2269) · `투자설명서(일괄신고)`(925) · `증권발행실적보고서`(893) · `기업가치제고계획(자율공시)`(523) · `연결재무제표기준영업(잠정)실적(공정공시)`(423) · `단일판매ㆍ공급계약체결`(407).

### ★ 연금/기관 식별 = `flr_nm`(제출자명)으로만 가능

- report_nm 제목엔 `연금`/`국민연금` **0건** (제목은 기관명 안 적음).
- 그러나 `flr_nm` 제출자에 직접 등장: `국민연금공단`(반복) · `BlackRockFundAdvisors` · `NorgesBank` · `자산운용`(468) · `연금`(249) · 은행/증권/보험(3,296).
- 대량보유 공시 flr_nm 샘플: `국민연금공단`·`BlackRockFundAdvisors`·`NorgesBank`(=기관) 와 `오세영`·`김담`·`박정원`(=개인/오너)가 **섞임**.
- ★적대검증 단일 실측(SSOT): **equity(지분) 9,934행 중 광의 기관패턴 flr_nm 매칭 = 940건 = 9.5%** (as-of 데이터max). 설계 초안 3종의 분모 상충(11.8/16.7/10.1%) 폐기.
- ★**위험의 방향 정정**: 지배적 오류는 '개인→기관 오분류(false positive)'가 아니라 **'기관→누락(false negative)'** — `J.P.MORGANSECURITIESPLC` 같은 명백한 기관도 점(.) 때문에 사전이 못 잡음. 증권/은행 토큰 가진 행 중 사업회사 자기보고 오매칭은 측정상 거의 0.
- ⇒ 독립 '연금/기관' 1급 탭 **불가**(88~90% 침묵=전상장사 커버 위반). '지분·내부자' 탭 내 보조 [기관] 필터칩 + `'제출자=기관(부분식별·약10%·근사)'` 범위 라벨 + flr_nm 원문 툴팁 노출(impute 금지)로만. 상세 02 범위 절.

## 3. 현 UI 구조 실측

### 좌측 패널 [LeftRail.svelte](../../ui/packages/surfaces/src/terminal/panels/LeftRail.svelte) (300px 고정폭, 공개/로컬 동일)

3섹션 세로 스택:
- **(A) eMacro** '마켓 펄스·매크로' — auto높이 ([L110-118](../../ui/packages/surfaces/src/terminal/panels/LeftRail.svelte#L110-L118))
- **(B) eIndustry** '산업 스윕' — auto높이, ScatterMap(compact)+상세버튼+노트 ([L120-131](../../ui/packages/surfaces/src/terminal/panels/LeftRail.svelte#L120-L131)). ← 운영자가 "높이 조금 줄이고"라 한 섹션.
- **(C) eQuant `fillCol`** — 남은 공간 전부 차지, **스크리너 ⇄ 공시 워치 탭 토글** ([L135-179](../../ui/packages/surfaces/src/terminal/panels/LeftRail.svelte#L135-L179)).

배선:
- 그리드 `grid-template-columns: 300px minmax(0,1fr) 496px` (terminal.css). `.col`은 flex column, gap 3px, overflow-y auto. **`.fillCol` 가진 섹션만 flex:1 1 auto** — 한 섹션만 가능.
- 하단 탭 상태는 부모가 제어: [TerminalSurface.svelte:72](../../ui/packages/surfaces/src/terminal/TerminalSurface.svelte#L72) `bottomTab: 'screener'|'watch'` (localStorage 지속), [L372](../../ui/packages/surfaces/src/terminal/TerminalSurface.svelte#L372) LeftRail에 prop 주입.
- ⇒ 신규 시장피드는 **(가) eQuant 탭바에 3번째 탭 추가** vs **(나) eIndustry와 eQuant 사이 새 섹션** 두 길. 운영자 의도("산업 아래")는 (나)지만 안티클러터·fillCol 단일제약상 (가)가 강할 수 있음 → 토론 IA 결정.

### 우측 패널 [RightStack.svelte](../../ui/packages/surfaces/src/terminal/panels/RightStack.svelte) — 단일기업 공시

- 정기공시 패널(`rt.filing.regular`) + 비정기공시 패널(`rt.filing.nonRegular`, nonRegState loading/ready/empty).
- 행 `.filingRow` 그리드: 제목 · 날짜 · ↗(DART 원문 직링크). 차트하단 이벤트레일이 `classifyFiling`으로 필터.
- 읽기 = hyparquet(안전). cf. 직전 정기보고서팩트 패널은 DuckDB로 수십초 멈췄다가 hyparquet으로 수정([companyLive.ts](../../landing/src/lib/browser/companyLive.ts), commit `e801f42f0`) — 이 교훈을 데이터층 로딩/타임아웃 설계에 반영.

## 4. 재사용 자산 (발명 아닌 추출+확장)

| 자산 | 위치 | 시장피드 재사용 |
|---|---|---|
| `classifyFiling`·`EVENT_CATS` | [eventRail.ts](../../ui/packages/surfaces/src/terminal/lib/eventRail.ts) | 분류 기반(단 etc 36.6% → 전용 확장 필요) |
| `.filingRow` CSS 그리드 | terminal.css | 행 렌더(회사명 컬럼 추가 필요) |
| `loadRecentFilingsForCodes` | [nonRegularFilingsSource.ts:62](../../ui/packages/runtime/src/adapters/public/sources/nonRegularFilingsSource.ts#L62) | read 패턴(단 stock_code 필터 제거=full read) |
| `FilingPort` | [filing.ts:77](../../ui/packages/contracts/src/filing.ts#L77) | 신규 `marketRecent()` 메서드 + 새 행 타입 필요 |
| `viewerPort.urlForCompany`/`openFiling` | viewer.ts | 행 클릭 딥링크/회사 점프 |
| `disclosureFocus.pulse` | disclosureFocus.svelte.ts | 차트↔목록 동기화(필요 시) |

### ⚠ contract 갭 — 시장피드 행 타입 신설 필요

`NonRegularFiling`([filing.ts:12](../../ui/packages/contracts/src/filing.ts#L12))은 `{rceptNo, rceptDate, reportNm, filer, url}` — **`stockCode`·`corpName`·`category` 없음**. 시장피드 행은 "어느 회사 공시인지"를 보여야 하므로(우측 단일기업과 차별의 핵심) 새 타입 필요:

```ts
interface MarketFiling {  // 신설 후보
  rceptNo; rceptDate; stockCode; corpName; reportNm; filer; category; url;
}
```

## 5. 경계 (다른 PRD 소유 — 침범 금지)

| 경계 | 소유 | 시장피드의 선 |
|---|---|---|
| 좌측 '공시 워치' 탭 | terminal-improvement(watchlist·since-last-visit 델타) | 워치=*내가 고른 종목*, 시장피드=*전상장사*. 중복 아님(다른 유니버스). |
| 우측 단일기업 공시 2패널 | (현 터미널) | 선택회사 공시. 시장피드=시장 전체. |
| 차트하단 이벤트레일 | (현 터미널) | 선택회사 공시의 시간축 점. 시장피드=리스트. |
| periodic-report-dossier | (직전 PRD) | 단일기업 정기보고서 비재무 도시에. 무관. |
