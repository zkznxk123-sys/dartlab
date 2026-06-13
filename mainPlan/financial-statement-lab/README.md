# 재무제표 분석 심화 랩 (Financial Statement Lab) PRD Index

상태: 비전 PRD v0.1 (2026-06-13, 전문 에이전트 4 lens 조사·설계·적대검증 후 작성)
범위: 터미널 재무제표 분석 surface 업그레이드. 아이투자(iTooza) V차트 + 버틀러(Butler) 레퍼런스를 **그대로 복제하지 않고**, DartLab 고유 자산(panel cell-grid · `compare` N사 · reverseDCF · honesty spine)으로 흡수해 "한 단계 위"의 분석 능력을 만든다.

---

## 한 줄 결정

이 업그레이드의 성공 지표는 **차트 수가 아니다.** iTooza는 50차트를 가졌고 자기 메모에 "37개 전체 노출 = 덕지덕지"라고 적었다. 우리 터미널은 이미 5탭·~40카드로 그 철학(금액 막대 + 비율 선, 이중축 overlay)의 압축본을 가졌고, iTooza가 *없는* 카드(만기 사다리·감사보수 독립성·OCI bridge·자사주 흐름)까지 있다. 따라서 목표는 "더 많은 차트"가 아니라 **iTooza·Butler가 답하지 않는 *질문*을 답하는 것**이다:

> *iTooza·Butler는 한 회사의 역사를 그려주고 거기서 멈춘다. DartLab은 같은 차트 위에서 세 가지를 더 답한다 — 이 회사가 **동종 분포의 어디에 서 있는지**(절대값이 아니라 백분위), **현재가가 어떤 성장·마진·ROIC를 요구하는지**(역사적 멀티플이 아니라 가격이 함축한 기대), **이 숫자를 믿어도 되는지**(이익의 현금화·재무제표 정합·일회성). 그리고 모든 숫자는 추정이 아니라 원천 공시로 역추적되고, 결손은 0으로 채우지 않으며, 추천하지 않는다.*

핵심 명제: **iTooza는 차트를 보고도 Excel을 켜게 만들고, DartLab은 그 Excel 작업을 답으로 바꾼다.** 그리고 그 답을 위해 **기본 뷰는 더 작아진다**(업종 무관 카드 정리 = 덕지덕지 컷). 강함은 쌓아서가 아니라 깎아서.

---

## 핵심 결정 요약 (4 lens 토론 수렴 + 적대검증 후)

- **거처 = 기존 터미널 재무 surface 확장.** 새 엔진·새 패널·새 탭 더미 금지. `ui/packages/surfaces/src/terminal/`의 `finTabs.ts`(FS_TABS)·`MiniFinChart.svelte`·`financeSource.ts`를 EXTEND. 브라우저 계산이 가능한 건 브라우저에서, panel 주석·세그먼트·R&D 같은 Python 의존은 `tests/_attempts` 졸업 게이트 후 `src/dartlab` → prebuild parquet. 상세 = [03-architecture-and-reuse.md](03-architecture-and-reuse.md).
- **렌더러 = `MiniFinChart.svelte` EXTEND, `ChartRenderer`(landing/notebook 풀사이즈 디스패처) 도입 금지.** MiniFinChart는 이미 막대+선·이중축·signed·stacked·refLine·**heatmap·waterfall** 7형을 한 컴포넌트로 처리하고 카드 해석칩까지 붙어있다 — 터미널 small-multiples 밀도의 정본 렌더러. 지수 리베이스·백분위 밴드는 새 `kind`가 아니라 **데이터 변환 + spec 필드 추가**. "손수 차트 금지" 룰의 정신(렌더러 재발명 금지)을 MiniFinChart EXTEND가 정확히 지킨다.
- **차별의 핵 = panel cell-grid + `compare(codes,topic,period,scope)`.** 한 회사를 더 예쁘게 그리는 게 아니라 *전 회사·전 계정·전 시점이 수평화된 하나의 격자*에서 **동종 백분위**를 진짜 계산한다(iTooza는 회사별 사일로라 구조적으로 못 함). 그 위에 reverseDCF(가격 함축 기대)·이익품질 forensic이 싸게 얹힌다. 상세 = [02-differentiation-killer-features.md](02-differentiation-killer-features.md).
- **데이터 없으면 카드 없음.** 애널리스트 컨센서스(DART/EDGAR/gov 어디에도 없음)·수출 회사매핑(관세청=전국 집계, 회사 귀속 불가)은 **EXCLUDED**. 수주잔고(정량 표면 부재)는 **BLOCKED**. 세그먼트(panel 존재하나 XBRL 인코딩상 ~2/10만 clean)·PER/PBR 시계열(gov 주가 2020+·기간별 발행주식수 정합 필요)은 **CONDITIONAL**. 금융업(은행/보험/증권) 전용 카드는 계정 drift 비용·소수 audience로 **WON'T(본 PRD)**. 상세 = [04-data-readiness-kill-list.md](04-data-readiness-kill-list.md).
- **추천·단정·종합등급·목표주가 금지.** 해석칩은 *차트가 보여주는 것 + 점검 포인트*만 기술(좋다/나쁘다/개선 자동 판정 금지). reverseDCF는 "가격이 함축한 기대 읽기"지 "적정주가 X원"이 아니다(scenario-simulator의 honesty 패턴 차용·교차참조).
- **착수 = 운영자 go.** Phase 1(브라우저 전용, 신규 데이터 0)은 mainPlan UI 플랫폼 완료와 무관하게 선행 가능. Python 의존 Phase는 `tests/_attempts` 졸업 게이트 통과 후. 상세 = [05-scope-phasing-guardrails.md](05-scope-phasing-guardrails.md).

---

## 문서 지도

1. [00-product-prd.md](00-product-prd.md) — 판정, 제품 비전(투자자의 5 질문), 차별 명제, 제품 원칙, 핵심 화면, 범위·성공기준 요약.
2. [01-reference-teardown.md](01-reference-teardown.md) — iTooza 50차트 census 분해 + Butler 분해. 우리가 이미 가진 것 / 고가치 갭 / 덕지덕지. TAKE·REJECT·DEFER 취사선택.
3. [02-differentiation-killer-features.md](02-differentiation-killer-features.md) — ★차별의 핵. 투자자 실제 질문, iTooza/Butler 천장, killer 5종(동종 백분위·가격 함축 기대·이익품질·정합성·정직 TTM) 각 가치+데이터지원+가드레일.
4. [03-architecture-and-reuse.md](03-architecture-and-reuse.md) — 자산 인벤토리 판정(REUSE/EXTEND/NEW), 거처(browser TS·Python·contract), 렌더러 결정, 덕지덕지 함정, 계약 확장.
5. [04-data-readiness-kill-list.md](04-data-readiness-kill-list.md) — 데이터 가용성 매트릭스, EXCLUDED/BLOCKED/CONDITIONAL 킬리스트, PER/PBR 시계열 조인 정합 분석, honest-gap 규칙.
6. [05-scope-phasing-guardrails.md](05-scope-phasing-guardrails.md) — MUST/SHOULD/WON'T 단두대, 데이터 준비도순 Phase, honesty 가드레일, 성공지표·실패모드·단일 최대 리스크.
7. [06-progress-ledger.md](06-progress-ledger.md) — 현재 결정·토론 출처·문서 상태·NEXT·메모리 포인터.

---

## 정직 척추 (전 문서 관통)

1. **클론 아님.** 차트 수가 성공지표면 이미 실패. 기본 뷰는 더 작게, 카드마다 *별개의 근거 있는 질문*. parity-as-spec(경쟁사 스크린샷 매칭) 금지.
2. **차별 = 더 많은 차트가 아니라 못 풀던 질문.** 동종 백분위 / 가격 함축 기대 / 이익 품질 / 정합성 — 전부 ref-추적.
3. **데이터 없으면 카드 없음.** 컨센서스·수주잔고·수출 회사매핑·세그먼트 8/10 = 차단. "나중에 Phase N"으로 흐리지 말고 BLOCKED/EXCLUDED로 박는다.
4. **결손은 0 대체 금지.** missing/blocked/partial/notApplicable 라벨. 빈 카드는 자동 제거(`alive` 패턴), 부분 카드는 honest-gap 상태.
5. **추천·단정 금지.** 종합점수·등급·매수매도 신호·목표주가 0. 모든 숫자 → sourceRef + as-of.
6. **본진 0줄(검증 전).** Python 의존 능력은 `tests/_attempts/financialStatementLab/`에서 졸업 게이트(개념확립→모듈화→데모→덕지덕지제거→클린코드→docstring) 후에만 `src/dartlab`. 브라우저 계산은 기존 `financeSource.ts`/`MiniFinChart.svelte` EXTEND.
