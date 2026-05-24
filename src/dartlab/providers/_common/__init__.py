"""providers/_common/ scaffold — T9-1 분해 무대.

providers/ 73K monolithic 분해 시 *공통 helper* (HTTP / XBRL / docs zip) 이전
폴더. 본 commit 은 *scaffold 만* — 실제 함수 이전은 별도 PR (10 commit 큰 리팩터).

분해 전략 (T9-1):
    Stage 1 (현재) — _common/ + 분해 트랙 문서
    Stage 2 (다음 세션) — dart/openapi 안 HTTP retry / token 로직 → _common/http.py
    Stage 3 — dart/finance / edgar/finance 공통 XBRL helper → _common/xbrl.py
    Stage 4 — docs zip 처리 → _common/docs.py
    Stage 5 — providers/__init__.py 의 lazy import 보강
    Stage 6 — importlinter 4 contract (dart/_common, edgar/_common, edinet/_common, providers)
    Stage 7 — 27 게이트 통과 + 회귀 0 검증

분해 후 목표:
    providers/dart/ ≤ 30K
    providers/edgar/ ≤ 25K
    providers/edinet/ ≤ 5K (현재)
    providers/_common/ ≤ 15K
    합산 ≤ 75K (현재 104K, -28 percent)
"""
