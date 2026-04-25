# 코드 규칙

> 상위 사상: [philosophy.md](philosophy.md) · 자가개선 루프: [coreloop.md](coreloop.md)

**주체**: 개발자 + AI (dartlab 전 코드베이스).
**현재**: camelCase 네이밍 · 9 섹션 독스트링 규약 · 1.0.0 선언 체크리스트 · CHANGELOG 사용자 관점 원칙 확립.
**방향**: 공개 API Returns 단위 보강 · CAPABILITIES 자동 생성 확대 · wheel 검증 강화.

dartlab 전체에 적용되는 코드 스타일, 독스트링, 테스트, 릴리즈 규칙. 각 섹션은 **"이렇게 한다"** 명제로 열고, 반복된 실수는 섹션 하단 **"반복 실패"** 에 정리한다.

| 항목 | 내용 |
|---|---|
| 범위 | 전체 코드베이스 |
| 네이밍 | camelCase (함수·변수·파일), snake_case 는 하위호환 |
| 독스트링 | 공개 API 함수는 9 섹션 필수 |
| 자동 생성 | CAPABILITIES.md · llms.txt · reference.md → `generateSpec.py` |
| 릴리즈 | semver + GitHub Actions trusted publishing |

---

## 1. 네이밍 — camelCase 로 간다

- 기존 코드의 네이밍 패턴을 따른다.
- 이동된 기존 snake_case 는 하위호환 유지 (shim).
- **최신 먼저 역순** — 데이터 정렬 기본값.

---

## 2. 독스트링 — 9 섹션으로 쓴다

공개 API 함수는 아래 구조를 따른다. **Returns 섹션은 AI 가 반환값을 정확히 이해하는 근본이므로 반드시 키 + 타입 + 단위를 명시한다.**

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
    story : analysis 결과를 보고서로 조립.
    """
```

9 섹션: Summary · Description · Parameters · Returns · Raises · Examples · Notes · Guide · See Also.

### Returns 작성 규칙 — 키 + 타입 + 단위를 명시한다

**모든 공개 함수 + 모든 calc 함수**에 Returns 를 반드시 작성한다. AI 가 이 스키마를 읽어서 반환값의 구조·단위·의미를 확정한다.

**포맷**: `키 : 타입 — 설명 (단위)`.

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

**단위 표기**:
- 비율: `(%)` — operatingMargin · roe · debtRatio 등
- 금액: `(원)` — revenue · totalAssets · ocf 등
- 일수: `(일)` — dso · dio · dpo · ccc 등
- 배수: `(배)` — per · pbr · interestCoverage 등
- 점수: `(점)` — healthScore · score 등

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

**실행 결과 기반**: 독스트링은 추측이 아니라 실제 반환값을 실행해서 확인 후 작성한다.

**반복 실패** — `dict — 분석 결과.` 같은 한 줄 Returns 는 AI 가 추측하게 만든다. 키를 전부 명시한다.

---

## 3. CAPABILITIES — 단일 진실의 원천으로 간다

```
5 surface (Python API, CLI, Server, Data Modules, AI Tools)
    ↓ scripts/build/generateSpec.py (코드에서 자동 수집)
    ├── CAPABILITIES.md                  (루트 총괄 스펙맵)
    ├── landing/static/llms.txt          (AI 크롤러용)
    └── .claude/skills/dartlab/reference.md (Claude Code 스킬)
```

- `CAPABILITIES.md` · `llms.txt` · `reference.md` 는 **직접 수정하지 않는다** → `scripts/build/generateSpec.py` 로만 생성.
- 모듈 추가·변경 시: `uv run python scripts/build/generateSpec.py` 실행.
- 릴리즈 전 반드시 실행해 문서-코드 동기화 확인.
- "없다·범위밖" 판단 전에 CAPABILITIES 먼저 확인한다.
- registry 소비처: Company property · Excel export · LLM tool · Server API · Skills · CAPABILITIES · llms.txt (7 곳).

---

## 4. 문서·생성물 정합성 — 코드 기준으로 맞춘다

- 공개 문서·스펙·생성물은 모두 같은 구조를 말해야 한다.
- 문서와 코드가 충돌하면 **코드 구조를 기준** 으로 문서를 즉시 맞춘다.
- 공개 문서에서 내부 클래스명 (`DartCompany` · `EdgarCompany` 등) 노출하지 않는다.

---

## 5. 예외 처리 — 구체적 타입으로 처리한다

- 구체적 예외 타입을 명시한다 (`except Exception:` 대신 `except ValueError:` 등).
- 사용자 입력 검증은 early return 으로 처리.
- 에러를 삼키지 않는다.

---

## 6. 테스트 — lock wrapper 로 그룹별 분리 실행한다

- `test-lock.sh` 필수, 그룹별 분리 실행 (unit → integration → heavy).
- GPU · Ollama 의존 테스트는 mock.
- fixture scope 는 `module` (session scope 사용하지 않음).
- 전 기간 데이터로 테스트한다.

---

## 7. 릴리즈 — semver + GitHub Actions trusted publishing 으로 간다

### 기본 흐름
1. `pyproject.toml` 의 `version` 수정.
2. 변경 내역을 `CHANGELOG.md` 에 기록 (keep-a-changelog 포맷).
3. master push 후 `git tag vX.Y.Z && git push origin vX.Y.Z`.
4. `publish.yml` 이 PyPI 업로드 + wheel 리소스 검증 실행.

### wheel 번들 검증 (0.9.11 `accountMappings.json` 누락 사고 이후 고정)
- `uv build --wheel` 결과에 `accountMappings.json` 포함 확인.
- 번들 json 파일 30 개 이상 포함 확인.
- `cd pyodide && node test_node.mjs` 13/13 통과.

**반복 실패** — PyPI 는 같은 버전 덮어쓰기를 허용하지 않으므로, 검증 실패 시 새 patch 버전으로 재발행해야 한다. 0.9.11 에서 `accountMappings.json` 이 빠진 채 배포되어 pyodide 테스트가 전체 실패한 사고 재발 방지.

---

## 8. 검증 엄격성 — 사람 판정 + 고정 provider 로 간다

- **AI provider = oauth-codex** — AI 테스트·검증·audit 시 oauth-codex 사용 (gemini 아님).
- **벤치마킹 필수** — UI·AI·에이전트 작업 시 Claude Code 벤치마킹 강제.
- **이미지 생성 = Replicate 전용** — `black-forest-labs/flux-1.1-pro`, TTS 는 `minimax/speech-02-hd`.

**반복 실패** — 자동 메트릭만으로 ACE 효과 주장. 사람 판정 기반 비교가 필수. OpenAI · DALL-E · 기타 provider 는 이미지 생성에 쓰지 않는다.

---

## 9. 코드 품질 — 근본 원인 한 곳에서 고친다

- **클린코드 지향** — 구조 개선이 기능 추가보다 우선.
- **근본 코드 직접 수정** — wrapper · adapter · bridge 우회 레이어는 쓰지 않는다.
- **사용되지 않는 코드 즉시 삭제** — "나중에 쓸 수도" 는 쓰지 않는다.
- **파라미터 추가보다 설계 변경 먼저 검토**.
- **근본 원인 1 곳만 수정** — 우회 함수 · fallback 분기 · private 함수 덕지덕지 패치는 쓰지 않는다.

**반복 실패** — 증상 위에 패치를 더하면 "수정" 이 아니라 기술 부채. 증상 보이는 곳 ≠ 근본. 근본 위치를 식별한 뒤 1 곳에서 고친다.

---

## 요약 — 명제 9 줄

1. 네이밍은 camelCase, 기존 snake_case 는 하위호환 shim.
2. 독스트링은 9 섹션 + Returns 에 키·타입·단위까지 명시한다.
3. CAPABILITIES 는 `generateSpec.py` 자동 생성 SSOT — 직접 수정하지 않는다.
4. 문서·코드 충돌은 코드 기준으로 문서를 맞춘다.
5. 예외는 구체적 타입으로 잡고 삼키지 않는다.
6. 테스트는 `test-lock.sh` 로 unit → integration → heavy 그룹 분리 실행.
7. 릴리즈는 semver + GitHub Actions trusted publishing + wheel 번들 전수 검증.
8. AI provider 는 oauth-codex · 이미지는 Replicate 전용 · 사람 판정 기반 검증.
9. 근본 원인 1 곳만 고친다 — 우회 레이어·덕지덕지 패치는 쓰지 않는다.
