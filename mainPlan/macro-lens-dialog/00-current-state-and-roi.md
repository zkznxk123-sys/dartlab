# 00. 현상태 · ROI · 토론 결론

상태: 조사 메모 v0.2
범위: 이미 있는 매크로/터미널 자산과 이번 다이얼로그의 투자 대비 효과를 정리한다.

---

## 1. 판정

요청은 명확하고 타당하다. 기존 v0.1 기획은 UI 연결을 우선한 점은 맞지만, 분석의 핵이 되기에는 약하다. v0.2의 판정은 다음이다.

**Macro Lens는 다이얼로그가 아니라 매크로 전파 분석 코어다.** 다이얼로그는 그 코어를 터미널에서 조작하는 표면이고, 엔진은 `macro.transmission`(시장·섹터 전파)과 `analysis.macroExposure`(회사 노출·품질)로 나눠 강화한다.

현재 DartLab은 매크로 자산을 많이 갖고 있다.

- `src/dartlab/macro/__init__.py` — 6막 매크로 축: `cycle`, `inventory`, `corporate`, `trade`, `rates`, `liquidity`, `crisis`, `assets`, `sentiment`, `narrative`, `forecast`, `scenario`, `summary`.
- `src/dartlab/macro/summary.py` — 11개 축을 순차 호출해 종합 점수, 이유, 자산배분, 전략 대시보드를 만든다.
- `src/dartlab/analysis/financial/_signalsMacroSensitivity.py` — 섹터별 매크로 탄성치와 기업별 매크로 회귀(`calcMacroSensitivity`, `calcMacroRegression`)가 이미 있다.
- `ui/packages/contracts/src/macro.ts` — `MACRO_SERIES`가 ECOS/FRED 기반 경제지표 카탈로그를 정의한다.
- `ui/packages/runtime/src/adapters/public/sources/macroSource.ts` — 퍼블릭/로컬 공통 `MacroPort`가 HF parquet를 브라우저에서 직접 읽는다.
- `ui/packages/surfaces/src/terminal` — 좌측 `마켓 펄스`, 상단 KPI 티커, 차트 `ECON` 오버레이, 종목-거시 동행상관 정렬이 이미 구현되어 있다.

빈틈은 세 가지다.

1. **연결 부재.** 사용자는 지표·국면·차트 오버레이를 각각 볼 수 있지만, "이 종목에 왜 중요한가"를 한 흐름으로 보지 못한다.
2. **전파 산출물 부재.** 매크로 엔진은 국면·시나리오·요약은 강하지만, `driver → sector → financial line`을 기계가 읽을 수 있는 edge로 고정하지 않는다.
3. **품질 라벨 부재.** 회사별 회귀/민감도는 있지만, public terminal에 바로 띄우기에는 표본 수, R², lag, coverage, 기준기간 라벨이 부족하다.

---

## 2. ROI

### 높은 이유

1. **기존 자산 재사용률이 높다.** 새 수집 경로나 새 차트 엔진 없이 `macro.json`, `MacroPort`, `co.tailwind`, 차트 co-movement로 첫 화면을 만들 수 있다.
2. **터미널의 정체성을 바꾼다.** 현재는 종목·재무·차트 중심이다. Macro Lens가 붙으면 경제 → 섹터 → 종목 → 재무 → 가치 흐름이 닫힌다.
3. **좌측상단 영역의 의미가 강해진다.** `마켓 펄스`가 단순 국면 요약에서 종목별 외부환경 분석 입구가 된다.
4. **다이얼로그 방식이 anti-clutter에 맞다.** 상주 패널을 늘리지 않고 기존 입구를 유지한다.
5. **scenario-simulator·financial-statement-lab과 자연스럽게 이어진다.** 단, 이 문서는 그 기능을 침범하지 않고 심층 분석 입구만 정의한다.

### 낮아질 수 있는 이유

1. 회사별 매크로 회귀는 표본 부족과 계절성에 취약하다.
2. 업종별 민감도는 섹터 prior라 기업별 고유 노출을 단정할 수 없다.
3. 매크로 판단은 기준일과 갱신주기에 민감하다.
4. 상관은 인과가 아니다. 차트 co-movement를 "영향"으로 보이게 하면 제품 신뢰가 깨진다.

따라서 첫 제품 단위의 목표는 **예측·판정이 아니라 전파 경로, 품질 라벨, 반증 조건을 보여주는 것**이다. 강한 기능은 점수 하나를 만드는 것이 아니라 사용자가 한 매크로 driver를 손익·현금흐름·밸류에이션까지 추적하고, 동시에 "이 연결은 약하다"는 근거까지 볼 수 있게 하는 것이다.

---

## 3. 전문 관점 토론 결론

### 금융/매크로 분석 렌즈

- 핵심 질문은 `Regime → Sector Fit`: 현재 KR/US 국면이 선택 업종의 매출 driver와 같은 방향인지, 충돌하는지다.
- 강한 블록은 `Driver Chain Map`: 금리·환율·유동성·교역 중 어떤 축이 `sector → company → P&L → valuation`으로 전파될 수 있는지 보여준다.
- `calcMacroSensitivity`와 `calcMacroRegression`은 반드시 신뢰도 검사를 동반해야 한다. R², 관측치 수, lag, 기준 기간 없는 beta는 단정 금지다.
- 차트 co-movement는 thesis의 반증 도구이지 인과 증명이 아니다.
- 좋은 다이얼로그는 매출 노출, 마진 pass-through, 재무제표 압박, 현금흐름 흡수력, 밸류에이션 전파까지 이어져야 한다.

### 터미널 UX/PM 렌즈

- Macro Lens는 상주 패널이 아니라 다이얼로그다. 좌측 마켓 펄스, KPI 티커, 차트 ECON 오버레이가 이미 입구다.
- 정보 구조는 `국면`, `지표·Driver`, `전파 지도`, `시나리오`, `출처·한계` 5탭 이하가 상한이다.
- 좌측 마켓 펄스 클릭은 국면 탭, KPI 지표 클릭은 지표·Driver 탭, 순풍/역풍 섹터 칩 클릭은 전파 지도 탭으로 들어간다.
- 차트에는 원시 시계열 오버레이만 남긴다. 다이얼로그가 차트를 복제하지 않는다.
- 성공 기준은 30초 안에 "지금 국면은?", "어떤 지표가 그 판단을 만들었나?", "이 종목에는 어떤 경로로 중요할 수 있나?"를 답하는 것이다.

### 아키텍처/데이터 계약 렌즈

- 첫 화면 구현은 터미널 UI view-model로 시작한다.
- 분석 코어 강화는 새 독립 L2 엔진 신설이 아니라 기존 `macro` 엔진의 시장·섹터 전파 축 확장으로 한다.
- `macro.transmission`은 회사 객체를 모르면 된다. driver, source series, sector prior, financial line, lag, sign, confidence, evidence level만 낸다.
- 회사별 결합은 `analysis.macroExposure` 공개 surface가 맡는다. `macro`가 `analysis`를 import하지 않고, UI나 L2.5 조합기가 공개 산출물만 합친다.
- 재사용 산출물은 `dashboards/macro.json`, `macro/{fred,ecos}/observations.parquet`, `MACRO_SERIES`, `co.tailwind`, `eng.sectorTailwinds()`다.
- 새 산출물이 필요하면 per-company artifact가 아니라 시장 단위 HF artifact만 허용한다.
- public/local 공통배선이 불변이다. 로컬 `:8400` 없이 떠야 정상이다.
- UI 데이터 호출은 `ui/packages/runtime/src/data/fetch`와 `data/origins` 경유여야 한다. raw fetch·직접 URL·source 자체 캐시 신설은 금지다.
- L2 경계상 `macro`가 `analysis` 내부를 끌어오거나 반대로 다른 L2가 `macro` 내부 구현을 import하면 안 된다. 결합은 UI view-model, story/recipe, 또는 별도 L2.5에서만 한다.

---

## 4. 정체성

Macro Lens는 경제지표 모음이 아니다.

```text
지표 목록        X
국면 스코어      X
종목 추천        X

전파 사슬        O
민감도 품질      O
반증 조건        O
엔진 lineage      O
출처·기준일      O
```

다이얼로그의 이름은 `매크로 렌즈`, 카드 제목은 `이 종목의 경제 민감도`가 적합하다.
