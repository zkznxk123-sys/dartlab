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

`tests/audit/deprecationAudit.py` (T8-1 트랙) 가 PR 차단:

1. 코드 안 `@deprecated(...)` 데코레이터 검출 → 본 문서 항목 존재 강제
2. 본 문서 "Remove in" 버전이 현재 버전 도달 → CI fail (제거 누락 차단)
3. `__all__` 에서 사라진 심볼 → "Removed" 섹션 등록 강제

---

## Currently Deprecated

> 본 섹션은 PR 마다 자동 동기화 (deprecationAudit 통과 조건).

*(현재 deprecated 항목 0. 첫 항목 추가 시 본 섹션 위 형식대로 채움.)*

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
