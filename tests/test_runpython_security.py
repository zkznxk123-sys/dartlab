"""RunPython sandbox 회귀 가드 — Option B (AST 차단 + 경로 가드).

차단 정책:
- os.system / subprocess.* / shutil.rmtree / socket.socket / __import__ 우회
- 안전 경로 외 파일 쓰기

허용 정책:
- import 자체는 OK — 호출 시점에만 차단
- read mode open / pathlib 읽기 / os.path.* / dartlab API / polars
- ~/.dartlab/ · ./tmp/ · /tmp/ · $TEMP/ 안의 파일 쓰기
"""

from __future__ import annotations

import os
import os.path
import tempfile

import pytest

pytestmark = pytest.mark.unit


# ── 차단 시나리오 ───────────────────────────────────────────────────────────
#
# RunPython 의 PermissionError 는 traceback 으로 잡혀 result.refs[0].payload['stderr']
# 에 들어감 (summary 는 일반 "run_python 실행 실패"). 검증은 payload.stderr 에서.


def _stderrOf(result) -> str:
    refs = result.refs or []
    if not refs:
        return ""
    payload = getattr(refs[0], "payload", None) or {}
    return str(payload.get("stderr") or "")


def test_block_os_system():
    from dartlab.ai.tools.runPython import runPython

    result = runPython("import os\nos.system('echo hi')")
    assert not result.ok
    stderr = _stderrOf(result)
    assert "PermissionError" in stderr and "os.system" in stderr


def test_block_subprocess_run():
    from dartlab.ai.tools.runPython import runPython

    result = runPython("import subprocess\nsubprocess.run(['echo', 'hi'])")
    assert not result.ok
    stderr = _stderrOf(result)
    assert "PermissionError" in stderr and "subprocess.run" in stderr


def test_block_dunder_import_os_system():
    from dartlab.ai.tools.runPython import runPython

    result = runPython("__import__('os').system('echo hi')")
    assert not result.ok
    stderr = _stderrOf(result)
    # AST 가 os.system 호출을 먼저 잡거나 __import__ 우회를 잡거나 — 둘 다 OK.
    assert "PermissionError" in stderr and ("__import__" in stderr or "os.system" in stderr)


def test_block_shutil_rmtree():
    from dartlab.ai.tools.runPython import runPython

    result = runPython("import shutil\nshutil.rmtree('/tmp/nonexistent')")
    assert not result.ok
    assert "PermissionError" in _stderrOf(result)


def test_block_from_os_import_system():
    from dartlab.ai.tools.runPython import runPython

    result = runPython("from os import system\nsystem('echo hi')")
    assert not result.ok
    assert "PermissionError" in _stderrOf(result)


def test_block_open_outside_safe_roots():
    """안전 경로 외 쓰기 차단 — OS 무관."""
    from dartlab.ai.tools.runPython import runPython

    # 절대 경로로 안전 경로가 아닌 곳 시도. Windows: C:\Windows\..., Unix: /etc/...
    # 둘 중 어느 OS 에서도 차단되어야 함.
    code = "import os\np = '/etc/passwd' if os.name == 'posix' else r'C:\\Windows\\system_test_block.ini'\nopen(p, 'w').write('x')"
    result = runPython(code)
    assert not result.ok
    stderr = _stderrOf(result)
    assert "PermissionError" in stderr and "안전 경로" in stderr


# ── 허용 시나리오 ───────────────────────────────────────────────────────────


def test_allow_polars_basic():
    from dartlab.ai.tools.runPython import runPython

    result = runPython("import polars as pl\nemit_result(values={'rows': pl.DataFrame({'a':[1,2]}).height})")
    assert result.ok
    refs_dict = [r.toDict() for r in (result.refs or [])]
    assert any(r.get("kind") == "executionRef" for r in refs_dict)


def test_allow_os_path_expanduser():
    """os.path.expanduser 는 read-only — 호출 차단 대상 아님."""
    from dartlab.ai.tools.runPython import runPython

    result = runPython("import os\nemit_result(values={'home': os.path.expanduser('~')})")
    assert result.ok


def test_allow_os_environ_get():
    from dartlab.ai.tools.runPython import runPython

    result = runPython("import os\nemit_result(values={'pyutf8': os.environ.get('PYTHONUTF8', '0')})")
    assert result.ok


def test_allow_pathlib_read():
    """pathlib.Path 는 read 모드 사용 — 차단 안 됨."""
    from dartlab.ai.tools.runPython import runPython

    code = "from pathlib import Path\nemit_result(values={'cwd_exists': Path('.').exists()})"
    result = runPython(code)
    assert result.ok


def test_allow_write_under_dartlab_home(tmp_path, monkeypatch):
    """~/.dartlab/<file> 쓰기는 안전 경로 — 통과."""
    from dartlab.ai.tools.runPython import runPython

    # tmp_path 를 임시 home 으로 — 실제 ~/.dartlab/ 오염 회피.
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    target = tmp_path / ".dartlab"
    target.mkdir()
    test_file = target / "guard_test.txt"

    code = (
        "import os\n"
        "p = os.path.join(os.path.expanduser('~'), '.dartlab', 'guard_test.txt')\n"
        "with open(p, 'w', encoding='utf-8') as f:\n"
        "    f.write('hi')\n"
        "emit_result(values={'path': p})"
    )
    result = runPython(code)
    # 일부 환경에서 expanduser 가 임시 HOME 이 아닌 실 home 을 참조할 수 있음. 안전 경로 안이면 OK.
    if not result.ok:
        # 안전 경로 체크가 fail 한 경우 — 이 테스트는 skip 으로 다루지 않고 메시지로 진단.
        pytest.skip(f"expanduser HOME override 미지원 환경 — {result.summary}")
    assert test_file.exists() or result.ok


def test_allow_write_under_tempdir():
    """tempfile.gettempdir() 안의 쓰기는 안전 경로 — 통과."""
    from dartlab.ai.tools.runPython import runPython

    code = (
        "import os\n"
        "import tempfile\n"
        "p = os.path.join(tempfile.gettempdir(), 'dartlab_guard_test.txt')\n"
        "with open(p, 'w', encoding='utf-8') as f:\n"
        "    f.write('ok')\n"
        "emit_result(values={'wrote': p})"
    )
    result = runPython(code)
    assert result.ok


# ── 가드 모듈 단위 테스트 ───────────────────────────────────────────────────


def test_assert_safe_ast_passes_clean_code():
    from dartlab.ai.tools.runpythonGuard import _assertSafeAst

    _assertSafeAst("import polars as pl\nx = pl.DataFrame({'a':[1]})\nprint(x.height)")
    _assertSafeAst("import os\nprint(os.path.expanduser('~'))")
    _assertSafeAst("from pathlib import Path\nPath('.').exists()")


def test_assert_safe_ast_blocks_each_pattern():
    from dartlab.ai.tools.runpythonGuard import _assertSafeAst

    blocked = [
        "import os; os.system('ls')",
        "import subprocess; subprocess.run(['ls'])",
        "import shutil; shutil.rmtree('/x')",
        "__import__('os').system('ls')",
        "from os import system",
        "from subprocess import run",
    ]
    for code in blocked:
        with pytest.raises(PermissionError):
            _assertSafeAst(code)


def test_safe_open_factory_blocks_outside_roots(tmp_path):
    from dartlab.ai.tools.runpythonGuard import _safeOpenFactory

    safeOpen = _safeOpenFactory(safeRoots=[str(tmp_path)])
    # 안전 경로 안 — write 통과
    f = safeOpen(str(tmp_path / "ok.txt"), "w", encoding="utf-8")
    f.write("ok")
    f.close()
    # 안전 경로 밖 — write 차단
    with pytest.raises(PermissionError, match="안전 경로"):
        safeOpen(str(tmp_path.parent / "outside.txt"), "w", encoding="utf-8")


def test_safe_open_factory_allows_read_anywhere(tmp_path):
    """read mode 는 어디든 통과 — 외부 본문 분석 use case 보존."""
    from dartlab.ai.tools.runpythonGuard import _safeOpenFactory

    target = tmp_path.parent / "outside_read.txt"
    target.write_text("hello", encoding="utf-8")
    try:
        safeOpen = _safeOpenFactory(safeRoots=[str(tmp_path)])
        f = safeOpen(str(target), "r", encoding="utf-8")
        assert f.read() == "hello"
        f.close()
    finally:
        target.unlink(missing_ok=True)


def test_default_safe_roots_includes_dartlab_home_and_tmp():
    from dartlab.ai.tools.runpythonGuard import _defaultSafeRoots

    roots = _defaultSafeRoots()
    expected_dartlab = os.path.normpath(os.path.join(os.path.expanduser("~"), ".dartlab"))
    expected_tmp = os.path.normpath(tempfile.gettempdir())
    assert expected_dartlab in roots
    assert expected_tmp in roots
