# 최근 3일 캐러셀 맥락 개선 기록

날짜: 2026-06-19
범위: `hook.json` 수정 시간이 2026-06-16 이후인 `D*`, `E*`, `X*` 캐러셀

## 결론

최근 3일 대상 35개는 새 에디토리얼 루프 게이트를 통과했다. 이번 통과는 카드 원본 JSON, 브리프, 캡션, 스레드, 리뷰, 루프 산출물이 같은 질문과 같은 관전 포인트로 닫힌다는 뜻이다.

2026-06-20 기준 강화 사항까지 반영했다. 첫 장 훅은 `audienceQuestion`, `coreAnswer`, `tension`, `soWhat` 중 최소 두 축을 담아야 하고, 릴스가 있으면 `reel.json`도 공개언어·강조·브랜드 아바타 규칙을 통과해야 한다. 렌더 산출물은 `direct-visual-qa-2026-06-20.md`에서 포스트별 전 카드 직접 확인 기록으로만 인정한다.

## 적용한 파이프라인 개선

- `editorial_loop.json` 필수화
- 기획 3인, 작가 3인, 평가 5인, 피드백, 재평가 5인 계약 추가
- `checkCarouselEditorial.py`가 루프 산출물을 실제 검사
- `auditCarouselEditorialBatch.py`에 `--since`, `--recent-days`, `loop` 컬럼 추가
- `repairRecentCarouselEditorial.py`로 최근 3일 대상의 캡션·스레드·리뷰·루프를 같은 관전 포인트로 정렬
- 깨진 한글과 mojibake 감지 게이트 추가
- `E03`, `E18`의 깨진 한글 훅과 브리프를 수동 복구
- `renderRecentCarousels.py` 추가
- Remotion props 임시 파일을 repo 내부 `.tmp/remotion-props`로 이동
- 첫 장 훅 게이트 추가: 요약형 커버를 막고, 독자의 실제 질문을 첫 화면에 싣는다.
- `reel.json` 공개언어·강조·브랜드 아바타 게이트 추가
- 직접 시각 QA 기준 강화: 1장/숫자 장/마지막 장 샘플 확인이 아니라 모든 PNG를 한 장씩 연다.

## 검증 결과

명령:

```bash
python -X utf8 -m py_compile sns/scripts/checkCarouselEditorial.py sns/scripts/auditCarouselEditorialBatch.py sns/scripts/repairRecentCarouselEditorial.py sns/scripts/renderRecentCarousels.py
python -X utf8 sns/scripts/auditCarouselEditorialBatch.py --since 2026-06-16 --prefix D --prefix E --prefix X
python -X utf8 sns/scripts/checkCarouselEditorial.py E03-000660-sk-hynix-ai-memory-editorial
python -X utf8 sns/scripts/checkCarouselEditorial.py E18-271560-orion-localization-margin
```

결과:

- py_compile: PASS
- 최근 3일 배치 감사: 35개 PASS
- `E03-000660-sk-hynix-ai-memory-editorial`: PASS
- `E18-271560-orion-localization-margin`: PASS
- 직접 시각 QA: `direct-visual-qa-2026-06-20.md` 기준 35개 포스트 전 카드 확인 완료

## 최근 3일 통과 대상

- `D01-dartlab-search-sidecar-evidence-os`
- `D02-dartlab-table-export-evidence-os`
- `D03-dartlab-backtest-honesty-os`
- `E01-000660-skhynix-editorial`
- `E02-035420-naver-ai-factory-editorial`
- `E03-000660-sk-hynix-ai-memory-editorial`
- `E04-336260-doosan-fuel-cell-company-map`
- `E05-010120-ls-electric-power-grid-editorial`
- `E06-003230-samyang-buldak-export-engine`
- `E07-CPNG-coupang-breach-cost-loop`
- `E08-207940-samsung-biologics-cdmo-factory`
- `E09-035720-kakao-chatgpt-in-talk`
- `E09-278470-apr-beauty-device-dtc-engine`
- `E10-259960-krafton-pubg-cash-engine`
- `E10-373220-lg-energy-solution-ess-backlog`
- `E11-267260-hd-hyundai-electric-transformer-backlog`
- `E12-ORCL-oracle-rpo-cash-gap`
- `E13-005930-samsung-memory-profit-engine`
- `E14-257720-silicon2-kbeauty-tollgate`
- `E15-064350-hyundai-rotem-defense-profit`
- `E16-352820-hybe-stage-outside-numbers`
- `E17-012450-hanwha-aerospace-backlog-to-margin`
- `E18-271560-orion-localization-margin`
- `E19-042700-hanmi-tc-bonder-hbm4`
- `E20-009540-hd-ksoe-orders-to-margin`
- `X01-disclosure-treasury-cancel`
- `X02-profit-cashflow-conversion`
- `X03-policy-market-rates`
- `X04-dartlab-compare-grid`
- `X05-usd-krw-fx-margin`
- `X06-ai-power-demand-grid-bottleneck`
- `X07-disclosure-supply-contract-profit-gap`
- `X08-capex-depreciation-cash-timing`
- `X09-backtest-suspicion-checklist`
- `X15-macro-lens-evidence-dashboard`

## 다음 작업

1. 새로 수정한 포스트는 단일 포스트 렌더 후 모든 카드를 직접 연다.
2. 100개 챌린지는 매 사이클 첫 장 훅을 5인 평가의 첫 질문으로 둔다.
3. 다음 후보 제작 전에는 최근 3일 배치 게이트와 직접 QA 기록이 모두 녹색이어야 한다.
