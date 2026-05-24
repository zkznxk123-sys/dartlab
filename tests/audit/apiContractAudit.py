"""API contract audit — public API 3중 검증 (T8-5).

dartlab `__all__` 의 모든 public 심볼이 다음 3 조건 충족 여부 검증:

1. **docstring 존재** (9 섹션은 별도 audit T10-4) — 최소 1 줄 이상
2. **type annotation** — function 시그니처 의 매개변수/리턴 annotation 완전
3. **contract test 존재** — `tests/_contracts/test_{name}.py` 또는 `tests/contracts/` 안

baseline: `tests/audit/_baselines/apiContract.json`.
목표: Q2 80 percent → Q4 100 percent.

실행::

    uv run python -X utf8 tests/audit/apiContractAudit.py
    uv run python -X utf8 tests/audit/apiContractAudit.py --strict
    uv run python -X utf8 tests/audit/apiContractAudit.py --json
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONTRACT_DIR_CANDIDATES = [
    REPO_ROOT / "tests" / "_contracts",
    REPO_ROOT / "tests" / "contracts",
]


def loadPublicApi() -> dict[str, object]:
    """dartlab.__all__ 의 모든 심볼 dict."""
    try:
        dl = importlib.import_module("dartlab")
    except ImportError:
        return {}
    symbols = list(getattr(dl, "__all__", []))
    out: dict[str, object] = {}
    for sym in symbols:
        try:
            out[sym] = getattr(dl, sym)
        except AttributeError:
            continue
    return out


def hasDocstring(obj: object) -> bool:
    doc = inspect.getdoc(obj)
    return bool(doc) and len(doc.strip()) >= 1


def hasFullTypeAnnotation(obj: object) -> bool:
    """function/method 의 시그니처 매개변수 + 리턴 annotation 완전 여부."""
    if not (inspect.isfunction(obj) or inspect.ismethod(obj)):
        # class/module/dataclass 는 시그니처 검사 안 함 (다른 룰)
        return True
    try:
        sig = inspect.signature(obj)
    except (TypeError, ValueError):
        return True
    # self / cls 매개변수 제외
    for paramName, param in sig.parameters.items():
        if paramName in ("self", "cls"):
            continue
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            # *args / **kwargs 는 면제
            continue
        if param.annotation is inspect.Parameter.empty:
            return False
    if sig.return_annotation is inspect.Signature.empty:
        # 생성자 (__init__) 는 -> None 생략 가능
        return obj.__name__ == "__init__"
    return True


def hasContractTest(name: str) -> bool:
    """tests/_contracts/test_{name}.py 또는 contracts/ 존재."""
    for contractDir in CONTRACT_DIR_CANDIDATES:
        candidate = contractDir / f"test_{name}.py"
        if candidate.exists():
            return True
    return False


def auditApi() -> dict:
    """전체 audit 실행 — 심볼별 3 조건 통과 여부."""
    symbols = loadPublicApi()
    if not symbols:
        return {"totalSymbols": 0, "audits": {}, "summary": {}}

    audits: dict[str, dict] = {}
    for name, obj in symbols.items():
        audits[name] = {
            "kind": (
                "function"
                if inspect.isfunction(obj) or inspect.isbuiltin(obj)
                else "class"
                if inspect.isclass(obj)
                else "module"
                if inspect.ismodule(obj)
                else "attribute"
            ),
            "hasDocstring": hasDocstring(obj),
            "hasTypeAnnotation": hasFullTypeAnnotation(obj),
            "hasContractTest": hasContractTest(name),
        }

    total = len(audits)
    summary = {
        "totalSymbols": total,
        "docstringPassRate": round(sum(1 for a in audits.values() if a["hasDocstring"]) / total * 100, 1)
        if total > 0
        else 0,
        "annotationPassRate": round(sum(1 for a in audits.values() if a["hasTypeAnnotation"]) / total * 100, 1)
        if total > 0
        else 0,
        "contractTestPassRate": round(sum(1 for a in audits.values() if a["hasContractTest"]) / total * 100, 1)
        if total > 0
        else 0,
        "allThreePassRate": round(
            sum(1 for a in audits.values() if a["hasDocstring"] and a["hasTypeAnnotation"] and a["hasContractTest"])
            / total
            * 100,
            1,
        )
        if total > 0
        else 0,
    }
    return {"totalSymbols": total, "audits": audits, "summary": summary}


def main() -> int:
    parser = argparse.ArgumentParser(description="API contract audit (T8-5)")
    parser.add_argument("--strict", action="store_true", help="allThreePassRate < threshold 시 exit 2")
    parser.add_argument("--threshold", type=float, default=80.0, help="strict 임계값 (기본 80 — Q2 목표)")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    result = auditApi()
    summary = result["summary"]

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[apiContract] 공개 심볼 {result['totalSymbols']} 개")
        print(f"[apiContract] docstring: {summary['docstringPassRate']:.1f} percent")
        print(f"[apiContract] annotation: {summary['annotationPassRate']:.1f} percent")
        print(f"[apiContract] contract test: {summary['contractTestPassRate']:.1f} percent")
        print(
            f"[apiContract] 3 조건 모두 통과: {summary['allThreePassRate']:.1f} percent (임계 {args.threshold:.0f} percent)"
        )

        # 실패 심볼 상위 10
        failures = [
            (name, a)
            for name, a in result["audits"].items()
            if not (a["hasDocstring"] and a["hasTypeAnnotation"] and a["hasContractTest"])
        ]
        if failures:
            print(f"\n3 조건 미달 {len(failures)} 심볼 (상위 10):")
            for name, a in failures[:10]:
                missing = []
                if not a["hasDocstring"]:
                    missing.append("docstring")
                if not a["hasTypeAnnotation"]:
                    missing.append("annotation")
                if not a["hasContractTest"]:
                    missing.append("contract")
                print(f"  - {name} ({a['kind']}): missing {', '.join(missing)}")

    if args.strict and summary["allThreePassRate"] < args.threshold:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
