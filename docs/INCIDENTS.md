# INCIDENTS — 사고 기록 + RCA

> dartlab 의 *공개* 사고 기록. 시스템 가드 위반 / 사용자 보고 사고 / SLO 침범 발생 시 24h 안 RCA 추가.
> 비공개 운영자↔AI 사고 기록은 `memory/incidents.md` (L-memory) 별도.
> SLO burn alert ([SLO.md](SLO.md)) 5% 초과 시 본 문서 항목 자동 issue 생성 (T1-3 + T1-4 후속).

---

## RCA 템플릿

각 항목은 본 형식 강제:

```markdown
## YYYY-MM-DD — {짧은 제목}

- **분류**: regression | data-quality | security | infra | dependency | docs
- **영향 범위**: 어떤 사용자/시스템/SLO 가 영향받았나
- **지속 시간**: 발견 → 복구 까지
- **증상**: 외부에서 관측된 현상
- **원인** (5 whys 또는 fishbone):
  1. ...
  2. ...
  3. ...
- **수정**: commit hash + 짧은 설명
- **재발 가드**: 추가된 lint/test/audit + baseline 부채 원장 갱신
- **학습**: 이 사고로 어떤 정책/문서/툴이 갱신됐나
```

---

## 2026-05 — CI Fast 통과 0건 누적 사고

- **분류**: regression
- **영향 범위**: master 브랜치 + 외부 기여자 첫 PR 막힘. 약 30일.
- **지속 시간**: 2026-04 중순 ~ 2026-05-09 (점검 시점).
- **증상**: 최근 50 push 중 CI Fast 통과 0건. 매 push 마다 1개 이상 fast tier gate fail.
- **원인**:
  1. 푸시 전 `tests/run.py preflight` 12 게이트 통과 *룰* 은 있었지만 자동 강제 hook 0
  2. 사용자가 push 전 일부 게이트만 수동 실행 → 다른 게이트 누락
  3. CI 와 로컬 환경 명령이 *말로만* 동일하다고 가정 (실제 바이트 단위 동일 미보장)
  4. 환경: venv `pip` 모듈 누락 (`No module named pip`) → 모든 gate 시작 시점 실패
- **수정**:
  - `tests/run.py preflight` 단일 진입점 강행 (CI matrix 와 바이트 단위 동일 명령)
  - 27 게이트 SSOT — 로컬 ↔ CI 일치
  - `bash tests/test-lock.sh` wrapper 강제
  - `.claude/skills/ci-fast-local/SKILL.md` 절차서 추가
- **재발 가드**:
  - CLAUDE.md 강행규칙 "변경 단위 = 자기 변경 + 테스트 셋트 + CI 통과 검증 + 푸시 준비" 박힘
  - `pre-push` hook 으로 preflight 자동 발동 검토 (후속)
  - metrics workflow (T1-2) 가 통과율 시계열 시각화
- **학습**:
  - 로컬↔CI 동일성은 *명령 SSOT* 가 SSOT 여야 보장 (문서로 안 됨)
  - 환경 부트스트랩 실패 (`venv/pip` 누락) 도 CI fail 표면화 강제 필요

---

## 2025-04 ~ 2026-02 — allFilings 빈 parquet 영구 데드락 (222일치)

- **분류**: data-quality
- **영향 범위**: DART OpenAPI allFilings 본문 수집의 자동 재시도 차단. 222 일치 누적.
- **지속 시간**: 약 10 개월 (2025-04 ~ 2026-02 발견).
- **증상**: API 키 한도 / 네트워크 실패로 전 row 가 empty 로 끝나도 빈 .parquet 으로 저장 → 영구 데드락 마킹 → 재시도 0.
- **원인**:
  1. fillContent 함수가 success 와 empty 를 구분 안 함
  2. 빈 본문 parquet 도 정상 산출로 인식
  3. 자동 cron 이 같은 날 재시도 시 .parquet 존재만 보고 skip
- **수정**: commit `838b7d02` (2026-05-23) — `success == 0 + 시도 > 0` 시 .parquet 승격 차단, _meta 보존.
- **재발 가드**: allFilingsCollector.py 안 안전장치 + 정기공시 docs/ 위임 동행.
- **학습**: silent 빈 산출물이 영구 데드락의 가장 큰 원인. *수치 0* vs *empty* 명시 분기 필요.

---

## 2026-05-09 — accountMappings cycle 12 회귀

- **분류**: data-quality
- **영향 범위**: accountMappings 의 1글자 suffix trim ("액", "등", "외") 정책 누락 시 cycle 회귀.
- **지속 시간**: 단일 sprint.
- **증상**: 동일 의미 account 가 다른 snakeId 로 매핑 → 횡단 분석 깨짐.
- **원인**:
  1. mapper.py 의 suffix trim 정책 명시 없이 변경
  2. 회귀 테스트 부재
- **수정**: `feedback_account_mapping_suffix_trim.md` 메모리 박음 + suffix trim 유지 강행.
- **재발 가드**: 변경 전 회귀 테스트 통과 확인 강제.
- **학습**: 매핑 정책 변경 시 1글자 suffix 같은 *작은 정책* 도 회귀 테스트 동행 필수.

---

## 2026-05-12 — autoFillNine docstring 8344 마커 도배

- **분류**: tooling-regression
- **영향 범위**: providers/ 의 894 함수 docstring 이 stub 으로 도배 → 8344 `<TODO:>` 마커 잔존.
- **지속 시간**: 단일 sprint.
- **증상**: docstring lint PASS 인데 깊이 0. 사용자 검토 부담 폭증.
- **원인**:
  1. `tests/audit/docstringAutoFillNine.py` 가 자동 stub 생성
  2. 의미 있는 내용 검증 0
- **수정**: 자동 도구 폐기 + `feedback_no_docstring_auto_sweep.md` 메모리 박음.
- **재발 가드**: docstring 9 섹션 격상은 함수 단위 수동 작성 강행.
- **학습**: 자동 sweep 은 quantity 늘리지만 quality 0. 깊이 있는 docstring 은 함수 단위 의도 필요.

---

## 2026-05-18 — codex 원격 브랜치 분기 사고

- **분류**: regression
- **영향 범위**: 43 commit 작업물이 `codex/phase-a-god-module-split` 원격 브랜치에 갇혀 폐기. master 와 분기.
- **지속 시간**: 1 세션 (~수 시간).
- **증상**: 외부 codex agent 가 원격 브랜치 생성 → 세션 시작 시 git auto-checkout → IDE master 와 분기 → 사용자 "scripts/ 가 다시 복원됐다" 인식. 충돌 누적 후 작업물 폐기.
- **원인**:
  1. 별도 브랜치/worktree 작업 금지 룰 미박힘 (당시)
  2. 세션 시작 시 git 현재 브랜치 확인 단계 없음
  3. AI 가 master 가 아닌 브랜치에서 commit 시 IDE 화면에 변경 안 보임 (사용자 visibility 0)
- **수정**:
  - `feedback_master_only.md` 메모리 박음 (master only 강행)
  - CLAUDE.md 강행규칙 "별도 브랜치 금지, 로컬 워크트리(master)에서만 작업" 박음
  - 세션 시작 시 `git branch --show-current` 자동 확인 절차
- **재발 가드**:
  - 별도 브랜치·worktree 생성 모든 형식 금지 명문화
  - CLAUDE.md 의 강행규칙으로 박힘 (위반 시 즉시 보고)
- **학습**:
  - 외부 agent 의 원격 브랜치 push 가 다음 세션의 git auto-checkout 을 통해 작업 환경을 *기본 분기* 시킬 수 있음
  - IDE 가 보는 디스크 = git HEAD = master 워크트리 가 *한 점 일치* 가 사고 표면 0 의 필수 조건

---

## 2026-05-19 — 5 section bento row 빈공간 격분

- **분류**: ui-regression
- **영향 범위**: bento dashboard 5 section split 후 row col 합 12 미달 → 카드 사이 빈공간.
- **지속 시간**: 단일 sprint.
- **증상**: 5 section split 시 7/9/6/3 카드 row 빈공간.
- **원인**:
  1. bento dashboard row col 합 = 12 강행 룰 누락
  2. 카드 추가/section split 시 col 12 배수 맞춤 검증 X
- **수정**: `feedback_row_fills_12col_no_gap.md` 메모리 박음.
- **재발 가드**: bento 모든 row col 합 12 강행 + 카드 사이즈로 12 배수 맞춤.
- **학습**: UI 룰 *미명시* 시 LLM 이 자체 추론 → 사용자 의도 깨짐.

---

## 2026-04-26 — PyPI 깨진 wheel 사고

- **분류**: release
- **영향 범위**: PyPI 0.x.y 깨진 wheel publish. 외부 사용자 install 실패.
- **지속 시간**: PyPI yank 까지 약 4 시간.
- **증상**: `pip install dartlab` 후 `import dartlab` 실패 (missing module).
- **원인**:
  1. wheel build 시 src/ layout 의 일부 폴더 누락
  2. test.pypi 검증 단계 부재
- **수정**: PyPI yank + test.pypi 검증 단계 추가 (.github/workflows/release.yml T14-4).
- **재발 가드**: release workflow 의 build → test.pypi smoke install → pypi 본 업로드 chain 강행.
- **학습**: PyPI 본 업로드는 *test.pypi 검증 후* 만 허용.

---

## 2025-XX — accountMappings.json 누락 (v0.9.11)

- **분류**: dependency
- **영향 범위**: dartlab 0.9.11 의 wheel 안 accountMappings.json 누락. mappings/* 호출 실패.
- **지속 시간**: 패치 release 까지.
- **증상**: `Company.show("IS")` 시 KeyError.
- **원인**: pyproject.toml package-data 설정 누락.
- **수정**: package-data 명시 + verifyWheel.py audit 추가 (`.github/scripts/verifyWheel.py`).
- **재발 가드**: wheel-smoke gate 가 accountMappings 포함 검증.
- **학습**: data file 포함 여부 *명시 검증* 필수. 단순 wheel 빌드만으로 보장 X.

---

## 2026-05-08 — extras 분리 룰 같은 세션 내 2 번 위반

- **분류**: tooling-regression
- **영향 범위**: `[project.optional-dependencies]` (`[viz]`/`[server]`/등) 도입 시도 2 회.
- **지속 시간**: 단일 sprint.
- **증상**: dartlab single base install 단일 SSOT 룰 위반 시도.
- **원인**: 사용자 명시 룰 미인지 + LLM 의 일반 OSS 패턴 추론.
- **수정**: `feedback_no_extras_install.md` 메모리 박음.
- **재발 가드**: pyproject `[project.optional-dependencies]` 그룹 도입 금지 강행.
- **학습**: 일반 OSS 패턴 ≠ dartlab 룰. 룰 SSOT 우선 확인.

---

## 2026-05-19 — sections chapter row 등록 4 회귀

- **분류**: data-quality
- **영향 범위**: 공시뷰어 sections 가 chapter row 와 sub-section row 모두 등록해야 catch-all 회귀 차단. 4 회귀.
- **지속 시간**: 약 1 주.
- **증상**: 2026Q1 분기보고서의 '기재하지 아니하였습니다' placeholder 가 엉뚱한 textPath 에 박힘.
- **원인**:
  1. catch-all 중복 블록이 sub-section 블록과 alias
  2. chapter row 만 등록 시 sub-section 의 unique block 손실
- **수정**: chapter content 의 block 중 sub-section line set 에 없는 unique block 만 lonely-등록.
- **재발 가드**: sections regex audit 강화 + lonely block 보존 룰.
- **학습**: 등록 정책 변경 시 *기존 unique data* 손실 가능성 검증 필수.

---

## 2026-05-21 — DART XML body.iter() 재귀 nested duplication

- **분류**: regression
- **영향 범위**: sections regex 8 commit fix 회귀. nested table duplication.
- **지속 시간**: 약 8 commit cycle.
- **증상**: DART XML 파싱 시 body.iter() 재귀 + `.//` xpath 가 nested element 중복 추출.
- **원인**:
  1. body.iter() 가 모든 descendant 순회
  2. 동시에 `.//` xpath 도 사용 → 중복 매칭
  3. regex 기반 fix 8 commit 누적
- **수정**: `feedback_xml_native_truth.md` 메모리 박음. <TITLE ATOC AASSOCNOTE> hierarchy 직접 사용 → regex 제거.
- **재발 가드**: 원본 truth 우선, 추론 대신 직접 사용.
- **학습**: regex/추론 fix 누적은 근본 원인 가린다. *원본 데이터 truth* 직접 사용이 안전.

---

## 자동화 (T1-3 후속)

### 자동 등록

다음 이벤트 발생 시 본 문서 항목 자동 추가:

1. SLO burn 5% 초과 (T1-4) → metrics workflow 가 GitHub issue + PR 자동
2. CodeQL critical 검출 → 보안 트리아지 후 항목 추가
3. CI Fast 통과율 30일 < 70% → flakyAudit (T13-2) 가 알람
4. HF dataset 5σ drift (T7-5) → dataDriftCheck 가 issue + 항목 자동

### Toc 자동 생성

`tests/audit/incidentsToc.py` (예정) 가 본 문서 ≥ 12 항목 시 상단에 ToC 자동 삽입.

---

## 관련

- 비공개 사고 (운영자↔AI): `memory/incidents.md` (L-memory)
- SLO: [SLO.md](SLO.md) (T1-4)
- metrics: T1-2 (`metrics.yml` workflow)
- 재발 가드 baseline: `tests/audit/_baselines/*.json`
- [TODO.md](../TODO.md) 부록 E T1-3 트랙
