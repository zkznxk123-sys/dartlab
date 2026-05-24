# gather/ — L1 외부 수집

> dartlab 의 *L1 raw 생산 owner* 중 하나 — 가격 / 수급 / 뉴스 / 거시지표 외부 데이터 수집.
> providers/ (DART/EDGAR/EDINET) 와 동급 L1.

| 모듈 | 역할 |
|------|------|
| `gather/price.py` | 가격 시계열 |
| `gather/flow.py` | 외국인 / 기관 수급 |
| `gather/news.py` | 뉴스 본문 (untrusted 마커 강행) |
| `gather/macro/` | FRED / ECOS 거시지표 |
| `gather/mapping/` | 코드 매핑 (티커 ↔ 종목코드) |

## 룰

- L1 raw 생산 owner — 외부 API 호출은 본 폴더만
- core 만 import (gather ↛ providers 상호 금지)
- 외부 본문 untrusted — wrap_external_in_result 마커 (T2-5 audit)
- prebuild 단계 import 금지 (offlineGuard, T7-2)

## 관련

- [src/dartlab/skills/specs/engines/gather/SKILL.md](../skills/specs/engines/gather/SKILL.md)
- [tests/audit/untrustedWrapAudit.py](../../../tests/audit/untrustedWrapAudit.py) (T2-5)
- [.github/scripts/sync/](../../../.github/scripts/sync/) — sync workflow online 단계
