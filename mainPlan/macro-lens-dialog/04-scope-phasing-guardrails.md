# 04. 범위 · Phase · 가드레일

상태: 설계 v0.1
범위: 구현 단계와 정직 가드.

---

## 1. Phase

| Phase | 내용 | 의존 | 수용 기준 |
|---|---|---|---|
| 0 | 문서 확정 | 본 폴더 | 운영자 go 전까지 코드 0 |
| 1 | UI-only Macro Lens 다이얼로그 | 기존 terminal raw data | 다섯 탭, 출처 탭, 진입점 최소 2개 |
| 2 | 지표 행 ↔ 차트 ECON 연동 | `ChartCtl.toggleEcon`, `MACRO_SERIES` | 다이얼로그 row에서 오버레이 토글, ECON_MAX 준수 |
| 3 | 섹터/종목 영향 view-model | `co.tailwind`, `eng.sectorTailwinds`, company finance shape | Driver Chain Map과 Company Checkpoints 표시 |
| 4 | co-movement 반증 블록 | 기존 `rankCoMovers` | corr/n/인과 아님 라벨 표시 |
| 5 | 심층 민감도 연결 검토 | 공개 analysis surface 필요 | nObs/R²/표본기간 없이는 미출시 |
| 6 | 시장 단위 `macroLens` artifact 검토 | sync/prebuild 경계 | per-company 산출물 없이 public/local 공통 배선 |

Phase 1~4가 첫 제품 단위다. Phase 5~6은 다이얼로그 사용 후 필요성이 확인될 때만 진행한다.

---

## 2. MUST

- 기존 좌측 `마켓 펄스`, KPI ticker, 차트 ECON을 입구로 사용한다.
- 다이얼로그는 5탭 이하로 제한한다.
- 지표값에는 기준일과 출처를 붙인다.
- 선택 종목 기준 섹터 tailwind와 company checkpoint를 연결한다.
- co-movement에는 `상관은 인과가 아님`을 표시한다.
- 결손은 `missing/partial/notApplicable/notWiredYet`로 남긴다.
- public/local 공통배선을 지킨다.

---

## 3. SHOULD

- `MacroLensSnapshot` view-model을 별도 `lib/macroLens.ts`로 분리한다.
- 다이얼로그 행에서 `차트에 겹치기` 액션을 제공한다.
- `Driver Chain Map`은 고정 경로 템플릿으로 시작한다.
- 섹터별 민감 경로는 `sectorPriors.json` 또는 기존 `calcMacroSensitivity`의 공개 산출물과 정합시킨다.
- 지표 그룹 표는 검색/필터보다 그룹 접기 우선으로 설계한다.
- 회귀 기반 deep block은 품질 라벨이 준비될 때만 공개한다.

---

## 4. WON'T

- 새 L2 macro 엔진 신설.
- 새 상주 패널, 새 route, 새 chart instance.
- 회사별 매크로 점수 precompute.
- 목표주가, 매수/매도, 저평가 확정.
- "위기 임박", "수혜 확정", "실시간 경보" 문구.
- 컨센서스/애널리스트 전망 결합.
- public에서 로컬 전용 기능을 조용히 숨기는 것.
- 결손 0 대체.

---

## 5. 경계

| 기능 | 소유 |
|---|---|
| 매크로 국면·지표·시나리오 카탈로그 | `engines.macro` |
| 회사 재무제표 심층 판단·reverseDCF | `financial-statement-lab` |
| 미래 what-if·Play replay | `scenario-simulator` |
| 공시 워치·커맨드바 | `terminal-improvement` |
| 데이터 포트·공통배선 | `data-workbench-ssot` as-built + `operation.ui` |

Macro Lens는 이들을 재발명하지 않고 입구와 연결 설명을 제공한다.

---

## 6. 정직 문구

다이얼로그 어디엔가 항상 노출할 문구:

```text
매크로 렌즈는 배치 데이터 기반의 전파 경로 분석입니다. 상관은 인과가 아니며, 지표 변화가 회사 실적 변화를 보장하지 않습니다.
```

시나리오 탭 문구:

```text
시나리오는 명시 가정입니다. 예측이나 투자 추천이 아니며, 회사 손익 정량화는 별도 시뮬레이터의 영역입니다.
```

