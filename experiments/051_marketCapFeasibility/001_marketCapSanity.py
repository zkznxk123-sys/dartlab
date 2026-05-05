"""실험 ID: 051
실험명: gather.marketCap 시총 인프라 sanity check

목적:
- quant Phase 2 A1 (시총 인프라 부재) 이슈 재평가.
- gather.marketCap 이 이미 단일 종목 시총 합성을 제공하는지 실측.
- Grinold/Kahn 흡수 (IC/IR) 시 필요한 시총 시계열이 충분한지 판정.

가설:
1. gather.marketCapSnapshot("005930") 이 marketCap > 0 정합 값 반환
2. gather.marketCap("005930") 이 최근 1년 이상 (최소 200 영업일) 시계열 반환
3. US 경로 (AAPL) 도 동일 정합 — EDGAR sharesOutstanding.parquet 유무 따라 N/A 허용

방법:
1. dartlab.gather.marketCap 로부터 marketCap, marketCapSnapshot import
2. 삼성전자 "005930" 로 호출 → row 수, date 범위, marketCap 정합성 확인
3. 결과 출력 + 판정

실험일: 2026-04-15
"""

from __future__ import annotations

import sys
import traceback


def runKr() -> dict:
    """KR 시총 sanity."""
    from dartlab.gather.marketCap import marketCap, marketCapSnapshot
    snap = marketCapSnapshot("005930")
    df = marketCap("005930")
    if snap is None or df is None:
        return {"market": "KR", "ok": False, "reason": "snapshot or df None"}
    return {
        "market": "KR",
        "ok": snap["marketCap"] > 0 and df.height >= 200,
        "snapshot": {
            "date": str(snap["date"]),
            "close": snap["close"],
            "marketCap_trillion_krw": snap["marketCap"] / 1e12,
            "commonOutstanding": snap["commonOutstanding"],
        },
        "timeseries": {
            "rows": df.height,
            "dateMin": str(df["date"].min()),
            "dateMax": str(df["date"].max()),
            "marketCapNonNull": int(df.drop_nulls("marketCap").height),
        },
    }


def runUs() -> dict:
    """US 시총 sanity (데이터 없으면 N/A)."""
    try:
        from dartlab.gather.marketCap import marketCapSnapshot
        snap = marketCapSnapshot("AAPL")
        if snap is None:
            return {"market": "US", "ok": None, "reason": "snapshot None (edgar sharesOutstanding 미구축 가능)"}
        return {
            "market": "US",
            "ok": snap["marketCap"] > 0,
            "snapshot": {
                "date": str(snap["date"]),
                "close": snap["close"],
                "marketCap_trillion_usd": snap["marketCap"] / 1e12,
            },
        }
    except (ImportError, FileNotFoundError, KeyError) as e:
        return {"market": "US", "ok": None, "reason": f"{type(e).__name__}: {e}"}


def main() -> int:
    print("=" * 60)
    print("실험 051: marketCap feasibility")
    print("=" * 60)
    try:
        kr = runKr()
        print(f"KR 결과: {kr}")
    except Exception as e:
        kr = {"market": "KR", "ok": False, "error": f"{type(e).__name__}: {e}"}
        print(f"KR 예외: {kr}")
        traceback.print_exc()

    try:
        us = runUs()
        print(f"US 결과: {us}")
    except Exception as e:
        us = {"market": "US", "ok": None, "error": f"{type(e).__name__}: {e}"}
        print(f"US 예외: {us}")

    print("-" * 60)
    verdict = "통과" if kr.get("ok") else "기각"
    print(f"판정: {verdict}")
    return 0 if kr.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())


"""결과 (2026-04-15 실행):

KR 결과 (삼성전자 005930):
- snapshot date: 2026-04-15, close: 211,000원
- marketCap: 1,249조원 (1.249e15)
- commonOutstanding: 5,919,637,922 주
- timeseries rows: 244 (2025-04-15 ~ 2026-04-15)
- marketCapNonNull: 244 (결손 0)

US 결과 (AAPL):
- snapshot None — data/edgar/scan/sharesOutstanding.parquet 미구축
- EDGAR 경로 시총 합성 별도 트랙 필요

판정: 통과 (KR 한정)

결론:
1. gather.marketCap 은 KR 단일 종목 시총 시계열을 안정 제공. IC/IR 계산에 충분.
2. 기존 Phase 2 A1 우려 ("시총 인프라 부재")는 KR 에 한해 해소됨.
3. US는 sharesOutstanding.parquet 신규 빌드가 선결. 본 흡수 작업(B1) 은 KR 우선 진행,
   US는 EDGAR 경로 미구축 주석 + 후속 작업으로 분리.
4. Grinold/Kahn IC/IR 흡수 KR 한정으로 진행 가능 — 덕지덕지 추가 인프라 없이.
"""
