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
