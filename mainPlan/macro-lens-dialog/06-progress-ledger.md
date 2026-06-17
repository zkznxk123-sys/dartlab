# 06. 진행 원장

상태: v0.1

---

## 2026-06-17

결정:

- `경제지표분석` 강화는 `Macro Lens` 다이얼로그로 기획한다.
- 새 L2 엔진이 아니라 기존 `dartlab.macro`, `MacroPort`, `macro.json`, `sectorTailwind`, 차트 co-movement를 묶는 UI 제품으로 시작한다.
- 강한 분석의 중심은 `Macro → Sector → Company → Financial → Valuation` 전파 사슬이다.
- 상주 패널 추가는 금지한다. 기존 좌측 마켓 펄스, KPI ticker, 차트 ECON을 진입점으로 재사용한다.
- 첫 구현은 5탭 이하: `국면`, `지표`, `섹터/종목 영향`, `시나리오`, `출처·한계`.
- 회사별 회귀/민감도 심층화는 품질 라벨 계약 전까지 Phase 5로 둔다.

전문 관점 토론:

- 금융/매크로 렌즈: 전파 경로, 민감도 품질, co-movement 반증, 현금흐름 흡수력, 밸류에이션 전파가 핵심.
- 터미널 UX/PM 렌즈: 한 다이얼로그 5탭, 기존 진입점 재사용, 차트 복제 금지, 30초 3질문 성공 기준.
- 아키텍처/데이터 렌즈: public/local 공통배선, UI view-model first, 새 artifact는 시장 단위만, L2 내부 import 금지.

NEXT:

1. 운영자 go가 있으면 구현 전 현재 `ui/packages/surfaces/src/terminal`와 runtime audit 명령을 재확인한다.
2. Phase 1 UI-only 다이얼로그부터 구현한다.
3. 구현 후 public/local visual QA와 data wiring audit를 통과시킨다.

착수 상태:

- 코드 작업 전.
- 문서만 작성.

