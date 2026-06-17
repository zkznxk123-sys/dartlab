# Macro Lens Engine Attempt

목표: 퍼블릭 터미널의 Macro Lens를 단순 지표 나열이 아니라 `driver -> transmission -> company evidence -> falsifier`로 설명하는 분석 엔진으로 승격하기 전, 계약과 실패 조건을 먼저 고정한다.

## 현재 본진 반영 범위

- 터미널 UI는 `ui/packages/surfaces/src/terminal/lib/macroLens.ts`에서 정성 스냅샷을 만든다.
- 회사별 민감도 beta, 회귀 계수, 목표주가성 결론은 아직 본진에 넣지 않는다.
- 수치 엔진 승격 전까지는 회사 고유 노출이 표준화되지 않은 항목을 `qualitativeOnly`로 표시한다.

## 이번 proof가 닫는 범위

- `macroLensEngine.py`는 외부 API 없이 driver registry, transmission edge, lagged co-movement, exposure quality, scenario readiness를 하나의 스냅샷으로 조립한다.
- `test_macroLensEngine.py`는 최소 driver/sector coverage, lag/R² 후보, partial company evidence, look-ahead, stale driver, snapshot shape를 검증한다.
- `validateSamples.py`는 JSON 필드 검증을 넘어 실제 attempt snapshot 생성까지 확인한다.

## 승격 계약

본진 `src/dartlab`로 올릴 수 있는 최소 조건:

1. Driver registry가 source, 단위, 변환 방식, stale 기준, release lag를 가진다.
2. Transmission edge가 macro driver, sector, financial line, valuation lever, sign, lag, required company evidence를 가진다.
3. Exposure quality가 `nObs`, `rSquared`, `window`, `lag`, `coverage`, `missingEvidence`를 공개한다.
4. Falsifier가 과적합, 동행상관 부족, stale data, 회사 증거 누락을 UI에 그대로 전달한다.
5. Look-ahead 방지를 위해 모든 계산은 `asOf <= priceAsOf` 기준을 통과해야 한다.

## 산출물

- `driverRegistry.sample.json`: driver 의미/신선도/변환 계약.
- `transmissionEdges.sample.json`: 업종-재무제표 전파 경로 계약.
- `exposureQuality.sample.json`: 회사별 민감도 승격 게이트 예시.
- `failureCases.md`: 본진 승격 전에 반드시 깨지지 않아야 하는 실패 케이스.
- `macroLensEngine.py`: 순수 표준 라이브러리 기반 proof engine.
- `test_macroLensEngine.py`: proof engine targeted tests.
- `validateSamples.py`: 샘플 계약 필수 필드 검증.

## 실행

```powershell
python -X utf8 tests/_attempts/macroLensEngine/validateSamples.py
python -X utf8 -m pytest tests/_attempts/macroLensEngine/test_macroLensEngine.py -q
python -X utf8 tests/_attempts/macroLensEngine/macroLensEngine.py
```

## 현재 판정

Phase 4 proof는 `src/dartlab` 승격 전 계약 검증 단계까지 강화됐다. 다음 승격은 별도 변경으로 `macro.transmission` 축을 만들고, 이 proof의 `drivers/edges/sourceRefs`를 그대로 production API 반환으로 옮긴 뒤 architecture guard를 통과해야 한다.
