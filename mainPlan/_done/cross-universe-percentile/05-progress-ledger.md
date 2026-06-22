# 05 — 진행 원장

상태: **✅ 구현 완료 (2026-06-15)** · 커밋 5건 master · push 만 잔여(다른 세션/운영자 명시 승인) · `_done` 이관

## as-built (PRD 대비 진화)
완성형 한 빌드 후 운영자 눈검수 반복으로 표현이 진화 — PRD의 "막대 띠 + DistCurve 드릴다운"을 넘어섰다:
- **거처**: `ui/packages/surfaces/src/terminal/` — `panels/PercentileCrossDialog.svelte`(신규) + `lib/engine.ts`(`percentileIn`·`buildFundMetrics`·`buildQualShares`·`buildPriceStats`·`histOf`·`quantileBand`) + `lib/types.ts`(`Universe`·`UniversePercentile`·`CategoricalShare`·`PriceStat`·`Hist`) + `panels/DistCurve.svelte`(히스토그램+핀+neutral) + `RightStack.svelte`(상세보기 버튼·동적 import) + `TerminalSurface.svelte`(prop).
- **1차 시각 = 실도수 히스토그램**(막대 띠/5점곡선 폐기): 동종사 전체 값 배열 robust(p2~p98) 22빈, 봉우리·gap·왜도 그대로. 박스/KDE 기각(다봉성 은폐/bandwidth 자의).
- **회사 위치 = ▼ 핀(꼭지)** + 백분위 톤색. **하단 0라인 방향 색띠**(초록=좋은 방향, lowerBetter 반전, 가격 제외).
- 정성=등급레벨 분포 스택바(동급비중), 가격=중립 히스토그램 별격자, 값=지표명 인라인, 컬럼헤더 sticky, dim 글자 밝게(#aeb6c2), 폭 720.
- **prebuild 0 · 새 데이터 0**: 전부 브라우저 라이브(다이얼로그 open 시). 핫패스(co.percentile)는 `withHist=false`로 콜드비용 0. HF/cron/parquet 무관.
- 가드 유지: 판정 0(방향 색띠=지표 의미지 회사 판정 아님)·결손 '—'·n<10 숨김·유니버스 출처칩·cross-sector caveat·소속지수 BLOCKED.

## 커밋 (master, 미push)
`4cc6f2f83` 신설 → `7244cb103` 분포곡선 1차화 → `74b1c3ef1` baseline·값인라인·sticky → `523169d5c` 실도수 히스토그램 → `88d97bae2` 방향 색띠·핀.

## NEXT
- **push 만 잔여** — UI 변경이라 운영자 명시 승인("푸시해") 후 다른 세션/운영자가 origin/master 반영. landing dev(5173) HMR 반영 상태.
- 미해결(완성형 밖): 소속지수(구성종목 멤버십 데이터 부재 BLOCKED) · strip/beeswarm(소표본 유니버스 개별점, 선택적).

---
## (옛 기록)

상태: ~~구현 착수 (2026-06-15)~~ · 운영자 go(goal) 수신 → 완성형 한 빌드

## 결정 로그
- 2026-06-15 **구현 토론(3렌즈 병렬: 정보설계·터미널UX일관성·적대가드) + 코드 실측**. 확정 표현:
  - 메커니즘 확정 그대로(행=지표 × 열=3유니버스 띠 + 행클릭 DistCurve 3개 세로스택). **뒤집힘 = 띠 길이차 + 분산≥30 행 중립 `⇄` 표식**(Δ숫자·화살표·색인코딩 KILL — 허위정밀/판정).
  - 엔진: `industryPercentile` **무손상 유지**(co.percentile 회귀 0) + 신규 `percentileIn(code,universe)` **다이얼로그 전용**(buildCompany 비경유=콜드비용 0). 공유 `buildFundMetrics`(13지표)로 로직 복제 0. market/all band=`quantileBand` 라이브 5분위(표본<10 → null).
  - 정성(거버넌스·경영권·감사·주주환원·현금흐름)=등급칩+동급비중(`buildQualShares`, 가짜백분위 금지). 가격(PER/PBR)=raw.finance+prices 노드별 산출(valuationOf 식 재사용) 별 격자·톤색 없음·캡션(KILL#2).
  - CSS: 모달 셸만 전역(`.scrimWrap/.scrModal/.scrHead/.scrClose`) 재사용, 나머지 컴포넌트 스코프 `pcx*`(전역 `.pct*`는 `.dlTerm` 1열 격자라 부적합). 다이얼로그 **동적 import**(HoldingsDialog 패턴, 청크 무증가).
  - 배선 4지점: engine.ts(percentileIn 신설+인터페이스+반환) → TerminalSurface(prop) → RightStack(prop+버튼+동적 마운트) → PercentileCrossDialog.svelte(신규).
  - 가드 박음: n<10 띠/곡선 숨김, 결손='—'(0금지), 유니버스별 출처칩, cross-sector caveat, 소속지수 BLOCKED 명시 노트.

- 2026-06-14: PRD v0.1 작성. 4-ground 코드 실측 + 4렌즈 토론(정보설계·실현가능성·가드·PM) + 적대검증.
- 2026-06-14 **운영자 레인 분리 확정**: scan-grade-explainer = 종합평가(큰그림·판정)로 독립 개선. 본 화면 = 유니버스 교차 *분포 사실*(판정 0). → 흡수 거부, **별도 카테고리 + 공유 SSOT** 확정.
- 메커니즘: 히트맵 reject → 축별 행 × 유니버스 열 띠 + DistCurve 드릴다운.
- 유니버스: 업종 ✅이미라이브 / 시장 ✅라이브 / 전체 ✅라이브(cross-sector caveat) / **소속지수 ❌BLOCKED**(구성종목 멤버십 데이터 부재).

## 핵심 사실 (재조사 불필요)
- 백분위 산식 `pctRank`(engine.ts:88) + 전종목 raw `EcoNode`(types.ts:111-152, market 필드 포함) 이미 클라이언트. → `percentileIn(code, universe)` 모집단 필터만 분기(03).
- 셸·DistCurve·띠 마크업·다이얼로그 개폐 패턴(CenterStack:342,353) 전부 라이브.
- **완성형 = 한 빌드**: 시장/전체 분포곡선도 같은 모집단 배열에서 라이브 5분위로 산출 → prebuild 불필요(단계 분할 없음, 04 정정).

## NEXT
- 운영자 go → **완성형 착수**(engine.ts `percentileIn` 일반화 + `quantileBand` 라이브 5분위 + `PercentileCrossDialog.svelte`(3유니버스 백분위+곡선+정성 칩비중+가격격리) + RightStack 버튼 배선).
- UI 변경 → 자동 push 금지, 운영자 눈검수 + 명시 승인 후 push(feedback_ui_rules).

## 미해결 / 후속 (완성형 *밖*, 데이터 게이트)
- 소속지수: 구성종목 멤버십 데이터 소스 조사(별도 졸업게이트). KRX OpenAPI 미제공 확인됨 → 외부 소스 필요. 확보 전 link-only. *단계가 아니라 데이터 부재로 막힌 확장.*
