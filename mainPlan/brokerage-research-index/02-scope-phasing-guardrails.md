# 02 — 범위 · phasing · 경계

## 1. Phase 로드맵

| Phase | 내용 | 게이트 |
|---|---|---|
| **P0 — _attempts 개념확립** | 5~6개사 스크래퍼 + URL/selector 레지스트리 + 제목→ticker. "안정적으로 제목·url·날짜·ticker 뽑히나" 실측 | 커버리지·실패패턴 README 박제 |
| **P1 — 졸업 → gather source** | `sources/brokerage/` 7파일 + `mixins/research.py::brokerageReports()` 3패턴 | 9섹션 docstring · 단위테스트 · NEVER-CLAIM grep |
| **P2 — sync 백필 + HF** | `sync/syncBrokerageReports.py`(gather 호출만) + `DATA_RELEASES` public 등록 + prebuild 직독 | 별도빌드 0 · HF 백필 검증 · 본문 호스팅 0 |
| **P3 — 채점 레이어** | 금투협 전자공시(괴리율·투자의견 비율) gather 결합 → 애널 적중률·증권사 편향 채점 | *별도 PRD/게이트* (이 인덱스는 substrate) |

P0~P2 = 이 PRD 의 핵심 영토(링크 인덱스). P3 = 차별화의 본체지만 자기 게이트로 분리(인덱스 없이 채점 불가 → 순서 고정).

## 2. 경계 (다른 영토 — 침범 금지)

- **본문 콘텐츠(PDF·전문) 생산·호스팅** = **영원히 비영토**. 우리는 메타+링크만. (00 §4·§6)
- **회사별 목표주가 컨센서스** = FnGuide 유료 독점. 무료 직수집 불가 → **범위 밖**. 필요 시 별도 유료 판단.
- **증권사 거래 API 통합**(BYO 토큰 자동투자) = **별도 제3엔진**(execution/broker). 사용자 본인 계좌·본인 토큰·로컬 실행·private/pro 후보. 이 PRD 와 데이터·법적 결이 완전히 다름 → *여기서 다루지 않음, 포인터만*.
- **채점/검증 레이어** = P3, 금투협 결합 + 자기 게이트.

## 3. Guardrails (CLAUDE.md ⛔ 정합)

- **gather 직행 금지** → `tests/_attempts/brokerageIndex/` 졸업게이트 ([[feedback_attempts_graduation_gate]]).
- **공동작업대 SSOT** → 수집=gather, sync 는 gather 호출만, prebuild=offline ([[feedback_common_workbench_ssot]]).
- **외부 본문 untrusted** → snippet `wrapExternal()` (`.claude/skills/untrusted-wrap-check`).
- **클린 모듈트리** → `__init__`/`__all__` SSOT, 덕지덕지 금지 ([[feedback_clean_module_tree]] · [[feedback_always_check_clutter]]).
- **UTF-8** → `uv run python -X utf8`.
- **테스트** → `bash tests/test-lock.sh` 경유 (Polars OOM 가드).

## 4. 착수 조건

- **착수 = 운영자 go.**
- 이 인덱스는 **공개 gather + HF public**(메타데이터 = 사실). 유료/경쟁우위는 P3 채점·제3엔진에서.
- UI(터미널 "관련 리서치" 레일) push 는 *별도* — 공개 터미널 화면 작업이라 **운영자 명시 승인 후에만** (CLAUDE.md ⛔ UI push 게이트).
