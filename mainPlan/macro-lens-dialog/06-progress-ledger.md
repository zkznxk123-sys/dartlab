# 06. 진행 원장

상태: v0.2

---

## 2026-06-17

### v0.2 — 엔진 강화 반영

배경:

- 운영자가 "분석에 핵이 될 수 있게, 필요하면 매크로 엔진도 개선"을 요청했다.
- v0.1은 다이얼로그와 재사용 자산 중심이라 첫 화면 구현에는 안전하지만, 분석 코어로는 약했다.

추가 결정:

- Macro Lens는 UI 기능이 아니라 `Macro Driver → Transmission Edge → Company Exposure → Financial Checkpoint → Valuation Lever → Falsifier` 사슬이다.
- `macro` 개선은 허용한다. 단, 새 독립 L2 엔진이 아니라 기존 macro의 시장·섹터 전파 축(`macro.transmission`) 후보로 둔다.
- `macro.transmission`은 회사/analysis 내부를 import하지 않는다.
- 회사별 민감도와 회귀 품질은 `analysis.macroExposure` 공개 surface 후보로 둔다.
- 엔진 강화는 `tests/_attempts/macroLensEngine/` proof를 먼저 만든 뒤 src 승격을 결정한다.
- canonical id는 `MACRO_SERIES.id`를 기준으로 한다. 레거시 id는 alias registry 없이는 edge에 쓰지 않는다.

NEXT:

1. 구현 go가 있으면 Phase 1~3 다이얼로그 제품 단위를 먼저 만든다.
2. 엔진 go가 있으면 `tests/_attempts/macroLensEngine/`에 driver registry/edge/quality 샘플과 실패 케이스를 만든다.
3. attempts proof 후 `macro.transmission`과 `analysis.macroExposure` 승격 범위를 결정한다.

착수 상태:

- 코드 작업 전.
- 문서만 v0.2로 보강.

---

### v0.1 — 최초 기획

결정:

- `경제지표분석` 강화는 `Macro Lens` 다이얼로그로 기획한다.
- 당시에는 새 L2 엔진이 아니라 기존 `dartlab.macro`, `MacroPort`, `macro.json`, `sectorTailwind`, 차트 co-movement를 묶는 UI 제품으로 시작한다고 정했다.
- 강한 분석의 중심은 `Macro → Sector → Company → Financial → Valuation` 전파 사슬이다.
- 상주 패널 추가는 금지한다. 기존 좌측 마켓 펄스, KPI ticker, 차트 ECON을 진입점으로 재사용한다.
- 첫 구현은 5탭 이하: `국면`, `지표·Driver`, `전파 지도`, `시나리오`, `출처·한계`.
- 회사별 회귀/민감도 심층화는 품질 라벨 계약 전까지 Phase 5로 둔다.

전문 관점 토론:

- 금융/매크로 렌즈: 전파 경로, 민감도 품질, co-movement 반증, 현금흐름 흡수력, 밸류에이션 전파가 핵심.
- 터미널 UX/PM 렌즈: 한 다이얼로그 5탭, 기존 진입점 재사용, 차트 복제 금지, 30초 4문장 성공 기준.
- 아키텍처/데이터 렌즈: public/local 공통배선, UI view-model first, 새 artifact는 시장 단위만, L2 내부 import 금지.

NEXT:

1. 운영자 go가 있으면 구현 전 현재 `ui/packages/surfaces/src/terminal`와 runtime audit 명령을 재확인한다.
2. Phase 1 다이얼로그 shell부터 구현한다.
3. 구현 후 public/local visual QA와 data wiring audit를 통과시킨다.

착수 상태:

- 코드 작업 전.
- 문서만 작성.
