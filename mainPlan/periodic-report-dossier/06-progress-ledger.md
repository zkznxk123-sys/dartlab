# 06 — 진행 원장

## 상태

- **2026-06-19**: PRD v0.1 작성 완료. 13인 전문가 토론(`wf_c20526bc-bed`, 도메인 5 + 적대검증 5 + UI/UX 2 + 종합 리드) + 이번 세션 실측 인벤토리 기반. 착수 대기(운영자 go).
- 구현 코드 **0**. 전부 설계 단계.

## NEXT (재개 포인터)

> 운영자 go 시 Phase 0 부터. 재조사 불요 — 본 문서들이 자기충족 설계.

1. **Phase 0 (스파인, 단독 ship 가능)**: `companyLive.ts` 6 SELECT 에 `rcept_no`+`stlm_dt` 추가 → `LiveCompanyReportFact` contract → 도시에 헤더 리본 → 평면 팩트 패널 흡수. svelte-check 0 + 헤더 회귀 가드 + 공개/로컬 동일.
2. **Phase 1 (zero-fetch 리프레임)**: 환원흐름 문장+RETURN 막대 / lossPct+control-shift / 인력 자기이력+`상세보기` / CARD_GUIDE 리프레임. NEVER-CLAIM grep + 3-케이스 소형주 데모 → 운영자 push 승인.
3. **Phase 2 (엔진 bake)**: 인적자본 분위 배열 + rndIntensity CI parquet. slip 허용.
4. **Phase 3 (선택)**: 가동률 원문 발췌(zero 추출 한정).

## 열린 결정 (착수 전 확인 가능)

1. **R&D 스파크라인 vs 텍스트 추세**: 적대검증 합의=텍스트(↑/↓/→ + 전년 Δ), 레일 그래프 금지. 인라인 스파크라인 primitive 도입 안 함 확인.
2. **R&D 소스 태그 의미**: IS라인(정규화 비용) vs SG&A주석(총지출, 자본화 포함) = 다른 개념 → UI 가 회사별 소스 표시(절대 혼합 금지).
3. **Phase 2 slip 시**: Phase 1 단독 ship(R&D 행·백분위 축 부재로 우아하게 degrade, 깨진 빈 행 아님) 확인.
4. **`controlShiftSummary` 기간 선택**: earliest-vs-latest(큰 지배 이야기) vs latest-two(최신). 명시 YYYYqQ→YYYYqQ 라벨 어느 쪽이든.
5. **pctOfParentCap self-gate 임계**: 'material' listed 커버리지 기준(listed ≥1 AND listedStakeSum ≥ bookTotal 의 일정 비율)? 독립 소형주에 오해소지 작은 % 대신 자기 suppress 하도록 구체 cutoff.
6. **가동률 원문 블록(P3)**: 뷰어가 이미 rawMaterial 섹션 텍스트 렌더하는지(=anchor+label ship) vs 새 추출 필요(=컷) — feasibility 체크.

## 메모리 포인터

`MEMORY.md` §6.2 에 `[[project_terminal_periodic_report_dossier]]` 등록(포인터만, SSOT=본 폴더).
