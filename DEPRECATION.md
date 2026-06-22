# DEPRECATION 정책

> dartlab 의 public API 제거·교체 정책. 외부 사용자가 *언제 무엇이 사라지는지* 미리 알 수 있게 강제.
> 본 문서는 [VERSIONING.md](docs/VERSIONING.md) 와 짝. [RELEASE.md](docs/RELEASE.md) 의 체크리스트가 본 정책 정합을 검증.

---

## 정책

### 3 minor version notice 룰

public API (`dartlab.__all__` 에 포함된 심볼) 는 **deprecation 후 최소 3 minor version 동안 유지** 후 제거.

| 단계 | 시점 | 동작 |
|------|------|------|
| **deprecated 표시** | v0.X.Y | `@deprecated("0.X.0", alternative="...")` 데코레이터 부착. `DartlabDeprecationWarning` 발급 |
| **유예 기간** | v0.X.Y ~ v0.(X+2).Y | API 동작 유지. 본 문서에 항목 추가. CHANGELOG 에 "Deprecated" 섹션 명시 |
| **제거** | v0.(X+3).0 | 코드 삭제. 본 문서에서 "Removed" 섹션으로 이동. `ImportError` 또는 `AttributeError` 발생 |

예: v0.10.x 에서 deprecated → v0.13.0 에서 제거 가능.

### 1.0.0 이후

1.0.0 출시 후 (목표 2027-02-28) 는 **6 minor version** notice 로 확장 (LTS 정합).

---

## 형식 강제

각 deprecated API 는 본 문서에 다음 형식으로 항목 추가:

```markdown
### {api_name}

- **Deprecated since**: v0.X.Y
- **Remove in**: v0.(X+3).0
- **Replacement**: `new_api_name(...)` (또는 *없음*)
- **Reason**: 한 줄 사유
- **Migration**: 코드 예시 (before → after)
```

### 자동 검증

`tests/audit/deprecationAudit.py` 가 ci-fast `lint` 게이트에서 PR 차단 (debt-honesty P1-3 에서
*유령 가드 → 실 구현*: 오랫동안 본 문서가 강제한다고 약속했으나 파일 자체가 부재했음). 현재 검사:

1. **raw stdlib `DeprecationWarning` 금지 (ratchet)** — deprecation 은 사용자에게 보이는
   `DartlabDeprecationWarning`(FutureWarning 하위) / `warnDeprecated` / `@deprecated` 만 써야 한다.
   raw `warnings.warn(..., DeprecationWarning, ...)` 는 숨겨져 "언제 무엇이 사라지는지" 알림을 침묵시킨다.
   현재 9 사이트는 baseline 동결(`tests/audit/_baselines/deprecationAudit.json`), *신규만 차단* (목표 0).
2. **`@deprecated(...)` 데코레이터 → 본 문서 항목 존재 강제** — 데코 심볼이 본 문서에 없으면 fail.

미구현(후속): "Remove in" 버전 도달 자동 fail · `__all__` 제거 심볼 "Removed" 강제 — 현재는 RELEASE 체크리스트 수동 검증.

---

## Currently Deprecated

> raw `DeprecationWarning` 으로 알림 중인 deprecated alias 9 사이트 (baseline 동결 ratchet).
> `DartlabDeprecationWarning` 이관 시 사용자 가시화 + baseline 항목 제거가 목표 (debt-honesty P1-3).

| API | 대체 | 위치 |
|-----|------|------|
| `company._report.dividend/employee/majorHolder/executive/audit` (property 5) | `c.panel("…")` | `providers/dart/accessor/reportAccessor.py` |
| `company._profile.get(topic)` | `c.show(topic)` / `c.finance.*` | `providers/dart/accessor/profileAccessor.py` |
| `dartlab.quant("코드", "축")` 역순 호출 | `dartlab.quant("축", "코드")` | `quant/__init__.py` |
| `dartlab.credit("코드", "축")` 역순 호출 | id-first 자동 swap | `credit/__init__.py` |
| `story.buildStory` legacy 인자 | registry dispatch | `story/registry.py` |

---

## Removed

> 제거 완료된 API 의 history (영구 보존, 외부 사용자가 *왜 사라졌는지* 추적 가능).

*(현재 removed 항목 0.)*

---

## SemVer 정합

본 정책은 SemVer 2.0 의 *minor 호환성* 룰을 강화한 것:

- 0.x.x: minor (X) 증가 시 *deprecated* 항목 제거 가능. 즉 3 minor notice 가 최소 조건.
- 1.x.x+: minor 증가는 backwards-compat 강제. major (X) 증가만 deprecated 제거 허용.

상세: [docs/VERSIONING.md](docs/VERSIONING.md)

---

## 관련

- 코드: `src/dartlab/core/deprecation.py` (`@deprecated`, `warnDeprecated`, `DartlabDeprecationWarning`)
- 게이트: `tests/audit/deprecationAudit.py` (T8-1)
- 정책: [docs/VERSIONING.md](docs/VERSIONING.md), [docs/RELEASE.md](docs/RELEASE.md)
- CHANGELOG: [CHANGELOG.md](CHANGELOG.md) "Deprecated" 섹션
