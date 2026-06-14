# 05 — 진행 원장

상태: **v0.1 PRD 확정 (2026-06-14)** · 착수 = 운영자 go 대기

## 결정 로그
- 2026-06-14: PRD v0.1 작성. 4-ground 코드 실측 + 4렌즈 토론(정보설계·실현가능성·정직가드·PM) + 적대검증.
- 2026-06-14 **운영자 레인 분리 확정**: scan-grade-explainer = 종합평가(큰그림·판정)로 독립 개선. 본 화면 = 유니버스 교차 *분포 사실*(판정 0). → 흡수 거부, **별도 카테고리 + 공유 SSOT** 확정.
- 메커니즘: 히트맵 reject → 축별 행 × 유니버스 열 띠 + DistCurve 드릴다운.
- 유니버스: 업종 ✅이미라이브 / 시장 ✅라이브 / 전체 ✅라이브(cross-sector caveat) / **소속지수 ❌BLOCKED**(구성종목 멤버십 데이터 부재).

## 핵심 사실 (재조사 불필요)
- 백분위 산식 `pctRank`(engine.ts:88) + 전종목 raw `EcoNode`(types.ts:111-152, market 필드 포함) 이미 클라이언트. → `percentileIn(code, universe)` 모집단 필터만 분기(03).
- 셸·DistCurve·띠 마크업·다이얼로그 개폐 패턴(CenterStack:342,353) 전부 라이브.
- 시장/전체 분포곡선 band 는 Phase 2 prebuild(`_distribution`) 전까지 막대만.

## NEXT
- 운영자 go → Phase 1 착수(engine.ts `percentileIn` 일반화 + `PercentileCrossDialog.svelte` + RightStack 버튼 배선).
- UI 변경 → 자동 push 금지, 운영자 눈검수 + 명시 승인 후 push(feedback_ui_rules).

## 미해결 / 후속
- Phase 3 소속지수: 구성종목 멤버십 데이터 소스 조사(별도 졸업게이트). KRX OpenAPI 미제공 확인됨 → 외부 소스 필요.
- Phase 2 시장/전체 band prebuild 위치(빌드 산출물에 marketStats/allStats 추가) 설계.
