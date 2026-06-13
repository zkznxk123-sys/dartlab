"""AST 기반 DartLab Guard Index 생성."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

LAYER_OF: dict[str, float] = {
    "core": 0.0,
    "gather": 1.0,
    "providers": 1.0,
    "scan": 1.5,
    "frame": 1.5,
    "synth": 1.5,
    "reference": 1.5,
    "analysis": 2.0,
    "macro": 2.0,
    "quant": 2.0,
    "industry": 2.0,
    "credit": 2.0,
    "simulate": 2.5,
    "story": 3.0,
    "ai": 4.0,
    "mcp": 4.0,
}

ROOT_FACADE = "__root__"


@dataclass(frozen=True)
class ImportRecord:
    """AST import 1건."""

    module: str
    topPackage: str | None
    line: int
    isTopLevel: bool

    def toDict(self) -> dict[str, Any]:
        """JSON 직렬화용 dict."""
        return asdict(self)


@dataclass(frozen=True)
class ModuleRecord:
    """파일 1개의 Guard Index record."""

    path: str
    module: str
    topPackage: str
    layer: float | None
    imports: tuple[ImportRecord, ...]

    @property
    def importModules(self) -> list[str]:
        """전체 dartlab import module 목록."""
        return sorted({item.module for item in self.imports})

    @property
    def topLevelImports(self) -> list[str]:
        """전체 top-level package import 목록."""
        return sorted({item.topPackage for item in self.imports if item.topPackage})

    def toDict(self) -> dict[str, Any]:
        """Guard Index schema module dict."""
        return {
            "path": self.path,
            "module": self.module,
            "topPackage": self.topPackage,
            "layer": self.layer,
            "imports": self.importModules,
            "topLevelImports": self.topLevelImports,
        }


def buildIndex(repoRoot: Path) -> list[ModuleRecord]:
    """src/dartlab 이하 Python 파일을 전수 AST 스캔한다."""
    srcRoot = repoRoot / "src" / "dartlab"
    if not srcRoot.exists():
        raise FileNotFoundError(f"dartlab source root not found: {srcRoot}")
    pyFiles = sorted(p for p in srcRoot.rglob("*.py") if "__pycache__" not in p.parts)
    if not pyFiles:
        raise FileNotFoundError(f"dartlab source root has no Python files: {srcRoot}")
    records: list[ModuleRecord] = []
    for pyFile in pyFiles:
        record = indexFile(repoRoot, srcRoot, pyFile)
        if record is not None:
            records.append(record)
    return records


def indexFile(repoRoot: Path, srcRoot: Path, pyFile: Path) -> ModuleRecord | None:
    """단일 파일 AST import record 생성."""
    module = moduleNameFor(srcRoot, pyFile)
    if module is None:
        return None
    if module == "dartlab":
        return None
    topPackage = module.split(".")[1]
    try:
        source = pyFile.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(pyFile))
    except (OSError, UnicodeDecodeError, SyntaxError):
        imports: tuple[ImportRecord, ...] = ()
    else:
        imports = tuple(extractImports(tree))
    relPath = pyFile.relative_to(repoRoot).as_posix()
    return ModuleRecord(
        path=relPath,
        module=module,
        topPackage=topPackage,
        layer=LAYER_OF.get(topPackage),
        imports=imports,
    )


def moduleNameFor(srcRoot: Path, pyFile: Path) -> str | None:
    """src/dartlab/x/y.py -> dartlab.x.y."""
    try:
        relPath = pyFile.relative_to(srcRoot).with_suffix("")
    except ValueError:
        return None
    parts = list(relPath.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(["dartlab", *parts])


def extractImports(tree: ast.Module) -> list[ImportRecord]:
    """AST에서 dartlab.* import를 추출한다."""
    records: list[ImportRecord] = []
    for node in ast.walk(tree):
        for module in importNames(node):
            topPackage = topPackageFor(module)
            if topPackage is None:
                continue
            records.append(
                ImportRecord(
                    module=module,
                    topPackage=topPackage,
                    line=getattr(node, "lineno", 0),
                    isTopLevel=isTopLevelNode(tree, node),
                )
            )
    return records


def importNames(node: ast.AST) -> list[str]:
    """Import/ImportFrom 노드에서 import module name을 반환한다."""
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        if node.module is None or node.level != 0:
            return []
        return [node.module]
    return []


def topPackageFor(module: str) -> str | None:
    """dartlab.x.y -> x."""
    parts = module.split(".")
    if not parts or parts[0] != "dartlab":
        return None
    if len(parts) == 1:
        return ROOT_FACADE
    return parts[1]


def isTopLevelNode(tree: ast.Module, target: ast.AST) -> bool:
    """모듈 직속 import인지 확인한다. TYPE_CHECKING 블록은 top-level로 보지 않는다."""
    for node in tree.body:
        if node is target:
            return True
        if isinstance(node, ast.If) and not isTypeCheckingGuard(node.test):
            for inner in ast.walk(node):
                if inner is target:
                    return True
    return False


def isTypeCheckingGuard(test: ast.expr) -> bool:
    """if TYPE_CHECKING / typing.TYPE_CHECKING 분기."""
    if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
        return True
    return isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"


def reverseImportClosure(records: list[ModuleRecord], changedModules: set[str]) -> set[str]:
    """변경 module을 import하는 역방향 의존 closure."""
    reverseGraph: dict[str, set[str]] = {}
    moduleNames = {record.module for record in records}
    for record in records:
        for importName in record.importModules:
            matched = {name for name in moduleNames if name == importName or name.startswith(importName + ".")}
            for target in matched:
                reverseGraph.setdefault(target, set()).add(record.module)
    seen = set(changedModules)
    stack = list(changedModules)
    while stack:
        current = stack.pop()
        for parent in reverseGraph.get(current, set()):
            if parent not in seen:
                seen.add(parent)
                stack.append(parent)
    return seen
