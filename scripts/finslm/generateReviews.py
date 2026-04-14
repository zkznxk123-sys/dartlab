"""Stage B — publishBatch로 200종목 review 마크다운 생성.

순차 실행 + gc.collect() (메모리 안전).
결과: blog/05-company-reports/ 에 마크다운 누적.
실패 종목은 skip (금융업 등).

실행:
    uv run python -X utf8 scripts/finslm/generateReviews.py

완료 후:
    uv run python -X utf8 scripts/finslm/extractReviews.py  (리뷰 → QA 변환)
"""

from __future__ import annotations

import gc
import sys
import time

from dotenv import load_dotenv

load_dotenv()


def main() -> int:
    import dartlab
    from dartlab.review.publisher import publishBatch

    print("KOSPI 시총 상위 200종목 조회...")
    try:
        df = dartlab.listing("kospi")
    except (FileNotFoundError, OSError) as e:
        print(f"listing 실패: {e}")
        return 1

    if "시가총액" in df.columns:
        df = df.sort("시가총액", descending=True)
    codes = df["종목코드"].to_list()[:200]
    print(f"{len(codes)}종목 선정")

    print(f"\npublishBatch 시작... (예상 6~8시간)")
    t0 = time.time()
    try:
        paths = publishBatch(codes)
    except KeyboardInterrupt:
        print("\n중단됨")
        return 1

    elapsed = time.time() - t0
    print(f"\n완료: {len(paths)}개 보고서 ({elapsed / 3600:.1f}시간)")
    gc.collect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
