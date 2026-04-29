# Refactor Checklist — 대규모 rename / API 변경 6 단계

> **목적**: 한 이름이 src/ + tests/ + ops/ + blog/ + sns/ + landing/ + .github/scripts/ +
> workflow + CHANGELOG + 자동생성물에 다 박힌 dartlab 의 특성상, 변경 후 일부 위치에
> 옛 이름이 남는 "95% 완료 패턴" 이 반복됐다. 본 체크리스트는 모든 변경 채널을
> 강제 점검 대상으로 만든다.

이 문서는 다음 상황에서 적용된다:

- 공개 API 메서드/함수/클래스 rename (예: `c.review()` → `c.story()`)
- 모듈 경로 이전 (예: `dartlab.engines.X` → `dartlab.providers.X`)
- 폐기 (예: `c.docs.X` namespace → `c.show(topic)` 단일 진입)
- registry/dataclass 필드 rename, 변수/contextvar rename
- MCP 도구명 변경

작은 함수 시그니처 추가 같은 비파괴적 변경은 본 체크리스트 대상이 아니다 (그 경우는
[ops/api-contract.md](api-contract.md) 만 따른다).

## 자동 게이트 — 사람이 빠뜨려도 막히는 안전망

각 채널 점검 전에 자동 게이트가 있다. 게이트 통과를 점검 완료의 증거로 쓴다:

- `scripts/audit/stale_references.py` — 옛 이름 잔존을 17 패턴으로 검사 (CI 강제, ci-fast lint)
- `scripts/audit/stalePatterns.yaml` — 패턴 SSOT. 폐기 시점에 새 패턴 추가 (severity error)
- `scripts/audit/qualityGate.py` — F-rank, 헬퍼 파일 수, dead code baseline (warn)
- `.github/workflows/ci-fast.yml` — push/PR 마다 위 게이트 자동 실행

stale_references 가 0 건이 아니면 "완료 선언" 금지. 위반은 무조건 자동 막힘.

## 6 단계 점검

각 단계 끝에 명시된 grep 명령으로 잔존을 직접 확인. 결과 0 건이어야 다음 단계.

### 1. src 변경

핵심 코드 + docstring + Returns 단위 표기 + 에러 메시지까지.

- 함수/메서드/클래스 본체
- docstring (Summary, Description, Parameters, Returns, Raises, Examples, Notes, Guide, See Also — 9 섹션)
- 모듈 docstring (`"""..."""` 첫 줄)
- 에러 메시지 문자열 (`raise ValueError("옛 이름 사용 금지")` 같은 안내문)
- 타입 힌트 (`Literal[...]`, `TypedDict` 키 등)

```bash
# 옛 이름이 src 에 잔존하지 않는지
grep -rn "옛이름" src/dartlab/
```

### 2. tests 변경

새 contract 가 테스트로 강제되는지.

- unit 테스트 + integration 테스트 + realData 테스트
- fixture (`tests/fixtures/`) 의 코드 / 데이터
- `tests/conftest.py` 의 helper
- 폐기된 옛 API 테스트는 삭제 또는 "deprecation 검증" 으로 명시 전환

```bash
grep -rn "옛이름" tests/
# 새 이름이 최소 1건 이상 테스트로 검증되는지
grep -rn "새이름" tests/
```

### 3. ops/ 문서 변경

해당 엔진 문서 + cross-cutting 문서.

- `ops/{engine}.md` (해당 엔진)
- `ops/api-contract.md` (공개 API 추가/제거 시)
- `ops/code.md` (docstring 규약 영향 시)
- `ops/architecture.md` (레이어 변경 시)
- `ops/philosophy.md` (사상 영향 시)
- 폐기 명시 anti-pattern note 가 있으면 ops 안에 명시 (예: `ops/api-contract.md` 의
  "이 패턴은 폐기되었다" 섹션). stale_references 의 default_whitelist 와 정합.

```bash
grep -rn "옛이름" ops/
```

### 4. 블로그 / SNS / landing 변경

사용자 노출 콘텐츠. 이 단계가 가장 자주 빠진다.

- `blog/**/*.md` — 블로그 포스트
- `blog/**/*.svg` — 블로그 자산 (코드 스니펫 박힌 SVG 도 잡힌다)
- `sns/**/*.md` — 쇼츠/캐러셀/릴스 스크립트
- `landing/src/**/*.svelte` + `landing/src/**/*.ts` — 랜딩 페이지
- `landing/static/llms.txt` (자동 생성물 — 마지막 단계에서 재빌드)
- `README.md` / `README_EN.md` / `CAPABILITIES.md` (CAPABILITIES 는 자동 생성물)

```bash
grep -rn "옛이름" blog/ sns/ landing/src/
```

### 5. workflow + CI 스크립트 변경

`.github` 트리 전체.

- `.github/workflows/*.yml` — ci-fast, ci-full, publish, ai-policy 등
- `.github/scripts/*.py` — workflow 가 호출하는 보조 스크립트
- `.github/ISSUE_TEMPLATE/*.yml` — 이슈 템플릿 안의 코드 예시
- `.github/pull_request_template.md`
- `scripts/dev/*.py` + `scripts/audit/*.py` + `scripts/build/*.py` — 모든 자동화 스크립트
- `scripts/audit/stalePatterns.yaml` — 폐기되는 이름이면 새 패턴 추가 (다음 사고
  자동 차단)

```bash
grep -rn "옛이름" .github/ scripts/
```

### 6. 자동 생성물 재빌드

마지막에 한 번. 이전 단계의 변경이 모두 src 에 들어간 후.

- `python -X utf8 scripts/build/generateSpec.py` — `CAPABILITIES.md`,
  `landing/static/llms.txt`, 로컬 에이전트 reference,
  `src/dartlab/core/_generated.py`, `_generatedCapabilities.py` 재빌드
- `pyodide` 번들이 영향받으면 `pyodide/build.sh`
- 노트북 동기화 영향이면 `python scripts/build/syncColabFromMarimo.py`

```bash
# 자동 생성물에 옛 이름이 남았다면 generateSpec 누락
grep -n "옛이름" CAPABILITIES.md landing/static/llms.txt
```

## 종합 검증

6 단계 끝나면 자동 게이트 한 번 더:

```bash
# 1. stale references 0 건
python scripts/audit/stale_references.py

# 2. silent-fail 패턴 0 건
python scripts/dev/checkSilentFail.py

# 3. 단위 테스트 + 통합 테스트
bash scripts/dev/test-lock.sh tests/ -m "unit and not requires_data" -v --tb=short
bash scripts/dev/test-lock.sh tests/ -m "integration and not realData and not heavy and not requires_data" -v --tb=short

# 4. wheel 검증 (배포 영향 변경이면)
uv run python -X utf8 scripts/build/verifyWheel.py dist/dartlab-*.whl

# 5. 외부 venv smoke (PyPI 배포 직후)
python -m venv /tmp/dartlab-fresh
/tmp/dartlab-fresh/bin/pip install -U dartlab
/tmp/dartlab-fresh/bin/python -c "
import dartlab
c = dartlab.Company('005930')
c.show('BS')
c.story()
"
```

## 위반 사례 (학습용)

| 사고 | 빠진 단계 | 결과 |
|---|---|---|
| 2026-04-26 v0.9.22 review→story rename | 5 (`planRealdata.py` 의 `test_review.py` 잔존) | CI Full fail, hotfix 커밋 |
| 2026-04-26 c.docs/c.finance namespace 폐기 | 4 (블로그 SVG + landing svelte) | 외부 사용자 가이드에 옛 API 노출 |
| 2026-04-26 `_review_currency` contextvar | 1 (변수명만 바꾸고 호출처 한 곳 누락) | CI Full fail, hotfix 커밋 |
| 2026-04-19 v0.9.15 wheel parserMappings 누락 | 6 (자동 생성물 재빌드 우회) | PyPI 0.9.15 즉시 폐기, 0.9.16 재발행 |

## 신규 폐기 패턴 추가 절차

새 rename / 폐기 시 stale_references 패턴 추가는 동시에 한다 (별도 PR 금지):

1. `scripts/audit/stalePatterns.yaml` 의 `patterns` 에 새 entry 추가
2. 정규식이 false positive 안 내는지 grep 으로 사전 검증
3. 도입 시점에 0 건 (또는 default_whitelist 처리) 확인
4. severity 처음에는 `warn` 으로 시작, 1 주 관찰 후 `error` 로 승격

## 사상

이 체크리스트는 사람의 주의력에 의존하지 않는다. 자동 게이트가 0 건을 강제할 때만
"완료" 라고 부른다. 자동 게이트가 막지 못한 채널이 발견되면 stalePatterns.yaml 에
패턴을 추가해 다음번부터 자동 차단한다 — 사람이 같은 실수를 두 번 안 하도록.
