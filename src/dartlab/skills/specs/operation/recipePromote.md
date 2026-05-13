---
id: operation.recipePromote
title: Recipe 6-stage lifecycle + status 승급 CLI
category: operation
purpose: Recipe sub-spec 의 status frontmatter 변경은 `scripts/dev/recipe_promote.py` CLI 단독 권한. 도구 · 운영자 수동 편집 모두 금지. 6-stage (drafted→unverified→tested→verified→curated→deprecated) + scorecard 6 신호 게이트로 검토 없는 승격을 차단한다.
whenToUse:
  - recipe 승급
  - status 변경
  - "verified 로 올려"
  - "curated 마크"
  - recipe lifecycle
  - scorecard 검증
  - "deprecated 표시"
procedure:
  - 새 recipe 작성 시 status drafted 로 시작
  - validateRecipe sweep 통과 시 unverified 로 자동 승급
  - 실 데이터 fixture 동행 테스트 통과 시 tested 승급
  - 후속 시장 반응 확인 + scorecard 6 신호 통과 시 verified
  - 사람 검토 + 블로그/영상 흡수 후 curated
  - 시장 결과 부정 또는 API 변경으로 무효화 시 deprecated
  - 모든 status 변경은 recipe_promote.py CLI 경유 — 수동 frontmatter 편집 금지
examples:
  - "이 recipe verified 로 승급해줘"
  - "recipe scorecard 결과 확인"
  - "drafted 새 recipe 추가 후 lifecycle 어떻게 굴려"
  - "deprecated 마크 + 사유 추가"
expectedOutputs:
  - recipe .md frontmatter 의 status 갱신
  - scorecard 6 신호 (executionRef · tableRef · valueRef · webRef · marketResult · timeStable) 통과 기록
  - 승급/강등 이력 로그 (`recipes/_history.jsonl`)
  - 변경 commit (자동 생성 메시지)
requiredEvidence:
  - recipeId (skill id)
  - fromStatus · toStatus
  - scorecard (6 신호 boolean + 점수)
  - marketResultRef (후속 시장 반응 결과 — verified 이상 필수)
  - reviewerNote (curated 승급 시 사람 검토 코멘트)
failureModes:
  - status frontmatter 수동 편집 (CLI 우회) — git diff 에서 발견 시 reject
  - scorecard 미달인데 verified 승급 시도 (CLI 가 차단)
  - 후속 시장 반응 없이 curated 승급 (사람 검토 누락)
  - deprecated 사유 없음 (왜 무효화인지 불명)
forbidden:
  - recipe .md frontmatter status 필드 수동 편집
  - 검토 근거 없는 status 변경
  - scorecard 점수 조작 (`recipes/_history.jsonl` 직접 편집)
  - tested 건너뛰고 verified 점프
knowledgeRefs:
  - operation.coreloop
  - operation.philosophy
sourceRefs:
  - dartlab://skills/operation.recipePromote
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: unsupported
    notes: CLI 호출 필요 — 브라우저 환경 X
  pyodide:
    status: unsupported
    notes: CLI 호출 필요 — 브라우저 환경 X
status: observed
lastUpdated: "2026-05-12"
---

# Recipe 6-stage lifecycle — 검토 없는 승격 차단

## 무엇을 하나

`src/dartlab/skills/specs/recipes/**/*.md` 의 status frontmatter 는 *6 단계* lifecycle 을 거친다. 변경 권한은 `scripts/dev/recipe_promote.py` CLI 단독. AI · 도구 · 운영자 수동 편집 모두 금지. 검토 없는 recipe 승격을 차단하는 코드화된 운영 규칙이다.

배경: dartlab 의 지식 환류는 분석 실행과 커뮤니티 반응에서 나온 개선 후보를 운영자가 검토한 뒤 공식 자산에 반영하는 방식이다. recipe 도 같은 원칙을 따른다.

## 6 단계

| Status | 의미 | 승급 조건 |
|---|---|---|
| `drafted` | 신규 작성, 미검증 | validateRecipe sweep 통과 |
| `unverified` | 골격 통과, 실행 미테스트 | 실 데이터 fixture 동행 테스트 통과 |
| `tested` | 실행 OK, 시장 검증 전 | 후속 시장 반응 확인 + scorecard 6 신호 |
| `verified` | 시장 결과 양호, 검증 완료 | 사람 검토 + 블로그/영상 흡수 |
| `curated` | 사람 검토 + 콘텐츠 환류 | (안정 상태) |
| `deprecated` | 무효화 — API 변경 · 시장 결과 부정 | 사유 필수 |

## scorecard 6 신호

`tested → verified` 게이트:

1. `executionRef` — 실행 코드 ref 존재.
2. `tableRef` — 출력 표 ref 존재.
3. `valueRef` — 핵심 수치 ref 존재.
4. `webRef` — 외부 출처 (있으면).
5. `marketResult` — 후속 시장 반응 결과 ref.
6. `timeStable` — 7 일 / 30 일 / 90 일 안정성.

6 신호 *모두* 통과해야 verified.

## 공개 호출 방식

```bash
# 현재 recipe 목록 + status
uv run python -X utf8 scripts/dev/recipe_promote.py --list

# 특정 recipe 승급 (CLI 가 scorecard 검사 후 통과 시만 commit)
uv run python -X utf8 scripts/dev/recipe_promote.py \
    --id recipes.report.dailyMorningNote \
    --to tested

# verified 승급 (scorecard 6 신호 + reviewer note 필수)
uv run python -X utf8 scripts/dev/recipe_promote.py \
    --id recipes.report.dailyMorningNote \
    --to verified \
    --reviewer-note "S&P 500 30 일 reflection 결과 hit rate 72%"

# deprecated (사유 필수)
uv run python -X utf8 scripts/dev/recipe_promote.py \
    --id recipes.report.dailyMorningNote \
    --to deprecated \
    --reason "FRED API 2026-06 spec 변경으로 macroRef 갱신 불가"
```

CLI 가 자동:
- frontmatter `status` 갱신
- `recipes/_history.jsonl` append
- git commit (단일 path) — `commit -o <recipe.md> recipes/_history.jsonl` 형식

## scorecard 미달 시

```
[recipe_promote] verified 승급 차단 — scorecard 6 신호 중 2 개 미달:
  - marketResult: ref 없음 (후속 시장 반응 확인 후 재시도)
  - timeStable: 30 일 안정성 false (현재 14 일째)
```

## 자동 lint — 수동 편집 차단

`scripts/audit/recipeStatusGuard.py` 가 git diff 검사:
- frontmatter `status:` 라인 변경이 recipe_promote 가 만든 commit 인지 확인.
- 사람/AI 가 직접 편집한 commit 이면 PR reject.

## 검토 없는 승격 차단 — 왜 이 가드가 있는가

- recipe 는 실행 결과, 반례, 커뮤니티 반응, 운영자 검토가 함께 있을 때만 승격한다.
- 도구가 recipe 를 직접 verified 로 마크하면 검증 전 아이디어가 공식 실행 지식처럼 보일 수 있다.
- 본 룰은 status 변경 권한을 CLI 한 곳으로 모아 검토 근거와 승격 이력을 남긴다.

## 다음 단계

- 새 recipe 작성 → 강제 섹션 + 4 단계: [operation.skillDevelopmentLoop](/skills/operation.skillDevelopmentLoop).
- recipe scorecard 정의 + 후속 시장 반응 확인 절차: `operation.coreloop`.
- 공개 지식 환류와 커밋 방식: `operation.contributionWorkflow`.

## 무엇을 하지 *않는가*

- frontmatter `status` 수동 편집 (git diff 에서 자동 검출 reject).
- scorecard 미달 verified 승급.
- tested 건너뛰고 verified 점프.
- 검토 근거 없는 status 변경 (CLI 호출 제외 — CLI 안에서도 명시 인자 필요).

근본: `operation.coreloop` · `operation.contributionWorkflow`.
