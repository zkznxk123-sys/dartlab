# Skill OS — `engines/` 카테고리 hub

> dartlab 의 15 분석 엔진 spec. 각 엔진 폴더는 `SKILL.md` (공개 호출 / 호출 동작 / 대표 반환 3 강제 섹션) 보유.

---

## 15 엔진 라우팅

| 계층 | 엔진 | 책임 |
|------|------|------|
| **L1.5 frame** | [data](data/) | provider raw → 분석 ready frame |
| **L1.5 scan** | [scan](scan/) | 횡단면 스크리닝 |
| **L1.5 reference** | [mappers](mappers/) | XBRL ↔ KOR/ENG 매핑 |
| **L1.5 search** | [search](search/) | 검색 인덱스 (FM-index / inverted) |
| **L1 gather** | [gather](gather/) | 외부 API 수집 owner |
| **L1 provider** | [edgar](edgar/) | EDGAR (US) 전용 |
| **L2 분석** | [analysis](analysis/) | 재무 분석 (cashflow / ratios) |
| **L2 분석** | [credit](credit/) | 신용 점수 (Z-score / Altman) |
| **L2 분석** | [macro](macro/) | 거시 (cycle / sector rotation) |
| **L2 분석** | [quant](quant/) | 퀀트 factor / alpha |
| **L2 분석** | [industry](industry/) | 섹터 / peer 매트릭스 |
| **L3 조합기** | [story](story/) | 8 막 인과 + ref 조합 |
| **L4 소비자** | [company](company/) | Company facade (단일 종목 진입점) |
| **표현 / 전송** | [dashboard](dashboard/) | bento 대시보드 layout |
| **표현 / 전송** | [viz](viz/) | 차트 spec codegen |

---

## 엔진 spec 표준 (각 폴더 SKILL.md)

3 강제 섹션:

1. **공개 호출 방식** — facade API 진입 함수 시그니처
2. **호출 동작** — 내부 흐름 + ref 발급 / 메모리 / 캐시
3. **대표 반환 형태** — DataFrame schema 또는 dict 구조 예시

---

## 새 엔진 추가

```bash
uv run python -X utf8 src/dartlab/skills/addEngine.py {name}
```

5 단계 자동:
1. 폴더 + `__init__.py` skeleton
2. re-export to top-level `dartlab/__init__.py`
3. importlinter contract 자동 추가
4. skill.md spec 템플릿 (3 강제 섹션)
5. architecture.md 노드 추가

상세: [TODO.md](../../../../../TODO.md) T5-4 addEngine 완성 트랙.

---

## 다음 카테고리

- **start/** — 첫 진입
- **operation/** — 운영 설계 SSOT
- **runtime/** — 실행 환경
- **recipes/** — 분석 recipe lifecycle (각 엔진 안 recipe 분류)

---

## 관련

- [operation/architecture.md](../operation/architecture.md) — 4 계층 단방향 import 룰
- [operation/code.md](../operation/code.md) — engine 폴더 안 코드 룰
- [SCHEMA.md](../SCHEMA.md) — SKILL.md frontmatter / capabilityRefs 명세
