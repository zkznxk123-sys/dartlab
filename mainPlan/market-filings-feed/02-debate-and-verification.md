# 02 — 전문에이전트 토론·적대검증 정본

> `wf_9f54e359-0c8` (2026-06-19, 10에이전트·1.13M 토큰·19분). 5 도메인 설계(병렬) → 4 렌즈 적대검증(교차) → 종합 1. 본 문서 = 토론 감사 추적(audit trail). 결론은 [00-product-prd.md](00-product-prd.md).

## A. 5 도메인 설계 — 무게중심 한 줄

| 렌즈 | 무게중심 |
|---|---|
| 시장미시구조·공시 | etc 블랙홀을 쪼개되, flr_nm 기관식별 한계를 '기관 탭'으로 위장 않고 표면화 |
| 데이터 엔지니어 | recent.parquet 재사용 금지 — *읽기 경로 분리*(우측=stock_code range / 좌측=날짜정렬 whole-file GET) |
| UI/UX | "한 회사 뷰어"가 아니라 *시장 전체 디스커버리 레인* — 행 1순위=회사명, 동작=회사 점프 |
| IA·안티클러터 | 새 패널이 아니라 *멘탈모델 3분리*(시장전체/워치종목/선택회사) |
| 한국 자본시장 실무자 | 분류 정확도가 아니라 *노이즈 게이트* — 약신호(임원소유) 눌러두고 강신호(실적·계약·세력) 위로 |

**데이터층 5렌즈 만장일치 = 옵션 B**(CI bake rcept_dt 정렬 슬림 parquet → whole-file GET). 카테고리 탭은 6~12개로 분기(IA·도메인 6~7 / 엔지니어·실무자 11~12).

## B. 4 적대검증 — 렌즈별 must-fix (SHIP 전 정정 필수)

### B-1. 데이터층 주장 검증 (실측 대조)
- **survives**: ① stock_code 정렬→날짜 pruning 0건(11 rg 전부 dt 동일, statistics 직접 측정) ② govRecent 선례 1:1 ③ buildAllFilingsRecent.py 편승(새 cron 0).
- **fix**: ① 3mo 크기 562.9KB→**656.3KB**(cutoff 정의 차, rolling 90일 38,015행) ② 6mo "여유"→**1322KB=임계 86%**(가변) ③ **worker cache 파일명 게이트**(endsWith('recent.parquet') 실패→1h stale) ④ 기관식별률 9.4~9.8% ⑤ category bake "210K→0"은 논리혼선(옵션B는 38K만).
- **must-fix 5**: worker 분기 / 크기 정정+size assert / cutoff 동적 / 기관 단독탭 kill / classifyFiling equity 분리.

### B-2. 범위검증·거짓정밀 검증
- **survives**: 기관 거짓정밀 위험 진단·약신호 격리·ref-trace·호재악재 미끄럼 가드.
- **★방향 정정(fix)**: 지배적 오류는 '개인→기관(false positive, ≈0)'이 아니라 **'기관→누락(false negative)'** — J.P.MORGAN도 점 때문에 사전 누락. 칩 라벨을 '기관 매수' 단정→'제출자=기관(부분식별·약10%)'.
- **fix**: etc 36.6%→**20.3%**(윈도 기준, 전체파일 아님). etc 내용물=IR·지배구조·기준일 약신호라 '신호 구출' 과대포장 금지. worker 캐시 '한 줄' 거짓. 옵션A 기각에서 '1.5MB falldown' 메커니즘 제거(requestParquetWholeFile size 미검사).
- **must-fix 8**: 기관 라벨 명시화 / worker 분기 / etc% 정정 / 탭 6~7 수렴(12 금지) / 옵션A 근거 정정 / content_raw 부재 / corp_name COLS / UI push 게이트.

### B-3. 안티클러터·중복·경계 검증
- **survives**: 멘탈모델 3분리 코드중복 0(read경로·정렬키·범위 전부 다름) / 옵션B govRecent 선례 / 경계 PRD 침범 0(watchlist·periodic-report 재소유 없음) / 형제 분류기 정당.
- **kill**: 12탭(과세분화·300px 붕괴) / UI '옵션A whole-file 그대로'(stock_code pushdown 이점 전무).
- **fix**: fillCol 2분점(50/50 압착)→eMarketFeed max-height 고정·eQuant 단독 fillCol / '필터만 제거 한 줄'→배선 표면 5곳 / 기관 분모 단일 실측 SSOT / 임원소유 그룹핑 상태머신 v1 금지(탭 분리로 충분) / disclosureFocus.pulse v1 미사용.
- **must-fix 7**: fillCol 2분점 kill / 6탭 수렴 / 기관 독립탭 kill / worker 캐시 / 배선 5곳 명문화 / 분류 SSOT drift 가드 / 범위 라벨 3종.

### B-4. UI/UX 회귀·구현 위험 검증
- **survives**: fillCol 2개 메커니즘(가능하나 압착) / ScatterMap 안 깨짐 / 기관 독립탭 kill(report_nm '연금' 0건·9.5% 실측) / 200 cap 가상화 불필요 / 상태기계 존재 / checkUiDataWiring 통과 / 빌드 편승.
- **fix**: ① worker 캐시 파일명 게이트(별도 CF 배포) ② etc 36.6%→20.3%(윈도) ③ 3mo 656KB(rolling) ④ **`.filingRow.nonreg`는 `<a>` 행 전체라 onPick+중첩↗ 불가→`<div role=button>`+중첩`<a>` 신규** ⑤ swMap max-height 캡 금지(SVG 잘림)→swNote/swMore 축약 ⑥ '5줄'→~15줄(push path_in_repo 인자화·category 클라분류).
- **must-fix 8**: worker 캐시 / category 클라분류(bake 금지) / .feedRow 신규 요소 / 윈도 656KB·3mo 고정 / swMap 캡 금지 / 기관 칩 라벨 / 200 cap 라벨 / UI push 게이트.

## C. 종합 수렴 (4검증이 5설계를 깎은 결과)

| 쟁점 | 설계 분기 | 적대검증 수렴(정본) |
|---|---|---|
| 데이터층 | 옵션 B 만장일치 | **B** — 단 옵션A 기각근거를 'stock_code 정렬·210K 파싱'으로 정정(1.5MB falldown 삭제) |
| 카테고리 탭 | 6~12개 | **6탭+보조칩**(12 kill) |
| 연금/기관 | 탭 vs 칩 | **보조 [기관] 칩+범위 라벨**(독립탭 kill, 식별 9.5%, false-negative 방향) |
| fillCol | 2분점 vs 단독 | **eMarketFeed 고정높이·eQuant 단독 fillCol**(2분점 kill) |
| 행 렌더 | .filingRow 재사용 | **CSS만 재사용·요소 신규**(`<a>`행 한계) |
| category bake | 빌드 vs 클라 | **클라 분류**(SSOT drift 회피, report_nm 원본 유지) |
| 산업 높이 | max-height 캡 | **swNote/swMore 축약**(캡 시 ScatterMap 잘림) |
| 윈도/크기 | 33,686/0.3MB | **38,015행/656KB·3개월 고정** |
| worker 캐시 | "한 줄·자동" | **파일명 `market_recent.parquet`(A안) 또는 worker 분기(B안)** |
| 배선 비용 | "한 줄" | **표면 5곳**(source+포트+어댑터3+contract) |

## D. 이 토론이 직전 정기보고서 PRD 교훈을 어떻게 적용했나

직전 정기보고서 PRD에서 데었던 맹점 = *"데이터경로·로드상태를 추적 없이 주장"*. 이번엔 **데이터층을 토론 1순위 의제로 박고 모든 feasibility를 코드 실측에 대조**:
- recent.parquet 정렬·row-group statistics를 pyarrow로 직접 측정(stock_code 정렬 확정).
- worker.js cacheControlFor·requestParquetWholeFile·hfRange.ts 임계를 코드 라인으로 검증 → 설계 초안의 'falldown'·'한 줄'·'0.3MB' 낙관을 전부 정정.
- 기관 식별률 세 분모(11.8/16.7/10.1%)를 단일 실측(9.5%)으로 수렴.

결과적으로 종합이 *스스로* 자기 주장을 두 번 정정(옵션A falldown 메커니즘 오류·worker 파일명 endsWith 함정)했다 — 검증이 작동한 증거.
