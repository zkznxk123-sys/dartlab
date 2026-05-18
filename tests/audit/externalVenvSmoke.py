"""외부 venv 에 설치된 dartlab 의 8 엔진 smoke — nightly CI + 수동 실행 공용.

로컬에서 `pip install dartlab==X.Y.Z` 한 venv 내부에서 실행. 각 엔진 공개
API 를 호출해 crash / empty 검출. 실패 시 exit 1.

사용법::

    # CI (nightly): 자동으로 dartlab 설치된 venv 에서 실행
    python tests/audit/externalVenvSmoke.py

    # 로컬 수동: 특정 버전 검증
    python -m venv /tmp/smoke && /tmp/smoke/bin/pip install dartlab==0.9.19
    /tmp/smoke/bin/python tests/audit/externalVenvSmoke.py

Returns
-------
    exit 0 — 전 엔진 PASS.
    exit 1 — 하나라도 FAIL. stderr 에 상세.
    exit 2 — Company 로딩 자체 실패 (이후 엔진 skip).
"""

from __future__ import annotations

import sys
import traceback


def test(name: str, fn) -> bool:
    """fn() 실행 후 결과 None/empty 검출. PASS/FAIL 출력. 성공 여부 반환."""
    try:
        result = fn()
        ok = result is not None
        print(f"[{'OK' if ok else 'EMPTY'}] {name}: {type(result).__name__}")
        return ok
    except Exception as e:
        print(f"[FAIL] {name}: {type(e).__name__}: {e}")
        traceback.print_exc(limit=2)
        return False


def main() -> int:
    import dartlab

    print(f"dartlab version: {dartlab.__version__}")
    print(f"python: {sys.version.split()[0]}")
    print()

    results: dict[str, bool] = {}
    c = None

    # 1. Company facade
    def company():
        nonlocal c
        c = dartlab.Company("005930")
        return c

    results["Company"] = test("Company('005930')", company)
    if not c:
        print("\n[ABORT] Company 로딩 실패 — 나머지 엔진 skip", file=sys.stderr)
        return 2

    # 2. show (BS/ratios — finance accessor)
    results["show.BS"] = test("c.show('BS')", lambda: c.show("BS"))
    results["show.ratios"] = test("c.show('ratios')", lambda: c.show("ratios"))

    # 3. analysis — 가치평가 (dFV) + 종합평가
    results["analysis.valuation"] = test(
        "c.analysis('가치평가')",
        lambda: c.analysis("가치평가"),
    )
    results["analysis.synthesis"] = test(
        "c.analysis('종합평가')",
        lambda: c.analysis("종합평가"),
    )

    # 4. story
    results["story"] = test("c.story()", lambda: c.story())

    # 5. sections (docs 파이프라인)
    results["sections"] = test("c.sections", lambda: c.sections)

    # 6. macro
    results["macro"] = test("dartlab.macro()", lambda: dartlab.macro())

    # 7. industry (callable module 버그 재발 방지)
    results["industry"] = test(
        "dartlab.industry()",
        lambda: dartlab.industry(),
    )

    # 8. credit
    results["credit"] = test("c.credit()", lambda: c.credit())

    # 9. quant
    results["quant"] = test("c.quant()", lambda: c.quant())

    # 결과 요약
    print()
    print("=" * 50)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    for k, v in results.items():
        mark = "✓" if v else "✗"
        print(f"  {mark} {k}")
    print("=" * 50)
    print(f"PASSED: {passed}/{total}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
