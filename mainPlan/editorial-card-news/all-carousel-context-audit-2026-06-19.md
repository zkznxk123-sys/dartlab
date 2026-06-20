# 전체 캐러셀 맥락 감사

작성일: 2026-06-19

## 결론

`sns/carousels` 아래 현재 포스트로 인식되는 캐러셀은 `hook.json` 기준 58개다. 이 문서는 2026-06-19 초기 감사 스냅샷이며, 이후 최근 3일 대상 35개는 `editorial_loop.json` 기반 게이트로 개선됐다. 최신 상태는 `recent-3day-carousel-repair-2026-06-19.md` 와 날짜별 직접 시각 QA 문서를 우선한다.

2026-06-20 추가: 최근 3일 대상 35개(`D01-D03`, `E01-E20`, `X01-X09`, `X15`)는 강화된 `checkCarouselEditorial.py` 기준 배치 게이트를 통과했고, `direct-visual-qa-2026-06-20.md`에 카드별 직접 확인 기록을 남겼다. 첫 장 훅 게이트와 `reel.json` 공개언어 게이트도 현재 검사에 포함된다.

| 상태 | 개수 | 의미 |
|---|---:|---|
| PASS | 2 | 2026-06-19 초기 감사 당시 통과 |
| FAIL | 56 | 2026-06-19 초기 감사 당시 발행 보류 |

현재 운영 판정:

| 범위 | 현재 상태 | 근거 |
|---|---|---|
| 최근 3일 대상 35개 | PASS | 배치 게이트 + 날짜별 직접 QA |
| 그 외 레거시 포스트 | 보류 | 현재 루프와 직접 QA가 아직 증명되지 않음 |

초기 감사 당시 통과:

- `X09-backtest-suspicion-checklist`
- `X15-macro-lens-evidence-dashboard`

## 감사 명령

전체 감사:

```bash
uv run python -X utf8 sns/scripts/auditCarouselEditorialBatch.py
```

개별 감사:

```bash
uv run python -X utf8 sns/scripts/checkCarouselEditorial.py X09-backtest-suspicion-checklist
uv run python -X utf8 sns/scripts/checkCarouselEditorial.py X15-macro-lens-evidence-dashboard
```

## 그룹별 결과

| 그룹 | 대상 | PASS | FAIL | 주요 실패 원인 |
|---|---:|---:|---:|---|
| `001-020` legacy | 20 | 0 | 20 | `story_brief.json`, `threads.txt`, `source_report.md`, `editorial_review.md` 누락 |
| `0/T*` tutorial legacy | 3 | 0 | 3 | 튜토리얼 맥락 패키지 누락 |
| `D*` legacy/product | 3 | 0 | 3 | D01은 필수 파일 누락, D02/D03은 메시지 스파인·리뷰 형식·전문어 미달 |
| `E*` editorial | 22 | 0 | 22 | 구형 E는 필수 파일 누락, 신형 E는 메시지 스파인·리뷰 grounding 미달 |
| `X*` expansion | 10 | 2 | 8 | X01-X08은 메시지 스파인·리뷰 grounding 미달 |

## 실패 유형

### 1. 발행 패키지 누락

대상:

- `001-020`
- `0/T01-dartlab-company`
- `0/T02-dartlab-company-live`
- `0/T03-dartlab-three-entries`
- `D01`
- 구형 `E01-E05`, `E07`, `E09` 카카오, `E10` LG엔솔, `E11-E18`

이 그룹은 카드와 캡션이 있어도 현재 기준으로 발행 가능성을 증명할 수 없다. `story_brief.json`, `threads.txt`, `source_report.md`, `editorial_review.md` 중 누락이 있다.

### 2. 메시지 스파인 누락

대상:

- `D02`, `D03`
- `E06`, `E08`, `E09` 에이피알, `E10` 크래프톤, `E19`, `E20`
- `X01-X08`

이 그룹은 필수 파일은 대체로 있으나 `oneLineMessage`, `readerContext`, `readerPayoff`, `narrativeSpine.setup/turn/proof/payoff` 가 비어 있다. 카드가 있어도 독자의 질문에서 결론까지 이어진다는 계약이 없다.

### 3. 리뷰 pass 무효

대상:

- D/E/X 대부분

기존 `editorial_review.md` 는 역할 이름과 pass 코멘트만 있었고, `oneLineMessage` 와 `whereToLook[]` 를 실제 근거로 검토하지 않았다. 그래서 "전문 에이전트가 OK했다"는 말은 현재 기준에서 통과 근거가 아니다. 지금부터는 `Verdict: pass`, `Message:`, `Checks:`, `Blocking issues: none` 형식과 grounding 둘 다 필요하다.

### 4. 독자 언어 미달

대상:

- `D03`
- 과거 수정 전 `X09`, `X15`

`OOS`, `B&H`, `Sharpe`, `OBS`, `PRIOR`, `TPL`, `LOCK` 같은 내부어는 공개 카드·캡션·스레드에서 독자 언어로 번역한다. 2026-06-20 기준 `X01`부터 `X09`, `X15`는 수정 완료.

## 운영 판정

- 초기 감사 당시 발행 가능: `X09`, `X15`
- 2026-06-20 직접 QA 및 강화 게이트 통과: `X01`부터 `X09`, `X15`
- 현재 발행 보류: 최근 3일 대상 35개를 제외한 레거시 포스트
- "사람이 보기에는 구조가 살아 있음"은 보조 의견이다. 발행 판정은 배치 감사 PASS로만 한다.
- 구형 레거시 포스트는 일괄 보수보다 우선순위 큐로 재기획한다. 전체를 억지로 PASS시키는 작업은 템플릿 양산 위험이 크다.

## 다음 보수 순서

1. 100개 챌린지 새 후보를 5인 평가로 선정한다.
2. 최근 3일 대상 중 새로 문구를 수정한 포스트는 단일 렌더와 전 카드 직접 QA를 갱신한다.
3. `001-020` legacy는 발행용이 아니라 참고 자료로 보존하거나, 새 포맷으로 재기획한다.

## 규칙

- 전체 발행 전에는 `auditCarouselEditorialBatch.py` 를 실행한다.
- 새 포스트는 개별 `checkCarouselEditorial.py <post>` PASS 이후에도 전체 배치 감사에서 의도치 않은 회귀가 없는지 본다.
- 과거 `passed-visual` 은 현재 PASS를 의미하지 않는다. 현재 PASS는 오늘의 게이트와 오늘의 렌더 검수로만 증명한다.
