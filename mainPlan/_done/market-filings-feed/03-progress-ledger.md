# 03 — 진행 원장

## 상태

- **2026-06-19 (PRD)**: v0.1 작성. 전문에이전트 토론(`wf_9f54e359-0c8`, 10에이전트·1.13M 토큰: 5 도메인 → 4 적대검증 → 종합) + 코드 실측. 데이터층 옵션 B 만장일치, 4 적대검증 코드 실측 대조 통과.
- **2026-06-19 (구현 완료·as-built)**: **Phase 0~3 전부 구현·검증·커밋.** 운영자 `/goal` "플랜을 정공법으로 완성"으로 착수. UI push만 운영자 승인 대기.
- **2026-06-23 (완료·_done 이관)**: 운영자 "푸시해" → master push + **Deploy Landing success 실측**. 추가 흡수: 좌측 패널을 `[공시|뉴스]` 탭으로 — **뉴스 탭 = 시장 cross 뉴스**(public rss 아카이브 `news/public/rss/{market}/{날짜}.parquet` 최근 shard 직독, mount preload, 오늘 포함). 동반: 공시 패널 높이 ↑·패널 헤더 전역 확대(16→20px·10→12px)·좌측 최상단 마켓펄스 패널 제거(RegimeQuadrant zero-ref 삭제). PRD 스코프(시장 수시공시 시간순 피드) 완결.

### as-built 커밋
| Phase | 커밋 | 내용 | 검증 |
|---|---|---|---|
| 0 bake | `77051445c` | `buildAllFilingsRecent.py` buildFeed(): 동적 cutoff·rcept_dt desc·rg5000·size assert·push 인자화 | 로컬 38,015행·656KB·desc·6컬럼·8rg |
| 0 발행 | (HF) | `market_recent.parquet` HF publish + worker `endsWith('recent.parquet')`=true→600s 확인 | HF e2e read 38,015행·콜드 3.15s |
| 1 read | `532268a73` | contracts `MarketFiling` + `loadMarketFeed`(whole-file·dedup·corp_name) + 포트 3곳(public/local/fake) | runtime/contracts tsc·data-wiring 0·단위 3/3 |
| 2 분류 | `e9a2eda40` | eventRail `RX_OWNERSHIP` export(classifyFiling 불변) + `marketFeedCategory` 6키 + `isInstitutionalFiler` | 골든 31/31·실측 분포(ownership 26.1%·기관 10.0%) |
| 3 UI | `fa1d83470` | `MarketFeed.svelte`(6탭·기관칩·.feedRow·4상태·200cap) + LeftRail 배선 + swFoot 1줄 + terminal.css | svelte-check 0err·dev 실렌더(콘솔 0) |

### 핵심 실측 SSOT (설계 초안 정정값, 구현으로 재확인)
3개월 rolling = **38,015행 / 656KB**(임계 43%) · etc(classifyFiling 윈도) 20.3% · 기관 식별률 **10.0%** · recent.parquet = stock_code 정렬(날짜 pruning 0건). marketFeedCategory etc = 58.5%(좁은 필터·의도).

### 구현 중 정공법 수정 (적대검증 외 추가 발견)
- 기관 ● 오탐: 증권사 *자기* 발행실적보고서에 ● → `flr_nm 기관 AND 제출자≠회사` 가드(자기보고 제외).
- 회사명 truncation: `.feedRow` 그리드가 소스 뒤 `.filingRow`(0,2,0)에 밀림 → `.filingRow.feedRow`(0,3,0) 특이도.
- ● 클리핑: feedCorp ellipsis가 ● 자름 → feedCorp flex(이름 ellipsis + ● flex:none).

## NEXT (운영자 결정)

1. **UI push 승인** — Phase 1~3(ui/packages/runtime·contracts·surfaces) + Phase 0(`buildAllFilingsRecent.py`)은 commit 완료, push 대기. ⚠ master에 동시 세션 미push UI 커밋 다수 → push 시 동행. 운영자 "푸시해"/"올려" 시 진행.
2. **열린 결정 4건**(아래) 중 변경 원하면 반영. 기본값(A안 파일명·3개월·광의 사전·탭 분리)은 이미 구현됨.
3. **Phase 4(worker)** = 불필요(A안 `market_recent.parquet` 채택, worker 600s 자동).

## 열린 결정 (착수 전 운영자 확인)

1. **캐시정책** — A안 `market_recent.parquet`(worker 배포 0) vs B안 worker 분기+CF 재배포. → **A안 권장**.
2. **시간창** — 3개월 고정(656KB) vs 6개월(1322KB·임계 86%). → **3개월 권장**.
3. **기관 사전 범위** — 광의(~10% 식별·일부 오매칭) vs 협의(정밀↑ 재현↓). → 광의+범위 라벨.
4. **임원소유 도배** — 탭 분리로 충분 vs 집계+접힘 그룹핑. → **v1 그룹핑 금지**(탭+200cap+카운트).

## 메모리 포인터

`MEMORY.md` §6.2에 `[[project_terminal_market_filings_feed]]` 등록(포인터만, SSOT=본 폴더).

## 경계 (다른 PRD — 소비만)

terminal-improvement(watchlist·델타·freshness) / periodic-report-dossier(단일기업 정기보고서 비재무) / industry-analysis-lab(섹터) / table-export(egress) / scenario-simulator(미래). 이 기능 = '시장 전체 수시공시 시간순 피드' 한 점.
