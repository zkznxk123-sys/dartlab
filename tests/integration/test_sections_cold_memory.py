"""sections artifact 콜드 + 메모리 회귀 가드 (plan v4 §6.4).

정량 게이트:
    - sectionsLazy(periods=[X]).filter().select().collect() < 1s 콜드 (Windows 1000ms).
    - 위 패턴 RSS 증분 < 80MB (dartlab import 포함, 실 데이터 RSS < 10MB).

fresh subprocess 측정 — in-memory polars cache 0 강제. dartlab import 비용
(~70MB) 포함하므로 RSS threshold 80MB.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import dartlab.config as _cfg

_BASELINE_CODE = "005930"


def _sectionsDir(code: str) -> Path:
    return Path(_cfg.dataDir) / "dart" / "sections" / code


def _runFreshSubprocess(code: str, periodKey: str, topic: str) -> dict:
    """fresh python subprocess 에서 cold sectionsLazy 측정."""
    script = (
        f"import time, psutil, os, polars as pl; "
        f"os.environ['DARTLAB_NO_HF_DOWNLOAD']='1'; "
        f"p=psutil.Process(os.getpid()); r0=p.memory_info().rss; "
        f"from dartlab import Company; "
        f"c=Company('{code}'); "
        f"t=time.perf_counter(); "
        f"lf=c.sectionsLazy(periods=['{periodKey}']); "
        f"df=lf.filter(pl.col('topic')=='{topic}').select(['topic','content_raw']).collect(); "
        f"dt=time.perf_counter()-t; r1=p.memory_info().rss; "
        f"print(f'{{dt:.4f}}|{{r1-r0}}|{{df.height}}')"
    )
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", script],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    out = result.stdout.strip().splitlines()[-1]
    walls, rss, height = out.split("|")
    return {"wall_s": float(walls), "rss_bytes": int(rss), "rows": int(height)}


@pytest.mark.integration
def testSectionsLazyColdUnder1s() -> None:
    """sectionsLazy(periods=[X]).filter().select().collect() < 1s 콜드."""
    if not _sectionsDir(_BASELINE_CODE).exists():
        pytest.skip(f"{_BASELINE_CODE} sections artifact 부재")
    result = _runFreshSubprocess(_BASELINE_CODE, "2026Q1", "productService")
    assert result["wall_s"] < 1.0, f"sectionsLazy cold {result['wall_s']:.3f}s >= 1.0s — 회귀"


@pytest.mark.integration
def testSectionsLazyMemoryUnder80mb() -> None:
    """sectionsLazy 패턴 RSS 증분 < 80MB (dartlab import 70MB + 실 데이터 10MB)."""
    if not _sectionsDir(_BASELINE_CODE).exists():
        pytest.skip(f"{_BASELINE_CODE} sections artifact 부재")
    result = _runFreshSubprocess(_BASELINE_CODE, "2026Q1", "productService")
    rssMb = result["rss_bytes"] / 1e6
    assert rssMb < 80.0, f"sectionsLazy RSS {rssMb:.1f}MB >= 80MB — 회귀"
