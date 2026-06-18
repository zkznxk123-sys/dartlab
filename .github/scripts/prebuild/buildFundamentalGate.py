"""finance.parquet → gov/fundamental-gate.parquet (단일종목 펀더게이트 PIT 시계열).

terminal-strategy-lab W2 (간판②). 펀더게이트 = "재무가 튼튼할 때만 진입"(Piotroski≥6 등) —
가격 백테스터가 못 하는 panel moat. calcPiotroskiSeries(전 연도, _scoreOne 단일 SSOT) +
**rcept_dt(공시일 = rcept_no[:8]) PIT 앵커** join → 공시일 이후 봉부터 게이트 켜짐(계단, look-ahead 차단).

⛔ 정직 한계:
  - 커버리지 = finance.parquet **2020+** (그 이전은 게이트 null = 진입 미평가). 단일종목이라 생존편향 무관.
  - PIT 근사 = rcept_no[:8](접수일). 정정공시 별도 rcept 면 정정일 적용·아니면 "공시일 근사" 라벨.
  - 차별 = "재무를 쓴다"(TradingView request.financial 존재)가 아니라 **DART 계정정규화 + 학술팩터 사전구현**.
  - 출력은 boolean 게이트용 점수일 뿐 — 밸류에이션 판정("저평가") 아님(JUDGE=fin-stmt-lab 경계).

출력 스키마 (long-form, 1행/종목/회계연도)::

    stockCode · bsnsYear · rceptDt(YYYYMMDD 공시일·PIT 앵커) · piotroski(0~9)

실행::

    uv run python -X utf8 .github/scripts/prebuild/buildFundamentalGate.py [--skip-upload]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _hfRetry import retryHfCall  # noqa: E402

HF_REPO = "eddmpython/dartlab-data"
PATH_IN_REPO = "gov/fundamental-gate.parquet"
OUT_LOCAL = ROOT / "data" / "gov" / "fundamental-gate.parquet"
ANNUAL_REPORT_CODE = "11011"  # 사업보고서(연간) reprt_code


def _env(name: str) -> str:
    import os

    val = os.environ.get(name, "").strip()
    if val:
        return val
    envPath = ROOT / ".env"
    if envPath.exists():
        m = dict(re.findall(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", envPath.read_text(encoding="utf-8"), re.M))
        return m.get(name, "").strip().strip('"').strip("'")
    return ""


def _rceptDtByYear() -> pl.DataFrame:
    """(stockCode, bsnsYear) → rceptDt(공시일) — 연간 사업보고서 rcept_no[:8] 의 최소(최초 제출).

    finance.parquet 의 rcept_no(14자리, YYYYMMDD+seq) 첫 8자리 = 접수일 = PIT 앵커.
    정정공시는 별도 rcept_no(나중) → 최소 = 원공시일(보수적·정정 전 시점부터 게이트 켜짐 방지는 호출부).
    """
    fin = ROOT / "data" / "dart" / "scan" / "finance.parquet"
    lf = pl.scan_parquet(fin)
    df = (
        lf.select(["stockCode", "bsns_year", "reprt_code", "rcept_no"])
        .filter(pl.col("reprt_code").cast(pl.Utf8) == ANNUAL_REPORT_CODE)
        .with_columns(
            pl.col("stockCode").cast(pl.Utf8),
            pl.col("bsns_year").cast(pl.Utf8).alias("bsnsYear"),
            pl.col("rcept_no").cast(pl.Utf8).str.slice(0, 8).alias("rceptDt"),
        )
        .group_by(["stockCode", "bsnsYear"])
        .agg(pl.col("rceptDt").min())  # 최초 제출 공시일
        .collect(engine="streaming")
    )
    return df


def buildGate() -> pl.DataFrame:
    """Piotroski 시계열 + rcept_dt PIT 앵커 join → 펀더게이트 패널."""
    from dartlab.quant.alphas.piotroski import calcPiotroskiSeries

    pio = calcPiotroskiSeries(market="KR")
    if pio is None or pio.is_empty():
        raise SystemExit("[gate] Piotroski 시계열 0건")
    pio = pio.rename({"bsns_year": "bsnsYear"})
    rcept = _rceptDtByYear()
    gate = (
        pio.join(rcept, on=["stockCode", "bsnsYear"], how="inner")  # 공시일 있는 것만(PIT 앵커 필수)
        .filter(pl.col("stockCode").str.contains(r"^\d{6}$"))
        .select(["stockCode", "bsnsYear", "rceptDt", "piotroski"])
        .sort(["stockCode", "bsnsYear"])
    )
    return gate


def main() -> None:
    from dartlab.core.offlineGuard import enforceOffline

    enforceOffline()  # prebuild = offline only

    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-upload", action="store_true", help="로컬 parquet 만 생성")
    args = parser.parse_args()

    gate = buildGate()
    OUT_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    gate.write_parquet(OUT_LOCAL, compression="zstd")
    mb = OUT_LOCAL.stat().st_size / 1e6
    nStocks = gate["stockCode"].n_unique()
    print(
        f"[gate] {gate.height}행 · {nStocks}종목 · 연도 {gate['bsnsYear'].min()}~{gate['bsnsYear'].max()}"
        f" → {OUT_LOCAL} ({mb:.3f}MB)"
    )
    print(f"[gate] Piotroski≥6 비율: {gate.filter(pl.col('piotroski') >= 6).height / max(1, gate.height) * 100:.1f}%")

    if args.skip_upload:
        return
    token = _env("HF_TOKEN")
    if not token:
        raise SystemExit("[gate] HF_TOKEN 없음 — --skip-upload 로 로컬만")
    from huggingface_hub import HfApi

    retryHfCall(
        HfApi(token=token).upload_file,
        path_or_fileobj=str(OUT_LOCAL),
        path_in_repo=PATH_IN_REPO,
        repo_id=HF_REPO,
        repo_type="dataset",
        commit_message=f"갱신: fundamental-gate {gate['bsnsYear'].max()} ({gate.height}행)",
    )
    print(f"[gate] HF 업로드 → {PATH_IN_REPO}")


if __name__ == "__main__":
    main()
