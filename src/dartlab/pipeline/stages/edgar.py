"""EDGAR stage — daily 벌크(companyfacts.zip) + 분기 데이터셋(sub/pre/tag) 동형.

edgarSync 의 daily core 2 스텝(inline python)을 충실 재현 — companyfacts bulk
download+convert + 최신 4 분기 discover/download/convert. force 플래그는 env
EDGAR_FORCE_COMPANYFACTS/EDGAR_FORCE_QUARTERLY. (docs/panel/scan 은 조건부·별 캐시라
별 스텝 유지.) build 만(로컬 parquet) — HF deploy 는 별 스텝.
"""

from __future__ import annotations

import os

from dartlab.pipeline.types import PipelineMode, StageResult


def _fourQuarters(year: int, quarter: int) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for i in range(4):
        q, y = quarter - i, year
        while q <= 0:
            q += 4
            y -= 1
        out.append((y, q))
    return out


def runEdgar(
    *, category: str = "edgar", mode: PipelineMode = "recent", codes=None, upload: bool = True, token=None
) -> StageResult:
    """EDGAR daily 벌크 + 분기 데이터셋 — providers.edgar.bulk(gather 위임) 동형 호출.

    Args:
        category: 카테고리 라벨.
        mode: 미사용.
        codes: 미사용.
        upload: True 면 companyfacts 변경분(detectChanged)만 ``edgar/finance`` 로 HF 증분
            발행. 분기 벌크(meta)는 별 스텝/deploy 가 담당.
        token: HF 토큰(uploadCategoryToHf 위임, None=env).

    Returns:
        StageResult (bulk/quarterly 부분 실패는 격리 기록).

    Raises:
        없음.

    Example:
        >>> runEdgar()  # doctest: +SKIP
        StageResult(category='edgar', ...)
    """
    from dartlab.providers.edgar.bulk import (
        convertBulkToParquets,
        convertQuarterlyToParquets,
        discoverLatestQuarter,
        downloadCompanyfactsBulk,
        downloadQuarterlyDataset,
        listLocalQuarters,
    )

    res = StageResult(category="edgar")

    # 1. daily 벌크: companyfacts.zip → {cik}.parquet (변경분만 증분 + HF 발행)
    #    브라우저 터미널은 HF 직독이라 edgar/finance 도 미러 필요 — detectChanged 로 그날 공시한
    #    회사만 올린다(16,600 전체 재업로드 회피). deploy.py 의 옛 "finance HF 미러링 없음" 정책은
    #    백엔드(사용자 PC 자동 다운로드) 전용 가정 — 퍼블릭 패리티엔 본 스텝이 finance 를 발행.
    try:
        forceCf = os.environ.get("EDGAR_FORCE_COMPANYFACTS") == "true"
        zipPath = downloadCompanyfactsBulk(force=forceCf, progress=False)
        print(f"[pipeline] edgar companyfacts zip: {zipPath}", flush=True)
        stat = convertBulkToParquets(zipPath=zipPath, progress=False, detectChanged=True)
        print(f"[pipeline] edgar convert: {stat}", flush=True)
        changedFin = stat.get("changed") or []
        if changedFin:
            from dartlab.pipeline.changed import writeChanged

            writeChanged("edgar", changedFin)
            if upload:
                from dartlab.pipeline.hfUpload import uploadCategoryToHf

                n = uploadCategoryToHf("edgar", changedFiles=changedFin, token=token)
                print(f"[pipeline] edgar finance HF 발행: {n}개 (변경분)", flush=True)
        res.report.ok += 1
    except Exception as exc:  # noqa: BLE001 — bulk 실패 격리(quarterly 진행)
        res.report.err += 1
        res.report.failures.append(f"companyfacts: {type(exc).__name__}: {exc}")
        print(f"[pipeline] edgar companyfacts 실패(격리): {exc}", flush=True)

    # 2. 분기 벌크: 최신 4 분기 discover/download/convert
    try:
        forceQ = os.environ.get("EDGAR_FORCE_QUARTERLY") == "true"
        latest = discoverLatestQuarter()
        if latest is None:
            print("[pipeline] edgar 분기 감지 실패 — skip", flush=True)
            res.report.skip += 1
        else:
            have = set(listLocalQuarters(kind="sub"))
            for y, q in _fourQuarters(*latest):
                if not forceQ and (y, q) in have:
                    continue
                zp = downloadQuarterlyDataset(y, q, force=forceQ)
                if zp is None:
                    print(f"[pipeline] edgar {y}Q{q} 다운로드 실패", flush=True)
                    continue
                print(
                    f"[pipeline] edgar {y}Q{q}: {list(convertQuarterlyToParquets(y, q, zipPath=zp).keys())}", flush=True
                )
            res.report.ok += 1
    except Exception as exc:  # noqa: BLE001 — quarterly 실패 격리
        res.report.err += 1
        res.report.failures.append(f"quarterly: {type(exc).__name__}: {exc}")
        print(f"[pipeline] edgar quarterly 실패(격리): {exc}", flush=True)

    return res
