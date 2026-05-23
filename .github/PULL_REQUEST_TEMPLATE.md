<!--
PR 작성 룰 — docs/DEVELOPMENT.md "첫 수정 10분 가이드" + CONTRIBUTING.md 정합 강제.
모든 체크박스는 PR open 시점에 확인되어 있어야 review 진입.
자세한 가이드: docs/DEVELOPMENT.md / docs/TROUBLESHOOTING.md
-->

## 요약 (Summary)

<!-- 이 PR 이 무엇을 바꾸는가? 1-3 문장 (한국어 권장). -->

## 변경 종류 (Type)

- [ ] 추가 (new feature)
- [ ] 수정 (bug fix)
- [ ] 개선 (enhancement)
- [ ] 리팩터 (refactor, behavior 보존)
- [ ] 문서 (docs)
- [ ] 테스트 (tests)
- [ ] 빌드 / CI (build / infrastructure)
- [ ] 보안 (security)
- [ ] 성능 (performance)
- [ ] 의존성 (dependency)
- [ ] 정리 (cleanup, 자동 생성물 동기화)
- [ ] 기타 (other) — 상세는 본문에

## 영향 범위

<!-- 어느 모듈/엔진/사용자에 영향? L0/L1/L1.5/L2/L3/L4/landing/SNS 등 -->

- 영향 모듈: `src/dartlab/...`
- 영향 public API: <!-- __all__ 의 어떤 심볼? 없으면 "없음" -->
- 외부 사용자 영향: <!-- breaking / backwards-compat / docs only -->

## 자기 변경 path 명시 (CLAUDE.md 강행규칙)

<!-- 본 PR 의 자기 변경 파일 명시. git add -A / git add . 금지. -->

```
src/dartlab/<module>/<file>.py
tests/unit/test_<module>.py
docs/<doc>.md
```

## preflight 결과

<!-- uv run python -X utf8 tests/run.py preflight 결과 첨부 -->

- [ ] 27 게이트 fast tier 통과 (`tests/run.py preflight`)
- [ ] `ruff check` + `ruff format --check` 통과
- [ ] `tests/audit/lint_camelcase_ast.py --changed --strict` 통과
- [ ] 변경 모듈에 `bash tests/test-lock.sh tests/<path> -m "<marker>" -v` 추가 fail 0

## 테스트 / 검증

<!-- 어떤 테스트로 검증했나? -->

- [ ] 단위 테스트 (`tests/unit/`)
- [ ] 통합 테스트 (`tests/integration/`)
- [ ] property-based (`hypothesis`) — public 계산 함수일 때
- [ ] snapshot (`syrupy`) — CLI / 출력 형식 변경일 때
- [ ] 직접 dartlab REPL 실행 결과 첨부

## docstring / 문서 (public API 변경 시)

- [ ] `__all__` 변경 시 9 섹션 docstring 갱신 (Capabilities/Args/Returns/Example/Guide/SeeAlso/Requires/AIContext/LLM Specifications)
- [ ] `CHANGELOG.md` `[Unreleased]` 섹션 항목 추가
- [ ] deprecated API 추가 시 `DEPRECATION.md` 항목 + `@deprecated(...)` 데코레이터
- [ ] 새 엔진/recipe 시 Skill OS (`src/dartlab/skills/specs/`) 4 단계 동기화

## 메모리 안전 (CLAUDE.md 강행규칙)

- [ ] 새 캐시 추가 시 `BoundedCache` 사용 (무제한 dict 금지)
- [ ] pytest fixture scope = `module` 또는 `function` (session 금지)
- [ ] Company 사용 테스트는 `serial` marker

## 관련 이슈

<!-- Closes #123, Related #456 -->

## 검토 요청

<!-- 특별히 봐줬으면 하는 부분 명시. 예: "T9-1 providers 분해 진행 중, 3계층 명확화 부분 검토 요청" -->

---

<!--
체크리스트 미완 / 자기 변경 path 미명시 PR 은 자동 라벨 "needs-revision" 부여.
docs only PR 은 일부 게이트 면제 가능 (CI Fast 자체는 통과 필요).
보안 라벨 자동: dependabot 또는 commit prefix "보안:" 일 때.
breaking 라벨 자동: __all__ 시그니처 변경 시 import-linter 가 감지.
-->
