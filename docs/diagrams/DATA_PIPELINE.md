# Data Pipeline — sync ↔ HF ↔ prebuild ↔ runtime

> dartlab 데이터 흐름의 *시간 순서* 표현. ARCHITECTURE.md 의 정적 구조와 짝.

---

## 일간 cron 흐름

```mermaid
sequenceDiagram
    autonumber
    participant Cron as GitHub cron
    participant Sync as .github/scripts/sync/
    participant API as 외부 API
    participant Local as data/_raw/
    participant HF as HuggingFace
    participant Prebuild as .github/scripts/prebuild/
    participant Derived as data/_derived/
    participant User as dartlab 사용자

    Cron->>Sync: 매일 08:00 KST 트리거
    Sync->>API: DART/EDGAR/FRED/ECOS/KRX 호출 (online)
    API-->>Sync: raw response
    Sync->>Local: parquet 저장 + dataLineage.recordLineage()
    Sync->>HF: bulkUploadHf.py push
    HF-->>Sync: 확인
    Sync->>Sync: dataDriftCheck (5σ row count)

    Note over Prebuild,Derived: prebuild 별도 trigger (offline)
    Cron->>Prebuild: 매일 09:00 KST
    Prebuild->>HF: hf_hub_download (HF dataset)
    HF-->>Prebuild: parquet
    Prebuild->>Prebuild: enforceOffline() 강제
    Prebuild->>Derived: derived parquet/json

    User->>Local: import dartlab
    Local-->>User: BoundedCache hit (1.0s/corp)
    User->>HF: cache miss → 자동 다운로드
    HF-->>User: parquet
```

---

## 사용자 첫 호출 (cold)

```mermaid
flowchart LR
    A[import dartlab] --> B{cache 확인}
    B -->|hit| C[BoundedCache 1.0s/corp]
    B -->|miss| D[HuggingFace 다운로드]
    D --> E[BoundedCache 저장]
    E --> C
    C --> F[Company 인스턴스]
    F --> G[Company.show / scan / Story]
```

---

## 사고 차단 가드

| 단계 | 가드 | 정합 |
|------|------|------|
| sync 단계 | online API 호출 정상 | sync vs prebuild 분리 |
| prebuild 단계 | `enforceOffline()` monkey-patch | T7-2 dataAudit |
| HF 업로드 | dataDriftCheck 5σ | T7-5 |
| HF 보관 | DART 원본 zip 3층 가드 | CLAUDE.md "DART 원본 zip 비공개" |
| 사용자 다운로드 | BoundedCache 메모리 안전 | T3-4 profileCall |

---

## 관련

- [ARCHITECTURE.md](ARCHITECTURE.md) — 정적 구조
- [../../src/dartlab/core/dataAudit.py](../../src/dartlab/core/dataAudit.py) (T7-2)
- [../../.github/scripts/sync/dataDriftCheck.py](../../.github/scripts/sync/dataDriftCheck.py) (T7-5)
