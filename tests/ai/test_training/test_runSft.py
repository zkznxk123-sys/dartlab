"""runSft SFT 학습 trigger 단위 — 마스터 플랜 v2 트랙 8 PR-T5.

dry-run + argparse + 의존성 검사. 실 학습 호출 0 (GPU/ML 의존성 미요구).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dartlab.ai.training.runSft import _checkFtExtraInstalled, _parseArgs, main, runSftTraining

pytestmark = pytest.mark.unit


def _mkSftDataset(tmp_path: Path, n: int = 3) -> Path:
    out = tmp_path / "sft.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for i in range(n):
            sample = {
                "messages": [
                    {"role": "system", "content": "sys"},
                    {"role": "user", "content": f"Q{i}"},
                    {"role": "assistant", "content": f"A{i} long answer text sample sample sample"},
                ]
            }
            fh.write(json.dumps(sample, ensure_ascii=False) + "\n")
    return out


def test_runSftTraining_dry_run_returns_dataset_size(tmp_path: Path) -> None:
    ds = _mkSftDataset(tmp_path, n=5)
    stats = runSftTraining(datasetPath=ds, outDir=tmp_path / "out", dryRun=True)
    assert stats["dryRun"] is True
    assert stats["datasetSize"] == 5
    assert stats["adapterPath"] is None


def test_runSftTraining_dry_run_includes_ft_status(tmp_path: Path) -> None:
    ds = _mkSftDataset(tmp_path)
    stats = runSftTraining(datasetPath=ds, outDir=tmp_path / "out", dryRun=True)
    assert "ftInstalled" in stats
    assert "missingPackages" in stats
    # 본 테스트 환경에 [ft] 가 미설치 → ftInstalled=False 가정 (회귀 0)
    if not stats["ftInstalled"]:
        assert len(stats["missingPackages"]) > 0


def test_runSftTraining_missing_dataset_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="dataset 누락"):
        runSftTraining(datasetPath=tmp_path / "nonexistent.jsonl", outDir=tmp_path / "out")


def test_runSftTraining_default_base_model(tmp_path: Path) -> None:
    """기본 base model = Qwen2.5-7B-Instruct (PR-T4 ledger 1 순위)."""
    ds = _mkSftDataset(tmp_path)
    stats = runSftTraining(datasetPath=ds, outDir=tmp_path / "out", dryRun=True)
    assert stats["baseModel"] == "Qwen/Qwen2.5-7B-Instruct"


def test_runSftTraining_raises_when_ft_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """[ft] extra 미설치 + dryRun=False → RuntimeError."""
    monkeypatch.setattr(
        "dartlab.ai.training.runSft._checkFtExtraInstalled",
        lambda: (False, ["transformers"]),
    )
    ds = _mkSftDataset(tmp_path)
    with pytest.raises(RuntimeError, match="\\[ft\\] extra 미설치"):
        runSftTraining(datasetPath=ds, outDir=tmp_path / "out", dryRun=False)


def test_checkFtExtraInstalled_returns_tuple() -> None:
    ok, missing = _checkFtExtraInstalled()
    assert isinstance(ok, bool)
    assert isinstance(missing, list)


def test_parseArgs_required_args() -> None:
    args = _parseArgs(["--dataset", "data.jsonl", "--out", "models/v1"])
    assert args.dataset == "data.jsonl"
    assert args.out == "models/v1"
    assert args.base_model == "Qwen/Qwen2.5-7B-Instruct"
    assert args.dry_run is False
    assert args.epochs == 1


def test_parseArgs_dry_run_flag() -> None:
    args = _parseArgs(["--dataset", "x.jsonl", "--out", "out", "--dry-run"])
    assert args.dry_run is True


def test_parseArgs_no_4bit_flag() -> None:
    args = _parseArgs(["--dataset", "x.jsonl", "--out", "out", "--no-4bit"])
    assert args.no_4bit is True


def test_main_returns_2_on_missing_dataset(tmp_path: Path) -> None:
    rc = main(["--dataset", str(tmp_path / "missing.jsonl"), "--out", str(tmp_path), "--dry-run"])
    assert rc == 2


def test_main_dry_run_succeeds(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    ds = _mkSftDataset(tmp_path)
    rc = main(["--dataset", str(ds), "--out", str(tmp_path / "out"), "--dry-run"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "dryRun" in captured.out or "datasetSize" in captured.out


def test_main_returns_1_on_ft_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "dartlab.ai.training.runSft._checkFtExtraInstalled",
        lambda: (False, ["transformers", "peft"]),
    )
    ds = _mkSftDataset(tmp_path)
    rc = main(["--dataset", str(ds), "--out", str(tmp_path / "out")])
    assert rc == 1


def test_runSft_no_top_level_ml_imports() -> None:
    """import 만으로 transformers / peft / trl 활성화 안 됨 (lazy import 가드)."""
    import sys

    import dartlab.ai.training.runSft  # noqa: F401

    assert "transformers" not in sys.modules
    assert "peft" not in sys.modules
    assert "trl" not in sys.modules
