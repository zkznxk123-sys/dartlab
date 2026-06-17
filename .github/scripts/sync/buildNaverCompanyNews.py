"""종목별 뉴스 인덱스 빌드 + private HF push — 터미널 우측패널·이벤트레일 표시 전용.

두 트랙 머지 (좌우 분리 표시):
    - **naver (최근, 스니펫 O)**: 네이버 검색 API archive(`syncNaverNews`, forward-only). 일자별
      ``news/private/naver/KR/{YYYY-MM-DD}.parquet`` → recent.parquet 누적.
    - **gdelt (과거, 제목+링크)**: GDELT DOC 2.0 API(`gdeltDocNews`, 질의 기반·무료·~2017). 회사명
      질의 → gdeltArchive.parquet 누적. 스니펫 없음, 한국 커버리지 부분적.

private 데이터셋이라 브라우저 직독 불가(토큰 필요) → 종목코드별 작은 JSON 으로 묶어 push 하면 CF
워커(`/news?code=`)가 그 파일 하나만 read 토큰으로 읽어 반환(워커 parquet 파싱 0).

흐름 (buildAllFilingsRecent 동형 — 로컬 forward 분 + HF baseline merge 로 수렴):
    1. naver: 로컬 일자 parquet + 기존 HF recent.parquet merge → dedup(url) → 1년 trim.
    2. gdelt: DOC API 질의(올해 증분 또는 --gdelt-years backfill) + 기존 HF gdeltArchive merge → 5년 trim.
    3. 두 트랙 → 종목코드별 ``byCompany/{code}.json`` (item.track 으로 좌우 구분).
    4. recent.parquet + gdeltArchive.parquet + byCompany/*.json 한 commit 으로 private repo push.

⚠ private(언론사 저작권) — ``repoFor("newsNaver")`` = ``eddmpython/dartlab-news-private``.
공개 dartlab-data 안 감. 워커 서버사이드 read·화면 표시는 의도된 용도(공개 벌크 재배포만 금지).

Usage:
    uv run python -X utf8 .github/scripts/sync/buildNaverCompanyNews.py [--no-push] [--gdelt-years 5]
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

sys.path.insert(0, str(Path(__file__).resolve().parent))  # 동일 dir gdeltDocNews import
from gdeltDocNews import fetchGdeltDoc  # noqa: E402

_CATEGORY = "newsNaver"
_DIR = "news/private/naver"  # newsSources.naver.dir 과 일치 (drift 차단)
_RECENT_REL = f"{_DIR}/recent.parquet"
_GDELT_ARCHIVE_REL = f"{_DIR}/gdeltArchive.parquet"
_WINDOW_DAYS = 365  # naver 누적창 1년. 깊이 = start 페이징 백필(종목당 ≤1000건) + 일별 cron 누적, 1년에서 trim.
_GDELT_WINDOW_DAYS = 1825  # gdelt 누적창 5년 (DOC 인덱스 ~2017 이후).

# 표시에 쓰는 4컬럼 + dedup 키(url) + 그룹키(query). captured_at·market·enrichment 는 인덱스에 불필요.
_DISPLAY_COLS = ("date", "title", "source", "url", "description")


def _foldTrack(out: dict[str, list[dict[str, str]]], codedDf: pl.DataFrame, track: str, perCompany: int) -> None:
    """__code 보유 df → 코드별 date desc top-N item(track 태그)을 out[code] 에 누적 (in-place)."""
    if codedDf.is_empty() or "__code" not in codedDf.columns:
        return
    have = [c for c in _DISPLAY_COLS if c in codedDf.columns]
    work = (
        codedDf.select(["__code", *have])
        .with_columns(pl.col("date").cast(pl.Utf8).alias("__d"))
        .filter(pl.col("url").is_not_null() & (pl.col("url").str.len_chars() > 0))
        .unique(subset=["url"], keep="first")
        .sort("__d", descending=True)
    )
    for code in work["__code"].unique().to_list():
        sub = work.filter(pl.col("__code") == code).head(perCompany)
        items = [
            {
                "date": r.get("__d") or "",
                "title": (r.get("title") or "").strip(),
                "source": (r.get("source") or "").strip(),
                "url": r.get("url") or "",
                "description": (r.get("description") or "").strip(),
                "track": track,
            }
            for r in sub.iter_rows(named=True)
        ]
        if items:
            out.setdefault(str(code), []).extend(items)


def buildCompanyIndex(
    naverDf: pl.DataFrame, nameToCode: dict[str, str], *, gdeltDf: pl.DataFrame | None = None, perCompany: int = 2000
) -> dict[str, list[dict[str, str]]]:
    """두 트랙 뉴스 → 종목코드별 리스트 (순수 변환, HF 무의존). item.track 으로 좌우 구분.

    Sig: ``buildCompanyIndex(naverDf, nameToCode, *, gdeltDf=None, perCompany=300) -> dict[code, list[item]]``

    naver: query(=회사명)→코드 매핑 후 track='naver'. gdelt: __code 보유(DOC fetcher)라 그대로 track='gdelt'.
    트랙별 각각 top-N. item = {date, title, source, url, description, track}.

    Args:
        naverDf: 네이버 archive(query + _DISPLAY_COLS). date 는 pl.Date 또는 Utf8.
        nameToCode: 회사명 → 종목코드(6자리). naver query 매핑용.
        gdeltDf: GDELT DOC archive(__code + _DISPLAY_COLS). None/빈 df 면 gdelt 트랙 생략.
        perCompany: 트랙별 코드당 최대 항목 수.

    Returns:
        dict[code, list[item]] — 뉴스 있는 코드만(naver+gdelt 합). 빈 입력은 {}.
    """
    out: dict[str, list[dict[str, str]]] = {}
    if not naverDf.is_empty() and nameToCode and {"query", "url", "date"} <= set(naverDf.columns):
        mapDf = pl.DataFrame({"query": list(nameToCode.keys()), "__code": list(nameToCode.values())})
        coded = naverDf.join(mapDf, on="query", how="inner")  # inner = 회사 시드 행만
        _foldTrack(out, coded, "naver", perCompany)
    if gdeltDf is not None and not gdeltDf.is_empty():
        _foldTrack(out, gdeltDf, "gdelt", perCompany)
    return out


def _nameToCode() -> dict[str, str]:
    """회사명 → 종목코드 매핑. KRX listing(getKrxList, 가볍고 신뢰) 우선 — _stockSeedKR 와 동일 원천.

    시드(_stockSeedKR)와 같은 codeName 문자열을 써야 query→code 폴딩이 일치한다. getKrxList 는
    단일 KRX JSON 호출(short_code 6자리 = ISU_CD canonical)이라 OHLCV 패널 전체를 받는
    loadFiltered 보다 빠르고 CI 에서 빈 매핑으로 죽지 않는다. KRX API 차단 시만 loadFiltered 폴백.
    """
    # 1차 — KRX listing (시드와 동일 원천, 가볍고 신뢰).
    try:
        from dartlab.gather.krx.listing.krxList import getKrxList

        kdf = getKrxList()
        if kdf is not None and not kdf.is_empty() and "codeName" in kdf.columns and "short_code" in kdf.columns:
            out: dict[str, str] = {}
            for r in kdf.iter_rows(named=True):
                nm, cd = r.get("codeName"), r.get("short_code")
                if nm and cd:
                    out[str(nm)] = str(cd).strip()  # short_code = 6자리 canonical
            if out:
                return out
    except Exception as exc:  # noqa: BLE001 — KRX API 차단 시 loadFiltered 폴백.
        print(f"[warn] KRX listing 매핑 실패: {exc} — loadFiltered 폴백", file=sys.stderr)

    # 2차 — 시총 패널 (무겁지만 listing 부재 시 최후 수단).
    try:
        from dartlab.gather.bulkData.hfBulk import loadFiltered

        df = loadFiltered(adjustment="raw")
    except Exception as exc:  # noqa: BLE001 — listing 부재 시 매핑 0 (회사 인덱스 비게 됨, 무해)
        print(f"[warn] KRX listing 로드 실패: {exc} — 매핑 0", file=sys.stderr)
        return {}
    if df is None or df.is_empty() or "ISU_NM" not in df.columns or "ISU_CD" not in df.columns:
        return {}
    recent = df.sort("BAS_DD", descending=True).group_by("ISU_CD").agg(pl.col("ISU_NM").first())
    out2: dict[str, str] = {}
    for r in recent.iter_rows(named=True):
        nm, cd = r.get("ISU_NM"), r.get("ISU_CD")
        if nm and cd:
            out2[str(nm)] = str(cd).strip()  # ISU_CD = 6자리 canonical (gov-price-migration 정규화)
    return out2


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


def _hfFrame(token: str, relPath: str) -> pl.DataFrame | None:
    """기존 HF parquet (있으면) — CI 증분 merge 의 baseline. private 라 토큰 다운로드. 전체 컬럼 read."""
    if not token:
        return None
    try:
        from huggingface_hub import hf_hub_download

        from dartlab.core.hfRetry import retryHfCall

        path = retryHfCall(
            hf_hub_download, repo_id=repoFor(_CATEGORY), filename=relPath, repo_type="dataset", token=token
        )
        return pl.read_parquet(path)
    except Exception:  # noqa: BLE001 — 최초 빌드(파일 부재)·실패면 None(로컬/신규 분만으로 진행)
        return None


def _trimSort(out: pl.DataFrame, windowDays: int) -> pl.DataFrame:
    """url dedup + 최근 windowDays trim + date desc."""
    out = out.unique(subset=["url"], keep="first")
    maxd = out["date"].max()
    if maxd is not None:
        out = out.filter(pl.col("date") >= maxd - timedelta(days=windowDays))
    return out.sort("date", descending=True)


def buildNaverRecent(token: str) -> pl.DataFrame:
    """naver 트랙 — 로컬 일자분 + 기존 HF recent merge → trim. 없으면 빈 df."""
    frames = _localFrames()
    base = _hfFrame(token, _RECENT_REL)
    if base is not None:
        frames.append(base.select([c for c in NEWS_BASE_COLS if c in base.columns]))
    if not frames:
        return pl.DataFrame()
    return _trimSort(pl.concat(frames, how="diagonal_relaxed"), _WINDOW_DAYS)


def buildGdeltArchive(
    token: str, nameToCode: dict[str, str], *, years: int, budgetSec: float | None = None
) -> pl.DataFrame:
    """gdelt 트랙 — DOC API 신규 질의(시간예산 내) + 기존 HF gdeltArchive merge → trim. __code 보존. 없으면 빈 df.

    전 종목(~2800)은 한 job 에 다 못 도니 budgetSec 로 끊고, 기존 archive 와 누적 merge 해 매 run 커버 확대.
    """
    if not nameToCode:
        return pl.DataFrame()
    new = fetchGdeltDoc(nameToCode, years=years, budgetSec=budgetSec)
    base = _hfFrame(token, _GDELT_ARCHIVE_REL)
    frames = [f for f in (new, base) if f is not None and not f.is_empty()]
    if not frames:
        return pl.DataFrame()
    return _trimSort(pl.concat(frames, how="diagonal_relaxed"), _GDELT_WINDOW_DAYS)


def _writeArtifacts(
    naverOut: pl.DataFrame, gdeltOut: pl.DataFrame, nameToCode: dict[str, str], perCompany: int
) -> tuple[dict[str, Path], dict[str, Path]]:
    """recent/gdeltArchive parquet + byCompany json 로컬 작성. 반환 = ({relPath: path}, {code: jsonPath})."""
    dataDir = Path("data") / _DIR
    (dataDir / "byCompany").mkdir(parents=True, exist_ok=True)
    parquets: dict[str, Path] = {}
    if not naverOut.is_empty():
        p = dataDir / "recent.parquet"
        naverOut.write_parquet(p, compression="zstd", row_group_size=20_000)
        parquets[_RECENT_REL] = p
    if not gdeltOut.is_empty():
        p = dataDir / "gdeltArchive.parquet"
        gdeltOut.write_parquet(p, compression="zstd", row_group_size=20_000)
        parquets[_GDELT_ARCHIVE_REL] = p

    index = buildCompanyIndex(naverOut, nameToCode, gdeltDf=gdeltOut, perCompany=perCompany)
    jsonPaths: dict[str, Path] = {}
    for code, items in index.items():
        asOf = max((it["date"] for it in items), default="")
        p = dataDir / "byCompany" / f"{code}.json"
        p.write_text(json.dumps({"code": code, "asOf": asOf, "items": items}, ensure_ascii=False), encoding="utf-8")
        jsonPaths[code] = p
    print(
        f"[build] naver {naverOut.height:,} · gdelt {gdeltOut.height:,} rows → byCompany {len(jsonPaths)} 종목 "
        f"(naver+gdelt 머지, track 좌우구분)"
    )
    return parquets, jsonPaths


def push(token: str, parquets: dict[str, Path], jsonPaths: dict[str, Path]) -> None:
    from huggingface_hub import CommitOperationAdd, HfApi

    from dartlab.core.hfRetry import retryHfCall

    api = HfApi(token=token)
    ops = [CommitOperationAdd(path_in_repo=rel, path_or_fileobj=str(p)) for rel, p in sorted(parquets.items())]
    for code, p in sorted(jsonPaths.items()):
        ops.append(CommitOperationAdd(path_in_repo=f"{_DIR}/byCompany/{code}.json", path_or_fileobj=str(p)))
    retryHfCall(
        api.create_commit,
        repo_id=repoFor(_CATEGORY),
        repo_type="dataset",
        operations=ops,
        commit_message=f"company news: naver recent + gdelt archive + byCompany {len(jsonPaths)} 종목",
    )
    print(f"[HF↑] pushed {len(parquets)} parquet + {len(jsonPaths)} byCompany json → {repoFor(_CATEGORY)}")


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
    ap = argparse.ArgumentParser(description="종목별 뉴스 인덱스(naver+gdelt) 빌드 + private HF push")
    ap.add_argument("--no-push", action="store_true", help="빌드만, HF push 생략")
    ap.add_argument(
        "--per-company",
        type=int,
        default=2000,
        help="트랙별 종목당 최대 뉴스 건수(안전 backstop — 실데이터는 수집창·DOC 250/질의 한계로 그 아래에서 자연 수렴)",
    )
    ap.add_argument("--gdelt-years", type=int, default=1, help="GDELT DOC 질의 연도 수(1=올해 증분, 5=과거 backfill)")
    # GDELT 는 한국 종목 커버리지 사실상 0(실측: 삼성 2년 0건) + rate limit 5초/회 → daily 기본 OFF(opt-in).
    ap.add_argument(
        "--gdelt-budget-min", type=float, default=0.0, help="GDELT fetch 시간예산(분). 0=skip(기본·한국 커버리지 0)"
    )
    args = ap.parse_args(argv)

    token = _resolveToken()
    canPush = (not args.no_push) and bool(token)
    nameToCode = _nameToCode()
    naverOut = buildNaverRecent(token)

    # Phase 1 — naver byCompany 즉시 빌드+push (gdelt 무관·빠름). GDELT 가 느리거나 timeout 나도 naver 는 항상 라이브.
    if not naverOut.is_empty():
        p1, j1 = _writeArtifacts(naverOut, pl.DataFrame(), nameToCode, args.per_company)
        if canPush:
            push(token, p1, j1)
        print(f"[phase1] naver byCompany {len(j1)} 종목 {'push' if canPush else 'build'} 완료")

    # Phase 2 — gdelt 시간예산 내 best-effort → 병합 재빌드+push (누적이라 매 run 커버 확대).
    gdeltOut = buildGdeltArchive(token, nameToCode, years=args.gdelt_years, budgetSec=args.gdelt_budget_min * 60)
    if not gdeltOut.is_empty():
        p2, j2 = _writeArtifacts(naverOut, gdeltOut, nameToCode, args.per_company)
        if canPush:
            push(token, p2, j2)
        print(f"[phase2] naver+gdelt byCompany {len(j2)} 종목 {'push' if canPush else 'build'} 완료")

    if naverOut.is_empty() and gdeltOut.is_empty():
        print("naver·gdelt 양쪽 데이터 0 — syncNaverNews 또는 GDELT 질의 먼저", file=sys.stderr)
        return 0
    if not token:
        print("[HF↑] HF_TOKEN 없음 — push skip (빌드만 완료)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
