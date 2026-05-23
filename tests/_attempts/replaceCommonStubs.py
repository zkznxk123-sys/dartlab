"""auto-sweep stub 다중 파일 의미 채움.

대상: 같은 utility 함수 (splitCells, isSeparatorRow, parseAmount 등) 의 동일 stub
docstring 이 N 개 파일에 중복. 함수명별로 1 번 의미 작성 후 다중 파일에 대해
identical stub → real semantic 교체.

이는 *깊이 0 자동 sweep* 이 아님 — 기존에 박혀 있는 stub 의 의미를 사람이 한 번
작성한 뒤 적용. 새로운 placeholder 박는 행위 X.

회귀 가드: 각 파일 strip 후 AST 재파싱 검증.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# (구 docstring, 새 docstring) 매핑.
_REPLACEMENTS: dict[str, str] = {
    # splitCells — markdown table 한 행을 cell 리스트로 분할
    (
        "def splitCells(line: str) -> list[str]:\n"
        '    """splitCells — TODO 한국어 동작 설명.\n'
        "\n"
        "    Args:\n"
        "        line: 인자.\n"
        "\n"
        "    Raises:\n"
        "        없음.\n"
        "\n"
        "    Example:\n"
        "        >>> splitCells(...)\n"
        "\n"
        "    Returns:\n"
        "        <TODO: return desc> (list[str])\n"
        '    """'
    ): (
        "def splitCells(line: str) -> list[str]:\n"
        '    """markdown table 한 행을 cell 리스트로 분할 — 앞뒤 빈 cell 제거.\n'
        "\n"
        "    Args:\n"
        '        line: ``"| 셀1 | 셀2 |"`` 형식의 markdown 표 행.\n'
        "\n"
        "    Returns:\n"
        "        앞뒤 빈 cell 제거된 cell 문자열 list.\n"
        "\n"
        "    Raises:\n"
        "        없음.\n"
        "\n"
        "    Example:\n"
        '        >>> splitCells("| a | b |")\n'
        "        ['a', 'b']\n"
        '    """'
    ),
    # isSeparatorRow — markdown table separator (---) 판정
    (
        "def isSeparatorRow(line: str) -> bool:\n"
        '    """isSeparatorRow — TODO 한국어 동작 설명.\n'
        "\n"
        "    Args:\n"
        "        line: 인자.\n"
        "\n"
        "    Raises:\n"
        "        없음.\n"
        "\n"
        "    Example:\n"
        "        >>> isSeparatorRow(...)\n"
        "\n"
        "    Returns:\n"
        "        <TODO: return desc> (bool)\n"
        '    """'
    ): (
        "def isSeparatorRow(line: str) -> bool:\n"
        '    """markdown table separator row (``|---|---|`` 같은 ``-`` 만의 cell) 여부.\n'
        "\n"
        "    Args:\n"
        "        line: 표 행 문자열.\n"
        "\n"
        "    Returns:\n"
        "        모든 cell 이 ``-`` 만 으로 구성되면 True.\n"
        "\n"
        "    Raises:\n"
        "        없음.\n"
        "\n"
        "    Example:\n"
        '        >>> isSeparatorRow("|---|---|")\n'
        "        True\n"
        '    """'
    ),
}


def processFile(path: Path) -> int:
    src = path.read_text(encoding="utf-8")
    newSrc = src
    replaced = 0
    for old, new in _REPLACEMENTS.items():
        cnt = newSrc.count(old)
        if cnt:
            newSrc = newSrc.replace(old, new)
            replaced += cnt
    if replaced == 0:
        return 0
    # AST 검증
    try:
        ast.parse(newSrc)
    except SyntaxError as exc:
        print(f"SyntaxError in {path}: {exc} — revert", file=sys.stderr)
        return 0
    path.write_text(newSrc, encoding="utf-8")
    return replaced


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path("src/dartlab/providers")
    totalFiles = 0
    totalReplaced = 0
    for p in sorted(root.rglob("*.py")):
        if "__pycache__" in p.parts or "edinet" in p.parts:
            continue
        replaced = processFile(p)
        if replaced:
            totalFiles += 1
            totalReplaced += replaced
            print(f"{p}: {replaced} stub -> semantic")
    print(f"\n=== TOTAL: {totalFiles} files, {totalReplaced} replacements ===")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
