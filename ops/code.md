# 코드 규칙

dartlab 전체에 적용되는 코드 스타일, 독스트링, 테스트, 릴리즈 규칙.

| 항목 | 내용 |
|------|------|
| 범위 | 전체 코드베이스 |
| 네이밍 | camelCase (함수/변수/파일), snake_case는 하위호환 |
| 독스트링 | 공개 API 함수는 9섹션 필수 |
| 자동 생성 | CAPABILITIES.md, llms.txt, reference.md → `generateSpec.py` |
| 릴리즈 | semver + GitHub Actions trusted publishing |

## 네이밍

- 기존 코드의 네이밍 패턴을 따른다
- 이동된 기존 snake_case는 하위호환 유지 (shim)
- **최신 먼저 역순** — 데이터 정렬 기본값

## 독스트링 9섹션

공개 API 함수는 아래 구조를 따른다. **Returns 섹션은 AI가 반환값을 정확히 이해하는 근본이므로 반드시 키+타입+단위를 명시한다.**

```python
def calcMarginTrend(company, *, basePeriod: str | None = None) -> dict | None:
    """이익 구조 시계열 — 매출에서 순이익까지 금액과 마진.

    Parameters
    ----------
    company : Company
        분석 대상 기업.
    basePeriod : str, optional
        기준 기간.

    Returns
    -------
    dict
        marginTrend : dict
            history : list[dict]
                period : str — 기간 ("2025", "2024Q4")
                revenue : float — 매출 (원)
                operatingMargin : float — 영업이익률 (%)
                netMargin : float — 순이익률 (%)
                grossMargin : float — 매출총이익률 (%)
                revenueYoy : float — 매출 전기 대비 (%)
            displayHints : dict — core 컬럼 목록
        profitabilityFlags : list[str] — 경고 플래그

    Raises
    ------
    ValueError
        알 수 없는 축 이름.

    Examples
    --------
    >>> c.analysis("financial", "수익성")

    Notes
    -----
    basePeriod로 기준 기간 지정 가능.

    Guide
    -----
    인자 없이 호출하면 사용 가능한 축 목록을 안내한다.

    See Also
    --------
    review : analysis 결과를 보고서로 조립.
    """
```

9섹션: Summary, Description, Parameters, Returns, Raises, Examples, Notes, Guide, See Also

### [최우선] Returns 독스트링 작성 규칙

**모든 공개 함수 + 모든 calc 함수**에 Returns를 반드시 작성한다. AI가 이 스키마를 읽어서 반환값의 구조, 단위, 의미를 확정한다.

**포맷**: `키 : 타입 — 설명 (단위)`

```
Returns
-------
dict
    key1 : str — 설명
    key2 : float — 설명 (%)        ← 비율
    key3 : float — 설명 (원)        ← 금액
    key4 : float — 설명 (일)        ← 일수
    key5 : list[dict]
        subkey1 : str — 설명
        subkey2 : float — 설명 (%)
```

**단위 표기 필수**:
- 비율: `(%)` — operatingMargin, roe, debtRatio 등
- 금액: `(원)` — revenue, totalAssets, ocf 등
- 일수: `(일)` — dso, dio, dpo, ccc 등
- 배수: `(배)` — per, pbr, interestCoverage 등
- 점수: `(점)` — healthScore, score 등

**DataFrame 반환 시**:
```
Returns
-------
pl.DataFrame
    종목코드 : str — 6자리 코드
    종목명 : str — 회사명
    영업이익률 : float — (%)
    {period} : float — 기간별 값 (원). 컬럼명 예: "2025Q4"
```

**금지**: `dict — 분석 결과.` 같은 한 줄 Returns. 키를 명시하지 않으면 AI가 추측해야 한다.

**실행 결과 기반**: 독스트링은 추측이 아니라 실제 반환값을 실행해서 확인 후 작성한다.

## CAPABILITIES — 단일 진실의 원천

```
5 surface (Python API, CLI, Server, Data Modules, AI Tools)
    ↓ scripts/build/generateSpec.py (코드에서 자동 수집)
    ├── CAPABILITIES.md                  (루트 총괄 스펙맵)
    ├── landing/static/llms.txt          (AI 크롤러용)
    └── .claude/skills/dartlab/reference.md (Claude Code 스킬)
```

- **CAPABILITIES.md, llms.txt, reference.md는 직접 수정하지 않는다** → `scripts/build/generateSpec.py`로만 생성
- 모듈 추가/변경 시: `uv run python scripts/build/generateSpec.py` 실행
- 릴리즈 전 반드시 실행하여 문서-코드 동기화 확인
- "없다/범위밖" 판단 전에 CAPABILITIES 먼저 확인한다
- registry 소비처: Company property, Excel export, LLM tool, Server API, Skills, CAPABILITIES, llms.txt (7곳)

## 문서/생성물 정합성

- 공개 문서, 스펙, 생성물은 모두 같은 구조를 말해야 한다
- 문서와 코드가 충돌하면 **코드 구조를 기준**으로 문서를 즉시 맞춘다
- 공개 문서에서 내부 클래스명(`DartCompany`, `EdgarCompany` 등) 노출하지 않는다

## 예외 처리

- 구체적 예외 타입을 명시한다 (`except Exception:` 대신 `except ValueError:` 등)
- 사용자 입력 검증은 early return으로 처리
- 에러를 삼키지 않는다

## 테스트

- `test-lock.sh` 필수, 그룹별 분리 실행 (unit → integration → heavy)
- GPU/Ollama 의존 테스트는 mock
- fixture scope는 `module` (session scope 사용하지 않는다)
- 전 기간 데이터로 테스트한다

## 질적 안정 정의 + 1.0.0 선언 기준

**dartlab "질적 안정" = 기능 안정 + 아키텍처 정리 두 축 모두 충족. coverage 숫자만으로 "안정" 선언 금지.**

사용자 원문 (2026-04-21):
> "덕지덕지가 있으면 근본 원소스로 옮기고, 너무 많은 헬퍼들 필요없는 것들 정리하고, 코드 효율성까지 하면서 안정화를 노린다. 안정화가 되어야 1.0.0으로 정식 버전을 선언할 거다."

### 축 1 — 기능 안정
- 외부 사용자 `pip install -U dartlab` → 주요 API crash 없음
- show/select/analysis/scan/credit/quant/review/gather/ask 모두 정상 동작
- wheel-smoke / test_bundledResources / silent-fail lint 다중 방어

### 축 2 — 아키텍처 정리 (4 하위 기준 모두 충족)

1. **덕지덕지 → 근본 SSoT 이전** — 하드코딩 dict + registry 공존 제거. 다단 fallback → 단일 진입점. 패치 위에 패치 금지
2. **불필요한 헬퍼 정리** — 중복 formatter/validator 1곳으로, 반복 boilerplate → 공통 util, 각 엔진 `_helpers.py`·`_utils.py` 10개 → 6 이하, 단일 사용처 helper 는 소비 파일로 inline
3. **코드 효율성** — `@lru_cache` 누락 로더 보강, regex compile 모듈 레벨 상수화, polars native 미활용 hotspot 정리, realData 스위트 30%+ 단축 지표
4. **Dead code 제거** — 0% coverage 실사용 판정 후 삭제, `_reference/`·`_backup/` git rm, 소스 줄 수 10%+ 감축

### 1.0.0 정식 선언 체크리스트 (모두 YES)

- [ ] Q1: routing SSoT 통합 (하드코딩 dict 4/5 제거 + `_showImpl` 복잡도 36→10)
- [ ] Q2: 헬퍼 파일 수 10→6, formatter/validator 중복 제거
- [ ] Q3: F-rank 함수 197→150 이하
- [ ] Q4: realData 스위트 30%+ 속도 개선
- [ ] Q5: src/dartlab 줄 수 10%+ 감축, 0% coverage 파일 0개
- [ ] Q6: 전체 회귀 테스트 + 외부 venv 종합 smoke 통과
- [ ] CHANGELOG 1.0.0 entry (breaking changes + 마이그레이션 가이드)
- [ ] CI green 100%

### 판정 원칙

- **1.0.0 은 사용자가 직접 "1.0.0 해라" 지시할 때까지 어떤 형태로도 다루지 않는다**. 체크리스트 모두 통과해도 자동 선언·제안·version bump·CHANGELOG 1.0.0 entry·"이제 1.0.0 가능합니다" 발언 전부 금지. 체크리스트는 "불가 판정" 도구일 뿐, "가능 선언" 트리거 아님
- 사용자가 "안정" / "1.0.0" 언급 시 이 체크리스트로 판정. 하나라도 미완 → "1.0.0 선언 불가". 전부 통과여도 선언하지 않고 "기준 충족, 선언 대기" 보고만
- coverage 90% 같은 양적 지표만으로 안정 선언 금지 — 4 축 아키텍처 기준이 항상 함께
- 양적 coverage 는 Q6 이후 별도 축으로 상향 가능하지만 선언 기준은 아님

## 릴리즈

- **release 절대 금지** — 사용자 명시 지시 없으면 version bump / git tag / PyPI publish 금지. "릴리즈할까요?" 제안도 금지
- **끝자리(patch)만 올린다** — minor/major는 사용자 지시 시에만
- GitHub Actions trusted publishing
- 절차: `pyproject.toml` 버전 → 커밋 → `git tag vX.Y.Z && git push origin vX.Y.Z`
- CHANGELOG.md + docs/changelog.md 동시 업데이트
- **PyPI wheel 검증 필수** (0.9.11 accountMappings.json 빠진 사고로 확정):
  1. `uv build --wheel` 후 accountMappings.json 포함 확인
  2. json 파일 30개 이상 포함 확인
  3. Node.js 테스트 `cd pyodide && node test_node.mjs` 13/13 통과
  4. PyPI 같은 버전 덮어쓰기 불가

### CHANGELOG 작성 원칙 (사용자가 읽는다)

**관점: 외부 사용자가 이 버전 설치 후 무엇이 달라지는가.** 내부 리팩토링 코드명·플랜 번호·함수 이름·CC 지표는 사용자에게 의미 없다. 쓰지 않는다.

- ❌ 금지: "Q3.1 tail", "F-rank 197→149", "_calcTwoStageDcf CC 63→5", "lru_cache 적용", "regex 상수화", "Phase 2 Act1"
- ✓ 허용: "c.show('bond') 크래시 → None 반환", "c.analysis('예측신호') 에서 구조변화 감지가 이제 정상 동작", "섹션 분석 반복 호출 속도 개선"

**엔트리 구성**:
- `### Fixed` — 사용자가 만나던 크래시·버그가 해결된 것 (증상 + 해결).
- `### Changed` — 사용자가 체감할 동작 변화 (속도 / 반환 타입 / 기본값 등).
- `### Added` — 새 API / 새 옵션.
- `### Removed` — 공개 API 제거 시만. 내부 미사용 정리는 "내부 정리" 한 줄.
- `### Migration` — breaking change 가 있을 때만. 이전 코드 → 새 코드 변환 예시 포함.

**문체**: 간결한 기술체 (중립/사용자 주어). 함수 경로나 라인 번호 나열 금지 (필요하면 commit 해시 링크).

**서문 한 줄**: 이 버전의 주제를 한 문장으로. "내부 안정화 작업" · "성능 개선" · "버그 수정" · "새 기능 X 추가" 중 하나.

**1.0.0 자체 언급 금지** (사용자가 "1.0.0" 지시 전까지). "정식 릴리즈 아님" 같은 문구도 불필요.

## Git

- AI 흔적 커밋 메시지/코드/주석에 포함하지 않는다 (pre-commit hook 자동 차단)
- 커밋 메시지는 한국어 또는 영어
- force push 하지 않는다

## 검증 엄격성

- **AI provider = oauth-codex**: AI 테스트/검증/audit 시 oauth-codex (gemini 아님)
- **벤치마킹 필수**: UI/AI/에이전트 작업 시 Claude Code 벤치마킹 강제
- **ACE 효과 주장 금지**: 자동 메트릭만으로 효과 주장 X — 사람 판정 기반 비교 필수
- **이미지 생성 = Replicate 전용** (`black-forest-labs/flux-1.1-pro`, TTS minimax/speech-02-hd). OpenAI/DALL-E/기타 금지

## 코드 품질 강행규칙

- **클린코드 지향**. 구조 개선이 기능 추가보다 우선
- **wrapper/adapter/bridge 우회 레이어 금지** — 근본 코드 직접 수정
- **사용되지 않는 코드 즉시 삭제** — "나중에 쓸 수도" 금지
- **파라미터 추가보다 설계 변경 먼저 검토**
- **근본 원인 1곳만 수정**: 우회 함수/fallback 분기/private 함수 덕지덕지 패치 금지
