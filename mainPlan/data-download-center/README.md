# 데이터 다운로드 센터 — PRD 인덱스

> 상태: v0.1 (2026-06-28 작성, 전문 패널 3 설계 + 적대 교차검증 3 + 수석 종합 후 확정).
> 끊긴 세션은 [06-progress-ledger](06-progress-ledger.md) §NEXT 만 읽고 재개. 본 README = 인덱스 + 정신모델.

## 한 줄 정신모델

**HF parquet 경로를 거울로 비추고 확장자만 바꾼다.**

```
…/resolve/main/{dir}/{id}.parquet   →   https://{DATA_WORKER_HOST}/v1/{dir}/{id}.{ext}
```

워커가 아는 유일한 데이터 지식 = `DATA_RELEASES`(`src/dartlab/core/dataConfig.py`)에서 빌드타임에 emit 한 **노출 화이트리스트 1개**. 데이터셋별 하드코딩 0 — 새 회사·새 카테고리 parquet 가 SSOT 한 줄로 양 티어에 자동 노출된다. **CSV 사본은 어디에도 굽지 않는다**(온더플라이 변환, 런타임-SSOT 규칙 준수).

## 운영자 확정 제품 결정 (재론 금지)

1. **새 독립 공개 surface** "데이터 다운로드 센터". 기존 viewer `DataDownloadMenu` 는 그대로 두고, 새것이 더 좋으면 *나중에* 격상(이번 범위 아님).
2. **zip 통짜 다운로드 금지** — 벌크는 HuggingFace 가 이미 준다. 우리는 "슬라이스(뷰)"를 준다.
3. **URL 은 docs 없이 추측 가능**해야 한다.
4. **데이터 추가 시 자동 노출** — 새 회사 parquet·새 카테고리는 코드 0으로 노출.
5. **크기 한도 안에서도 편하게** — 슬라이스·리샘플·링크빌더.

## 2 티어

| 티어 | 백엔드 | 적용 범위 | 핵심 |
|---|---|---|---|
| **Tier 1 — 브라우저 다운로드** | 0 | 노출 dir 전부(날짜샤드 포함) | 브라우저가 parquet 직독→xlsx/CSV 변환. **진짜 MVP 척추** |
| **Tier 2 — 라이브 워커** | CF Worker 1개 | 회사당 flat 파일·series 한정 | parquet→CSV/TSV 온더플라이. Excel·Sheets 라이브 |

운영자 "Tier1 우선" 정합 — Tier 1 이 완전히 쓸모 있게 먼저 출시되고, Tier 2 는 CF 한도 실측 게이트 후 얹는다.

## 문서 라우팅

| 문서 | 내용 |
|---|---|
| [00-product-prd](00-product-prd.md) | 문제·사용자·범위/비범위·성공기준·killList |
| [01-api-contract](01-api-contract.md) | URL 문법·파라미터 4종·포맷·에러·자기기술 (구현자 SSOT) |
| [02-tier1-download](02-tier1-download.md) | 브라우저 parquet 직독 다운로드 (백엔드 0, 재사용 자산) |
| [03-tier2-live-worker](03-tier2-live-worker.md) | CF Worker parquet→CSV 온더플라이 + 보안 allowlist |
| [04-spreadsheet-integration](04-spreadsheet-integration.md) | Excel·Google Sheets 현실 한계와 권장법 |
| [05-validation-and-rollback](05-validation-and-rollback.md) | drift 가드·CF 실측·보안 검증·롤백 |
| [06-progress-ledger](06-progress-ledger.md) | Phase 체크리스트·결정 로그·미결·재개 포인터 |

## 화해 대상 (침범 0)

- **table-export** (구현 완료 Phase1·2a·2b): viewer 안 공시 표 1개→`.xlsx`. 그 writer(`buildWorkbook`)를 *재사용*만 한다.
- **terminal-data-download**: 가격 OHLCV CSV 버튼. 별개 작은 PRD, 공존.
- **viewer `DataDownloadMenu`**: 그대로 둠. 격상은 "나중".
