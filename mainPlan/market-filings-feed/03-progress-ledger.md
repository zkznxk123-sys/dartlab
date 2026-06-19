# 03 — 진행 원장

## 상태

- **2026-06-19**: PRD v0.1 작성 완료. 전문에이전트 토론(`wf_9f54e359-0c8`, 10에이전트·1.13M 토큰·19분: 5 도메인 설계 → 4 적대검증 → 종합) + 세션 코드 실측. **구현 0** — 착수 대기(운영자 go).
- **검증 평결**: 데이터층 옵션 B 만장일치, 4 적대검증 전부 코드 실측 대조 통과. 종합이 *스스로* 자기 주장 2건 정정(옵션A falldown 메커니즘 오류·worker 파일명 endsWith 함정) = 검증 작동 증거.
- **핵심 실측 SSOT**(설계 초안 정정값): 3개월 rolling = **38,015행 / 656KB** · etc(윈도) = **20.3%** · 기관 식별률 = **9.5%** · recent.parquet = stock_code 정렬(날짜 pruning 0건).

## NEXT (재개 포인터)

> 운영자 go 시 **Phase 0(데이터층 bake)부터** — UI 무관·자동 push 가능 단위. 그 뒤 Phase 1(read 배선)·2(분류기)는 UI 미배선이면 자동 push, Phase 3(좌측 UI)는 운영자 명시 승인 후에만 push.

1. **Phase 0 — bake (백엔드/CI, 단독 ship):** `buildAllFilingsRecent.py` build() 끝에 ① `push()` `path_in_repo` 인자화 ② cutoff=데이터max−90d 동적 ③ `.filter().sort(rcept_dt desc).write_parquet(rg5000, zstd)` ④ size assert(>1.5MB CI 실패) ⑤ 파일명 `dart/allFilings/market_recent.parquet`(worker 600s 자동) → HF push. 검증=HF 656KB·rcept_dt desc·6컬럼.
2. **Phase 1 — read 배선 (5곳):** contracts corpName + `loadMarketFeed(core)` + 어댑터 3곳(public/local/fake) filing 포트. core.requestParquetWholeFile 경유. 단위테스트.
3. **Phase 2 — 분류기:** eventRail.ts 정규식 export(classifyFiling 불변) + `marketFeedCategory()` + `isInstitutionalFiler()`. 이벤트레일 골든 회귀 0.
4. **Phase 3 — 좌측 UI:** eIndustry swNote/swMore 축약 + eMarketFeed 고정높이 섹션 + 칩 스트립 + .feedRow(div role=button + 중첩 a) + 상태기계 + 200cap 라벨 + [기관] 보조칩. svelte-check 0 + 스크린샷 눈검수. **UI push 운영자 승인.**
5. **Phase 4(선택):** worker B안 채택 시만. A안(`market_recent.parquet`)이면 불필요.

## 열린 결정 (착수 전 운영자 확인)

1. **캐시정책** — A안 `market_recent.parquet`(worker 배포 0) vs B안 worker 분기+CF 재배포. → **A안 권장**.
2. **시간창** — 3개월 고정(656KB) vs 6개월(1322KB·임계 86%). → **3개월 권장**.
3. **기관 사전 범위** — 광의(~10% 식별·일부 오매칭) vs 협의(정밀↑ 재현↓). → 광의+정직 라벨.
4. **임원소유 도배** — 탭 분리로 충분 vs 집계+접힘 그룹핑. → **v1 그룹핑 금지**(탭+200cap+카운트).

## 메모리 포인터

`MEMORY.md` §6.2에 `[[project_terminal_market_filings_feed]]` 등록(포인터만, SSOT=본 폴더).

## 경계 (다른 PRD — 소비만)

terminal-improvement(watchlist·델타·freshness) / periodic-report-dossier(단일기업 정기보고서 비재무) / industry-analysis-lab(섹터) / table-export(egress) / scenario-simulator(미래). 이 기능 = '시장 전체 수시공시 시간순 피드' 한 점.
