# Core Loop — 자가개선 루프 운영 SSOT

**주체**: dartlab 자가개선 루프 (Observe·Pattern·Promote·Refine·Axis).
**현재**: legacy Phase O/P/R/F/A 문서. 새 AI/skills 경로의 자가개선 계약은 직접 audit 판정과 `src/dartlab/skills` 승격 상태가 기준이다.
**방향**: 이 문서는 skill promotion 과 직접 audit 운영 포인터로 축소한다. Phase 이름은 compatibility 용어이며 새 구현의 원천이 아니다.

> 상위 사상: [philosophy.md](philosophy.md) §6.

사람과 AI 가 서로 개선하는 **양방향 루프**. 새 AI 경로에서는 자동 로그가 곧바로 지식이 되지 않는다. `AuditPacket` 을 사람이 P/T/C/V로 판정하고, 그 결과가 `ImprovementCandidate`, `RegressionBank`, `RecipeBank` 로 들어간 뒤에만 docstring/capabilities/protocol/tool 개선 후보가 된다.

Mapping:

| Legacy phase | 새 계약 |
|---|---|
| O Observe | TraceEvent + AuditPacket 생성 |
| P Pattern | P verdict 기반 Recipe candidate |
| R Promote | human accepted Recipe/SSOT change |
| F Refine | C/V 기반 RegressionBank + ImprovementCandidate |
| A Axis | 수동 engine/protocol proposal |
 
새 구현은 `src/dartlab/ai/runtime/*` 를 기준으로 하지 않는다. AI production 경로는 `src/dartlab/ai` 새 Ask Workbench Kernel 이며, `ai_backup` 또는 old runtime import 는 금지한다.

---

## 1. Legacy 5 Phase — O · P · R · F · A

아래 Phase P/R/F 스크립트와 절차는 compatibility-only다.
어떤 legacy 스크립트도 직접 audit verdict 와 accepted skill/docstring 개선 후보 없이 docstring, skill, protocol, tool schema 변경을 승격할 수 없다.
새 AI 구현에서는 Phase 이름을 내부 상태로 쓰지 않는다.

| Phase | 이름 | 한 줄 명제 |
|---|---|---|
| **O** | Observe (실험) | 실사용 질문·tool 호출·응답·에러를 `data/audit/ai-ask/YYYY-MM-DD.jsonl` 에 기록 |
| **P** | Pattern (후보 감지) | 동일 `(category, tool_sequence)` N 회 성공 → docstring Guide append 초안 생성 |
| **R** | Promote (승격) | 사용자 `--confirm` → `skill/docstring-*` 브랜치 PR → CODEOWNERS 리뷰 merge |
| **F** | Refine (자가 개선) | 실패 신호 (error · extreme_flags · override 실패) → docstring "Caveats" PR |
| **A** | Axis (엔진 승격) | 반복 조합 M 회·30 일 숙성 → 공식 엔진 axis 신설 proposal (수동) |

---

## 2. Phase O — 기록 인프라

### legacy 구현 위치

- 아래 경로는 old AI runtime 기준이며 새 AI/skills 경로의 production 표준이 아니다.
- 새 구현 위치는 `src/dartlab/ai` 와 `src/dartlab/skills` 의 trace, verify, provider, MCP 계약을 따른다.
- compatibility 코드가 필요하면 새 `AuditPacket`/`ImprovementCandidate` 스키마로 어댑트한다.

### 출력

`{dataDir}/audit/ai-ask/YYYY-MM-DD.jsonl` (UTC). 한 줄 = 1 요청.

### v2 스키마

```json
{
  "schema_version": 2,
  "ts": "2026-04-25T09:30:00.000000+00:00",
  "request_id": "req-abc123",
  "question": "삼성전자 수익성 분석해줘",
  "question_hash": "sha256:a1b2c3d4e5f6...",
  "category_hash": "FIN-profitability-KR-tech",
  "stockCode_hint": "005930",
  "provider": "standard-audit-profile",
  "model": "audit-model-id",
  "tool_calls": [
    {"name": "analysis", "args": {...}, "args_hash": "...",
     "ok": true, "error": null, "duration_ms": 1823,
     "result_size_bytes": 4012, "overrides_used": null,
     "extreme_flags": []}
  ],
  "tool_sequence_hash": "seq:a1b2c3d4",
  "override_calls": [
    {"tool": "analysis", "override_keys": ["wacc"],
     "trigger": "detectExtremeFlags:wacc>0.25", "succeeded": true}
  ],
  "rounds": 2,
  "chunk_len": 1823,
  "error": null,
  "violation": null,
  "trace": {
    "selectedTools": ["analysis"],
    "skippedCandidateTools": [],
    "toolArgs": [],
    "sanitizedArgs": [],
    "evidenceIds": [],
    "claimIds": [],
    "visualIds": [],
    "processMapIds": []
  },
  "quality": {
    "qualityIssues": [],
    "processMapSatisfied": true,
    "claimSupportRate": 1.0,
    "toolArgValidRate": 1.0,
    "freshnessSatisfied": true,
    "visualSatisfied": true
  },
  "skill_used": null,
  "duration_total_ms": 4521,
  "judgment": {"verdict": null, "judged_at": null,
               "judged_by": null, "issue_code": null,
               "root_cause": null, "ssot_fix_target": null,
               "suggested_contract_delta": null, "pr_url": null}
}
```

### 안전 장치

- I/O 실패 조용 무시 (응답 경로 보호).
- `args` 값 500 자 cap + 라인 4 KB 초과 시 요약본.
- `DARTLAB_AUDIT_DISABLE=1` 환경변수 시 비활성.

### 수동 판정 환류

자동 gate 는 구조 위반을 잡는 보조 장치다. 최종 품질 판정은 서버 경유 응답 원문을 사람이 읽고 P/T/C/V 로 기록한다.

수동 T/C/V 는 `issue_code`, `root_cause`, `ssot_fix_target`, `suggested_contract_delta` 를 함께 남긴다. 같은 root cause 가 반복될 때만 Phase P/R 의 docstring/capabilities 수정 후보가 된다. 자동 violation 하나만으로 SSOT 를 바꾸지 않는다.

---

## 3. Phase P — 후보 감지

### 스크립트

`scripts/audit/extract_skill_candidates.py`

```bash
uv run dartlab-coreloop pattern --since 30d \
    --min-repeat 3 --min-unique-questions 3 --min-chunk-len 400
```

### 게이트

- `n >= min_repeat` AND `n_unique_q >= min_unique_questions` AND `success_rate == 1.0`.
- `error` · `violation` 있는 레코드 제외.

### 출력

- `data/audit/candidates/{YYYY-MM-DD}-candidates.json`
- `data/audit/candidates/{YYYY-MM-DD}-draft.md` (사람 검토용)

### 보조 근거

- `playbook` 고품질 bullet (`quality >= 0.75` AND `success_count >= 5`): `--min-repeat` 완화 2 로.
- `auditAnalysis/*.md` "엔진 개선" 섹션: `--include-audit-analysis` (dry-run 강제).

### 안전

- `--dry-run` 기본. PR 안 만듦.
- `--sanitize`: 공개 공유용 question 원문 제외.
- polars streaming 불필요 (수천~수만 라인까지 Python json 반복 충분. 대용량 시 보강).

---

## 4. Phase R — 승격

### 스크립트

`scripts/audit/promote_skill.py`

```bash
uv run dartlab-coreloop promote \
    --candidate data/audit/candidates/2026-04-25-candidates.json \
    --id cand-2026-04-25-001 --confirm
```

### 절차

1. candidate json 로드.
2. 대상 파일의 Guide 섹션에 body append (없으면 말미 주석).
3. hallucination 재현 테스트 (예시 질문 → `POST /api/ask`, seq_hash 비교).
4. git 브랜치 생성 + 커밋 + `gh pr create --draft`.

### 브랜치·커밋 규칙

- 브랜치: `skill/docstring-{engine}-{axis-slug}-{YYYYMMDD}`.
- axis slug 매핑: `scripts/audit/_axis_slug.py::KOREAN_AXIS_SLUG`.
- 커밋 subject prefix: `[CORELOOP-R]` (3 중 auto-merge 차단 대상).

### auto-merge 3 중 방어

1. `promote_skill.py` 가 `gh pr merge --auto` 호출 안 함.
2. `.github/branch_protection.yml` (별도 설정, 1 회): main 브랜치 `required_approving_review_count = 1`.
3. `.github/workflows/ai-policy.yml::block-coreloop-auto-merge` job — `[CORELOOP-` 타이틀 + `auto-merge` 라벨 동시 감지 시 라벨 제거 + fail.

### 롤백

append-only → `git revert {sha}` 한 번. 엔진 코드 불변 → behavior regression 불가.

---

## 5. Phase F — 자가 개선

### 스크립트

`scripts/audit/refine_skill.py`

```bash
uv run dartlab-coreloop refine --since 30d --min-failures 2
```

### 실패 신호

- `error` 필드 non-null
- `violation` 필드 (P8 tool zero)
- `chunk_len < 200`
- `tool_calls[].extreme_flags` triggered
- `override_calls[].succeeded == false`

### 출력

`data/audit/counterexamples/{YYYY-MM-DD}-counterexamples.json`

### 안전

- `--exclude-types transient_network,rate_limit` 로 일시적 에러 제외.
- Phase R 과 동일하게 append-only, auto-merge 금지, 재현 테스트.

---

## 6. Phase A — 축 승격 (수동)

### 스크립트 (반자동)

`scripts/audit/propose_axis.py` — proposal md 만 생성. 엔진 코드 수정 X.

```bash
uv run dartlab-coreloop propose-axis \
    --engine analysis --axis 수익성 \
    --min-phase-r-merges 3 --min-phase-f-caveats 2 --min-age-days 30
```

### 게이트 (AND)

- Phase R merge 3+
- Phase F counterexample 2+
- 첫 R merge 로부터 30 일+

### 승격 (수동)

1. proposal.md 생성 확인.
2. 사용자 + AI pair 가 엔진 코드 설계:
   - `core/overrides.py` override key 추가 (필요 시).
   - `{engine}/__init__.py` 새 axis enum 또는 공개 함수.
   - docstring 9 섹션 전부 (`ops/code.md` 규격).
   - `tests/unit/{engine}/test_axis_{slug}.py`.
3. 일반 engine PR (CORELOOP 마킹 없음 — 사람 판단 주).
4. CODEOWNERS 리뷰 → merge.

### 자동화 금지

엔진 axis 추가는 사상 수준 결정. override 오남용·축 난립 방지를 위해 사람 판단 필수.

---

## 7. 루프 끊김 3 지점 복구

### (1) 블로그 frontmatter `ai:` → `insights(source="blog")`

- **hook (실시간)**: `src/dartlab/story/publisher.py::publishReportFromCompany` 끝에 `src/dartlab/ai/persistence/blog_insights.py::upsert_ai_frontmatter_to_insights` 호출.
- **backfill (일괄)**:

```bash
uv run dartlab-coreloop backfill-blog --blog-root blog/ --confirm
```

### (2) AI bullet → 엔진 docstring PR

Phase P · R 본체가 담당. 추가로 고품질 `playbook` bullet 이 Phase P 2 차 근거.

### (3) auditAnalysis → 엔진 docstring 피드백

`scripts/audit/_parse_audit_analysis.py` + `extract_skill_candidates.py --include-audit-analysis` (dry-run 강제).

---

## 8. KnowledgeDB 정리

### 스크립트

`scripts/audit/cleanup_knowledge_db.py`

```bash
uv run python scripts/audit/cleanup_knowledge_db.py            # dry-run
uv run python scripts/audit/cleanup_knowledge_db.py --confirm  # 실제 정리
```

### 정리 기준

- `insights(source="live")` **전량 drop** (검증 게이트 없이 축적분).
- `insights(source="audit")` 중 md 파일 부재 레코드 drop.
- 남은 audit 레코드에 `evidence_ref = 'audit:data/dart/auditAnalysis/{code}.md'`, `quality_gate = 'migration'` 주입.
- `playbook` → `quality >= 0.75 AND success_count >= 5` 만 유지.
- `executions` 30 일 이전 drop + `question` → `question_hash` 치환.
- 아카이브: `data/ai/knowledge/_archive/{YYYY-MM-DD}-pre-cleanup.sqlite`.

### 재출발 이후 쓰기 조건

- `saveInsightFromResponse` → `response_length >= 500 AND grade in {P,T} AND stockCode present` 게이트.
- `curate()` playbook 쓰기 → `quality < 0.5` 면 매월 auto-prune 대상.

---

## 9. 안전 · 프라이버시 · 메모리

### sanitize

`scripts/audit/sanitize_audit.py`

```bash
# check — 민감 토큰 리포트만 (파일 미작성)
uv run dartlab-coreloop sanitize --check data/audit/ai-ask/

# hash — question → question_hash, 공개 공유용
uv run dartlab-coreloop sanitize --in data/audit/ai-ask/ --out /tmp/sanitized --mode hash

# drop — question 삭제
uv run dartlab-coreloop sanitize --in data/audit/ai-ask/ --out /tmp/sanitized --mode drop

# mask — 종목명·이메일·URL 마스킹 (블로그용)
uv run dartlab-coreloop sanitize --in data/audit/ai-ask/ --out /tmp/sanitized --mode mask
```

**원본 jsonl 은 절대 덮어쓰지 않음.**

### Docstring shape 검증

Phase R PR 후에도 9 섹션 규격 유지 체크: `tests/unit/test_docstring_shape.py` (W-J 에서 신설 예정).

### 메모리 가드

- audit jsonl 가 GB 단위로 커질 때 polars streaming (`pl.scan_ndjson` + `collect(streaming=True)`) 사용.
- `core.memory.check_memory_and_gc` 호출 지점 유지.

---

## 10. RACI · 스케줄

### RACI 매트릭스

| 작업 | 사용자 | AI pair | CI |
|---|:-:|:-:|:-:|
| Phase O 기록 | — | — | A |
| Phase P 집계 | A | C | I |
| Phase R PR | A | R | I |
| Phase F PR | R | A | I |
| Phase A 승격 | A | C | — |
| sanitize 공유 | A | — | — |
| KnowledgeDB 정리 | A | C | — |

`R`=Responsible · `A`=Accountable · `C`=Consulted · `I`=Informed.

### 자동화 로드맵

1. **M0–M1**: 전부 수동. 사용자가 주 1 회 `dartlab-coreloop pattern` 실행.
2. **M1–M3**: `.github/workflows/coreloop-pattern.yml` nightly cron. candidate/draft 자동 생성, PR 은 수동.
3. **M3+ (안정화 지표 충족 시)**: tier 1 (Guide 섹션 append 만) draft PR 자동 생성. merge 는 계속 수동.

**안정화 지표**: Phase R 연속 clean merge 30 회 · 직전 3 개월 revert 0 · docstring shape 회귀 0.

---

## 11. CLI — `dartlab-coreloop`

구현: `src/dartlab/cli/coreloop.py`. `pyproject.toml [project.scripts]` 등록.

```bash
dartlab-coreloop status                            # 현황 요약
dartlab-coreloop pattern --since 7d                # Phase P
dartlab-coreloop refine --since 30d                # Phase F
dartlab-coreloop promote --candidate <path> --id <id> --confirm   # Phase R
dartlab-coreloop propose-axis --engine analysis    # Phase A
dartlab-coreloop sanitize --mode hash              # 민감정보 마스킹
dartlab-coreloop verify --candidate <path> --id <id>              # 재현 테스트
dartlab-coreloop backfill-blog --blog-root blog/ --confirm        # 블로그 → insights
```

---

## 12. 관련 문서

- [philosophy.md](philosophy.md) §6 — 5 Phase 사상 근거
- [skills.md](skills.md) — docstring = skill 규약
- [code.md](code.md) — docstring 9 섹션 규격 (Guide · When · How · Verified · Examples)
- [ai.md](ai.md) §11 — audit 10 질문 (별개 사람 품질 검증)
- [api-contract.md](api-contract.md) — 공개 API 추가 규칙

---

## 반복 실패

- Phase A 자동화 (엔진 axis 를 코드 생성) — 사상 수준 결정이라 수동 강제.
- Phase R PR 을 `gh pr merge --auto` 로 머지 — 3 중 방어 우회 시도.
- audit jsonl 공개 전 sanitize 누락 — 사용자 질문 원문 유출.
- Phase P 집계에서 error/violation 레코드 미제외 — 실패 패턴을 "성공 skill" 로 오승격.
