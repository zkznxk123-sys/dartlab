# Macro Lens Engine Attempt

목표: 퍼블릭 터미널의 Macro Lens를 단순 지표 나열이 아니라 `driver -> transmission -> company evidence -> falsifier`로 설명하는 분석 엔진으로 승격하기 전, 계약과 실패 조건을 먼저 고정한다.

## 현재 본진 반영 범위

- 터미널 UI는 `ui/packages/surfaces/src/terminal/lib/macroLens.ts`에서 정성 스냅샷을 만든다.
- 회사별 민감도 beta, 회귀 계수, 목표주가성 결론은 아직 본진에 넣지 않는다.
- 수치 엔진 승격 전까지는 회사 고유 노출이 표준화되지 않은 항목을 `qualitativeOnly`로 표시한다.

## 승격 계약

본진 `src/dartlab`로 올릴 수 있는 최소 조건:

1. Driver registry가 source, 단위, 변환 방식, stale 기준, release lag를 가진다.
2. Transmission edge가 macro driver, sector, financial line, valuation lever, sign, lag, required company evidence를 가진다.
3. Exposure quality가 `nObs`, `r2`, `window`, `lag`, `coverage`, `missingEvidence`를 공개한다.
4. Falsifier가 과적합, 동행상관 부족, stale data, 회사 증거 누락을 UI에 그대로 전달한다.
5. Look-ahead 방지를 위해 모든 계산은 `asOf <= priceAsOf` 기준을 통과해야 한다.

## 산출물

- `driverRegistry.sample.json`: driver 의미/신선도/변환 계약.
- `transmissionEdges.sample.json`: 업종-재무제표 전파 경로 계약.
- `exposureQuality.sample.json`: 회사별 민감도 승격 게이트 예시.
- `failureCases.md`: 본진 승격 전에 반드시 깨지지 않아야 하는 실패 케이스.
- `validateSamples.py`: 샘플 계약 필수 필드 검증.

## 실행

```powershell
python -X utf8 tests/_attempts/macroLensEngine/validateSamples.py
```
