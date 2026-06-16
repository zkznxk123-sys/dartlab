"""종목별 뉴스 인덱스 빌드 + private HF push — 터미널 우측패널·이벤트레일 표시 전용.

네이버 뉴스 archive 는 일자별 ``news/private/naver/KR/{YYYY-MM-DD}.parquet`` 로 샤딩돼
있어(`syncNaverNews`), 브라우저(정적 터미널)가 종목별로 보려면 수십 일치 파일을 스캔해야 한다.
게다가 private 데이터셋이라 브라우저 직독 불가(토큰 필요). → 운영자/CI 에서 **종목코드별 작은
JSON** 으로 미리 묶어 push 하면, CF 워커(`/news?code=`)가 그 파일 하나만 read 토큰으로 읽어
반환한다(워커는 parquet 파싱 0 — "의존성 0 순수 fetch" 설계 유지).

흐름 (buildAllFilingsRecent 동형 — 로컬 forward 분 + HF baseline merge 로 수렴):
    1. 로컬 일자 parquet + 기존 HF ``recent.parquet`` merge → dedup(url) → 최근 180일 trim.
    2. ``recent.parquet`` 단일 누적 파일 push (다음 cron 의 baseline — ephemeral CI 에서도 이력 누적).
    3. query(=회사명) → 종목코드 매핑(KRX listing) → 코드별 최근 40건 ``byCompany/{code}.json``.
    4. recent.parquet + byCompany/*.json 한 commit 으로 private repo push.

⚠ private(언론사 저작권) — ``repoFor("newsNaver")`` = ``eddmpython/dartlab-news-private``.
공개 dartlab-data 안 감. 워커 서버사이드 read·화면 표시는 의도된 용도(공개 벌크 재배포만 금지).

Usage:
    uv run python -X utf8 .github/scripts/sync/buildNaverCompanyNews.py [--no-push] [--per-company 40]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import timedelta
from pathlib import Path

import polars as pl

import dartlab.config as _cfg
from dartlab.core.dataConfig import repoFor
from dartlab.gather.sources.newsSchema import NEWS_BASE_COLS

_CATEGORY = "newsNaver"
_DIR = "news/private/naver"  # newsSources.naver.dir 과 일치 (drift 차단)
_RECENT_REL = f"{_DIR}/recent.parquet"
_WINDOW_DAYS = 180  # 뉴스는 신선도 감쇠 — 6개월 윈도(과거 dot 완결성보다 표시 관련성 우선). filings 와 정책 다름.

# 표시에 쓰는 4컬럼 + dedup 키(url) + 그룹키(query). captured_at·market·enrichment 는 인덱스에 불필요.
_DISPLAY_COLS = ("date", "title", "source", "url", "description")


def buildCompanyIndex(
    df: pl.DataFrame, nameToCode: dict[str, str], *, perCompany: int = 40
) -> dict[str, list[dict[str, str]]]:
    """뉴스 archive(query=회사명) → 종목코드별 최근 뉴스 리스트 (순수 변환, HF 무의존).

    Sig: ``buildCompanyIndex(df, nameToCode, *, perCompany=40) -> dict[code, list[item]]``

    회사 시드(query 가 nameToCode 에 있는 행)만 채택 — 매크로 키워드 query 는 종목 귀속 불가라 제외.
    코드별 date 내림차순 top-N, url dedup. item = {date(YYYY-MM-DD), title, source, url, description}.

    Args:
        df: NEWS_ARCHIVE 스키마 일부(최소 query + _DISPLAY_COLS). date 는 pl.Date 또는 Utf8.
        nameToCode: 회사명 → 종목코드(6자리) 매핑.
        perCompany: 코드당 최대 항목 수.

    Returns:
        dict[code, list[item]] — 뉴스 있는 코드만. 빈 입력·미매칭은 {}.
    """
    if df.is_empty() or not nameToCode:
        return {}
    have = [c for c in _DISPLAY_COLS if c in df.columns]
    if "query" not in df.columns or "url" not in df.columns or "date" not in df.columns:
        return {}
    mapDf = pl.DataFrame({"query": list(nameToCode.keys()), "__code": list(nameToCode.values())})
    work = (
        df.select(["query", *have])
        .join(mapDf, on="query", how="inner")  # inner = 회사 시드 행만
        .with_columns(pl.col("date").cast(pl.Utf8).alias("__d"))
        .filter(pl.col("url").is_not_null() & (pl.col("url").str.len_chars() > 0))
        .unique(subset=["url"], keep="first")
        .sort("__d", descending=True)  # 전역 내림차순 → 코드별 head = 최신
    )
    out: dict[str, list[dict[str, str]]] = {}
    for code in work["__code"].unique().to_list():
        sub = work.filter(pl.col("__code") == code).head(perCompany)
        items: list[dict[str, str]] = []
        for r in sub.iter_rows(named=True):
            items.append(
                {
                    "date": r.get("__d") or "",
                    "title": (r.get("title") or "").strip(),
                    "source": (r.get("source") or "").strip(),
                    "url": r.get("url") or "",
                    "description": (r.get("description") or "").strip(),
                }
            )
        if items:
            out[str(code)] = items
    return out


def _nameToCode() -> dict[str, str]:
    """KRX listing 최근 1일 → 회사명(ISU_NM) → 종목코드(ISU_CD) 매핑. _stockSeedKR 와 동일 원천."""
    try:
        from dartlab.gather.bulkData.hfBulk import loadFiltered

        df = loadFiltered(adjustment="raw")
    except Exception as exc:  # noqa: BLE001 — listing 부재 시 매핑 0 (회사 인덱스 비게 됨, 무해)
        print(f"[warn] KRX listing 로드 실패: {exc} — 매핑 0", file=sys.stderr)
        return {}
    if df is None or df.is_empty() or "ISU_NM" not in df.columns or "ISU_CD" not in df.columns:
        return {}
    recent = df.sort("BAS_DD", descending=True).group_by("ISU_CD").agg(pl.col("ISU_NM").first())
    out: dict[str, str] = {}
    for r in recent.iter_rows(named=True):
        nm, cd = r.get("ISU_NM"), r.get("ISU_CD")
        if nm and cd:
            out[str(nm)] = str(cd).strip()  # ISU_CD = 6자리 canonical (gov-price-migration 정규화)
    return out


def _localFrames() -> list[pl.DataFrame]:
    base = Path("data") / _DIR / "KR"
    frames: list[pl.DataFrame] = []
    if not base.exists():
        return frames
    for f in sorted(base.glob("*.parquet")):
        if f.stem == "recent":
            continue
        try:
            schema = pl.read_parquet_schema(f)
            cols = [c for c in NEWS_BASE_COLS if c in schema]
            if cols:
                frames.append(pl.read_parquet(f, columns=cols))
        except Exception:  # noqa: BLE001 — 손상 파일 격리
            continue
    return frames


def _hfBaseFrame(token: str) -> pl.DataFrame | None:
    """기존 HF recent.parquet (있으면) — CI 증분 merge 의 baseline. private 라 토큰 다운로드."""
    if not token:
        return None
    try:
        from huggingface_hub import hf_hub_download

        from dartlab.core.hfRetry import retryHfCall

        path = retryHfCall(
            hf_hub_download,
            repo_id=repoFor(_CATEGORY),
            filename=_RECENT_REL,
            repo_type="dataset",
            token=token,
        )
        schema = pl.read_parquet_schema(path)
        return pl.read_parquet(path, columns=[c for c in NEWS_BASE_COLS if c in schema])
    except Exception:  # noqa: BLE001 — 최초 빌드(파일 부재)·실패면 None(로컬 분만으로 진행)
        return None


def build(token: str, *, windowDays: int = _WINDOW_DAYS) -> pl.DataFrame:
    """로컬 일자분 + 기존 HF recent merge → dedup(url) → 최근 windowDays trim → date desc."""
    frames = _localFrames()
    base = _hfBaseFrame(token)
    if base is not None:
        frames.append(base)
    if not frames:
        raise SystemExit("로컬·HF 어느쪽도 naver news parquet 없음 — syncNaverNews 먼저")
    out = pl.concat(frames, how="diagonal_relaxed").unique(subset=["url"], keep="first")
    maxd = out["date"].max()
    if maxd is not None:
        cutoff = maxd - timedelta(days=windowDays)
        out = out.filter(pl.col("date") >= cutoff)
    return out.sort("date", descending=True)


def _writeArtifacts(out: pl.DataFrame, perCompany: int) -> tuple[Path, dict[str, Path]]:
    """recent.parquet + byCompany/{code}.json 로컬 작성. 반환 = (recentPath, {code: jsonPath})."""
    dataDir = Path("data") / _DIR
    dataDir.mkdir(parents=True, exist_ok=True)
    recentPath = dataDir / "recent.parquet"
    out.write_parquet(recentPath, compression="zstd", row_group_size=20_000)

    index = buildCompanyIndex(out, _nameToCode(), perCompany=perCompany)
    byDir = dataDir / "byCompany"
    byDir.mkdir(parents=True, exist_ok=True)
    jsonPaths: dict[str, Path] = {}
    for code, items in index.items():
        payload = {"code": code, "asOf": items[0]["date"] if items else "", "items": items}
        p = byDir / f"{code}.json"
        p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        jsonPaths[code] = p
    print(
        f"[build] recent {out.height:,} rows ({out['date'].min()}~{out['date'].max()}) "
        f"→ {recentPath.stat().st_size / 1e6:.2f} MB · byCompany {len(jsonPaths)} 종목"
    )
    return recentPath, jsonPaths


def push(token: str, recentPath: Path, jsonPaths: dict[str, Path]) -> None:
    from huggingface_hub import CommitOperationAdd, HfApi

    from dartlab.core.hfRetry import retryHfCall

    api = HfApi(token=token)
    ops = [CommitOperationAdd(path_in_repo=_RECENT_REL, path_or_fileobj=str(recentPath))]
    for code, p in sorted(jsonPaths.items()):
        ops.append(CommitOperationAdd(path_in_repo=f"{_DIR}/byCompany/{code}.json", path_or_fileobj=str(p)))
    retryHfCall(
        api.create_commit,
        repo_id=repoFor(_CATEGORY),
        repo_type="dataset",
        operations=ops,
        commit_message=f"naver news: recent 누적 + byCompany {len(jsonPaths)} 종목 인덱스",
    )
    print(f"[HF↑] pushed recent.parquet + {len(jsonPaths)} byCompany json → {repoFor(_CATEGORY)}")


def _resolveToken() -> str:
    token = os.environ.get("HF_TOKEN", "")
    if token:
        return token
    envp = Path(_cfg.__file__).resolve().parents[2] / ".env"
    if envp.exists():
        for line in envp.read_text(encoding="utf-8").splitlines():
            if line.startswith("HF_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="종목별 뉴스 인덱스 빌드 + private HF push")
    ap.add_argument("--no-push", action="store_true", help="빌드만, HF push 생략")
    ap.add_argument("--per-company", type=int, default=40, help="종목당 최대 뉴스 건수")
    args = ap.parse_args(argv)

    token = _resolveToken()
    out = build(token)
    recentPath, jsonPaths = _writeArtifacts(out, args.per_company)
    if args.no_push:
        return 0
    if not token:
        print("[HF↑] HF_TOKEN 없음 — push skip (빌드만 완료)", file=sys.stderr)
        return 1
    push(token, recentPath, jsonPaths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
