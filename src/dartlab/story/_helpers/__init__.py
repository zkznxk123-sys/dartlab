"""story 8 막 builders 의 *공유 helper* — T9-5 분해 첫 단계.

builders.py 의 _unitForCurrency / _fmtAmtShort / _notesDetailBlocks 같은
순수 helper 를 이전할 폴더. 본 commit 은 *scaffold 만* — 실제 함수 이전은
별도 commit (BUILDERS_SPLIT_PLAN.md 참고).

순서:
    Commit 1 (현재) — _helpers/__init__.py + 분해 무대 마련
    Commit 2 — _notesDetailBlocks / _unitForCurrency / _fmtAmtShort 이전
    Commit 3 — builders.py 의 5 토픽 (profile/revenue/capital/liquidity/margin) 분리
    Commit 4 — builders.py 폐기 + facade
"""
