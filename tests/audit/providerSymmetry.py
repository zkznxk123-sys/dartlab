"""provider method-level symmetry — P-PR 트랙 측정 게이트.

dart Company 의 공개 method 마다 edgar Company 동명 또는 `_SYMMETRY_MAP.rename_map` 의
대응 method 가 존재하는지 + body LoC 비대칭 (edgar/dart < 0.3 → shallow) 검증.

폴더 mirror (`folderMirror.py`) 는 strict 통과 — 본 게이트는 **method-level** 만.

`_SYMMETRY_MAP` 영구 제외 (`runtime.providerProtocol` SSOT):
    dart_only: 한국 특화 18 메서드 (codeName/keywordTrend/news/credit 등)
    edinet_deferred: 5 method (ask/quant/disclosure/liveFilings/readFiling)
    rename_map: dart_method → edgar_method (의미 동일, 이름 다른 경우)

mode:
    --mode baseline (default) — 현 missing/shallow 등록 + new violation 만 fail
    --mode strict — 전 violation fail

baseline JSON 형식:
    {"_note": "...", "missing": [...], "shallow": [...]}

P-PR6/7/8 통과마다 baseline 축소. P-PR8 종료 시 strict.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_REPO = Path(__file__).resolve().parents[2]
_DART_COMPANY = _REPO / "src" / "dartlab" / "providers" / "dart" / "company.py"
_EDGAR_COMPANY = _REPO / "src" / "dartlab" / "providers" / "edgar" / "company.py"
_BASELINE = _REPO / "tests" / "audit" / "_baselines" / "providerSymmetry.json"

# ── _SYMMETRY_MAP — runtime.providerProtocol SSOT ──

_DART_ONLY: frozenset[str] = frozenset(
    {
        # 식별자
        "codeName",
        "resolve",
        "status",
        # 시장 메타
        "listing",
        "industry",
        # 검색·뉴스
        "search",
        "keywordTrend",
        "news",
        "publicSentiment",
        # 분석 결합
        "credit",
        "marketScan",
        "watch",
        "story",
        "analysis",
        "validateStory",
        # 데이터 접근
        "gather",
        "table",
        # raw provider 접근
        "rawDocs",
        "rawFinance",
        "rawReport",
    }
)

_EDINET_DEFERRED: frozenset[str] = frozenset(
    {
        "ask",
        "quant",
        "disclosure",
        "liveFilings",
        "readFiling",
    }
)

# 의미 동일, 이름 다른 매핑 (현재 비어 있음 — 신규 매핑 발견 시 추가)
_RENAME_MAP: dict[str, str] = {}

_SHALLOW_RATIO = 0.3


def _collectPublicMethods(path: Path) -> dict[str, int]:
    """Company class 안 공개 method → body LoC (자신을 포함한 줄 수).

    클래스 안 method 만 (module-level 함수 제외). underscore/dunder/property 제외.
    """
    if not path.exists():
        return {}
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return {}
    methods: dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Company":
            for sub in node.body:
                if not isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if sub.name.startswith("_"):
                    continue
                if _isProperty(sub):
                    continue
                methods[sub.name] = _bodyLoc(sub)
    return methods


def _isProperty(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for dec in func.decorator_list:
        if isinstance(dec, ast.Name) and dec.id == "property":
            return True
        if isinstance(dec, ast.Attribute) and dec.attr in {"setter", "deleter", "getter"}:
            return True
    return False


def _bodyLoc(func: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """함수 body LoC — start_line 부터 end_line 까지."""
    end = getattr(func, "end_lineno", func.lineno)
    return max(1, end - func.lineno + 1)


def _scan() -> tuple[list[str], list[str]]:
    """dart vs edgar method 비대칭 추출 — (missing list, shallow list)."""
    dartMethods = _collectPublicMethods(_DART_COMPANY)
    edgarMethods = _collectPublicMethods(_EDGAR_COMPANY)

    missing: list[str] = []
    shallow: list[str] = []

    for dartName, dartLoc in dartMethods.items():
        if dartName in _DART_ONLY:
            continue
        # rename_map 의 대응 이름 확인
        targetName = _RENAME_MAP.get(dartName, dartName)
        if targetName not in edgarMethods:
            missing.append(f"edgar.{targetName} (dart.{dartName})")
            continue
        edgarLoc = edgarMethods[targetName]
        if dartLoc > 0 and edgarLoc / dartLoc < _SHALLOW_RATIO:
            shallow.append(f"edgar.{targetName}/{edgarLoc} vs dart.{dartName}/{dartLoc} ratio={edgarLoc / dartLoc:.2f}")

    return sorted(missing), sorted(shallow)


def _loadBaseline(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "_note": "P-PR 트랙 — method-level symmetry baseline. P-PR6/7/8 통과마다 축소.",
        "missing": [],
        "shallow": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="dart vs edgar method-level symmetry audit")
    parser.add_argument("--mode", choices=["baseline", "strict"], default="baseline")
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--baseline", default=None, help="baseline JSON path")
    args = parser.parse_args()

    baselinePath = (_REPO / args.baseline).resolve() if args.baseline else _BASELINE
    missing, shallow = _scan()

    print("=== provider method-level symmetry (P-PR 트랙) — dart vs edgar ===")
    print(f"missing: {len(missing)} 건  shallow: {len(shallow)} 건 (총 {len(missing) + len(shallow)})")
    print(f"dart_only 영구 제외: {len(_DART_ONLY)} 항목  edinet_deferred: {len(_EDINET_DEFERRED)} 항목")

    if args.update_baseline:
        baselinePath.parent.mkdir(parents=True, exist_ok=True)
        baselinePath.write_text(
            json.dumps(
                {
                    "_note": (
                        "P-PR 트랙 — method-level symmetry baseline. "
                        "P-PR6 (XBRL) / P-PR7 (10-K sections + Form 4) / P-PR8 (DEF 14A + 8-K + strict) "
                        "통과마다 missing/shallow 축소. P-PR8 종료 시 strict 0."
                    ),
                    "missing": missing,
                    "shallow": shallow,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"\nbaseline 갱신: {baselinePath.relative_to(_REPO)}")
        return 0

    if args.mode == "strict":
        if missing or shallow:
            print("\n=== STRICT FAIL ===")
            for m in missing[:10]:
                print(f"  MISSING: {m}")
            for s in shallow[:10]:
                print(f"  SHALLOW: {s}")
            return 1
        print("\n=== STRICT PASS ===")
        return 0

    # baseline 모드
    baseline = _loadBaseline(baselinePath)
    allowed_missing = set(baseline.get("missing", []))
    allowed_shallow = set(baseline.get("shallow", []))
    new_missing = [m for m in missing if m not in allowed_missing]
    new_shallow = [s for s in shallow if s not in allowed_shallow]

    if new_missing or new_shallow:
        print("\n=== baseline 외 신규 위반 ===")
        for m in new_missing[:10]:
            print(f"  NEW MISSING: {m}")
        for s in new_shallow[:10]:
            print(f"  NEW SHALLOW: {s}")
        return 1

    print("\n=== baseline 안 — 통과 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
