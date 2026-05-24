# reference/ — L1.5 정적 룩업 + 매핑

> 산업 맵 / accountMappings / capability registry 등 *정적 reference 데이터* + 매핑 엔진.

| 모듈 / 데이터 | 역할 |
|--------------|------|
| `reference/data/accountMappings.json` | 한국 XBRL ↔ snakeId 매핑 (34622 항목, T7-1 버전 추적) |
| `reference/data/_version.json` | accountMappings 버전 + history (T7-1) |
| `reference/mapper.py` | 매핑 엔진 (suffix trim / 학습 synonym) |
| `reference/industry/` | 산업 카테고리 / KSIC |

## 룰

- L1.5 형제 cross import 금지 (scan / frame / synth 와 분리)
- accountMappings 변경 시 _version.json history 항목 + 버전 bump 강제 (T7-1 audit)
- mapper.py suffix trim ("액", "등", "외") 1글자 — cycle 12 회귀 가드 (memory/feedback_account_mapping_suffix_trim)

## 관련

- [src/dartlab/reference/data/_version.json](data/_version.json) (T7-1)
- [tests/audit/accountMappingsDriftAudit.py](../../../tests/audit/accountMappingsDriftAudit.py) (T7-1)
- [src/dartlab/skills/specs/operation/mappingRefresh.md](../skills/specs/operation/mappingRefresh.md)
