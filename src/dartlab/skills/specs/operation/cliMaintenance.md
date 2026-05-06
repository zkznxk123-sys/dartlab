---
id: operation.cliMaintenance
title: CLI 유지보수 규칙
kind: curated
scope: builtin
status: observed
category: operation
purpose: dartlab CLI 의 명령 추가·변경·폐기 절차와 stdout/stderr 분리, exit code 계약, 테스트 게이트를 정의한다. CLI 는 단일 파일이 아니라 src/dartlab/cli/ 패키지로 유지한다.
whenToUse:
  - 새 CLI 명령 추가
  - 기존 명령 옵션 변경
  - 명령 폐기 또는 별칭 처리
  - exit code 또는 출력 형식 변경
  - CLI 패키지 구조 점검
inputs:
  - 변경할 명령 또는 신규 기능
  - 변경 종류 (추가 · 수정 · 폐기)
outputs:
  - 갱신된 src/dartlab/cli/commands/ 모듈
  - 갱신된 parser 와 services
  - 테스트 (parser + execution)
  - 도움말 출력 일관성
toolRefs:
  - argparse
  - operation.stability
  - operation.testing
sourceRefs:
  - dartlab://skills/operation.cliMaintenance
  - https://github.com/eddmpython/dartlab/tree/master/src/dartlab/cli
requiredEvidence:
  - 변경된 모듈 경로
  - 테스트 통과 결과
  - exit code 일관성 확인
expectedOutputs:
  - 변경된 명령
  - 도움말 갱신
  - CHANGELOG 항목 (Tier 1 기준)
runtimeCompatibility:
  server:
    status: limited
  localPython:
    status: supported
  mcp:
    status: limited
  webAi:
    status: limited
  pyodide:
    status: unsupported
procedure:
  - src/dartlab/cli/commands/{name}.py 에 신규 명령 모듈 추가.
  - configure_parser(subparsers) 와 run(args) 분리.
  - 공유 상수는 src/dartlab/cli/context.py, 출력/환경 로직은 src/dartlab/cli/services/.
  - CLIError 로 사용자 에러 발생 (ad-hoc print 금지).
  - parser 테스트 1 개 + execution 또는 error-path 테스트 1 개 추가.
  - 폐기 시 deprecated 별칭은 마이그레이션 메시지 출력 + 테스트 보존.
  - operation.stability 의 Tier 정책에 따라 안내.
failureModes:
  - 명령에서 직접 print 로 에러 출력 (CLIError 미사용)
  - stdout 에 경고/에러 출력 (stderr 가 정답)
  - argparse 외 다른 프레임워크 즉흥 도입
  - 별도 helper 스크립트 신설 (명령 트리 확장이 정답)
  - exit code 의미 변경
forbidden:
  - exit code 0 / 1 / 2 / 130 의 의미를 변경하지 않는다.
  - 공개 명령 이름을 마이그레이션 계획 없이 바꾸지 않는다.
  - 새 명령에 테스트 없이 머지하지 않는다.
  - 별도 helper 스크립트로 명령 트리 우회하지 않는다.
examples:
  - 새 dartlab subcommand 추가
  - 기존 명령 옵션 폐기
  - CLI 출력 형식 변경
source:
  type: curated_markdown
  owner: dartlab
lastUpdated: "2026-05-06"
---

dartlab CLI 는 단일 파일이 아니라 `src/dartlab/cli/` 패키지로 유지한다.

## 규칙

- 새 명령은 `src/dartlab/cli/commands/<name>.py` 에 추가한다.
- 각 명령 모듈은 parser 등록과 실행을 분리한다.
- `configure_parser(subparsers)` 로 인자 정의, `run(args)` 로 실행.
- 공유 상수와 provider 리스트는 `src/dartlab/cli/context.py`.
- 공유 출력과 환경 로직은 `src/dartlab/cli/services/`.
- 사용자 대상 실패는 `CLIError` 로 발생 (각 명령에서 ad-hoc print 금지).
- stdout = 성공 데이터 출력. stderr = 경고/에러/deprecation.
- exit code 안정성: `0` 성공, `1` 런타임 실패, `2` 사용 에러, `130` 인터럽트.
- 명시적 마이그레이션 계획 없는 한 공개 명령 이름은 보존한다.
- Deprecated 별칭은 마이그레이션 메시지 출력 + 테스트 보존.
- 새 명령은 parser 테스트 1 + execution 또는 error-path 테스트 1.

## 현재 레이아웃

```text
src/dartlab/cli/
  __init__.py
  main.py
  parser.py
  context.py
  commands/
  services/
```

## 변경 정책

- ad-hoc helper 스크립트 신설보다 기존 명령 트리 확장 우선.
- argparse 가 기본 프레임워크. 명시적 UX rewrite 가 아닌 한 다른 프레임워크 도입 금지.
- 출력 형식 변경 시 테스트와 사용자 도움말을 같은 변경에서 갱신.
- 별칭 마이그레이션 후엔 도움말에서 숨겨도 제거 전까지 실행 가능 유지.

## 릴리즈 게이트

- 릴리즈 변경은 parser/unit 테스트 + subprocess E2E smoke 테스트 통과 필수.
- 공개 도움말 출력과 exit code 는 호환성 계약.
- `pyproject.toml` 의 script entry point 는 `dartlab.cli.main:main` 유지.
- 새 deprecation 은 `CHANGELOG.md` + 도움말 동작 테스트 반영.

## 다음 단계

- [operation.stability](/skills/operation.stability) — API tier 와 deprecation 정책.
- [operation.code](/skills/operation.code) — 코드 품질 · 독스트링 · 릴리즈.
- [operation.testing](/skills/operation.testing) — 테스트 규칙.
