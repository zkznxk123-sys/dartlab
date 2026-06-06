"""(shim) HF seed — 본체는 dartlab.pipeline.seed.seedCategoriesFromHf 로 이동.

CLI(--category / --data-dir) + GITHUB_STEP_SUMMARY 호환만 유지. 신규 코드는
``dartlab.pipeline.seedCategoriesFromHf`` 를 직접 쓴다.
"""

import argparse
import os


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--category", required=True, help="쉼표 구분 (예: finance,report,panel)")
    p.add_argument("--data-dir", default=os.environ.get("DARTLAB_DATA_DIR", "./data"))
    args = p.parse_args()

    from dartlab.pipeline.seed import seedCategoriesFromHf

    summary = seedCategoriesFromHf(args.category.split(","), dataDir=args.data_dir)
    print(f"[seed] done: {summary}")

    stepSummary = os.environ.get("GITHUB_STEP_SUMMARY")
    if stepSummary:
        with open(stepSummary, "a", encoding="utf-8") as f:
            f.write("## HF Seed\n\n| 카테고리 | 로컬 총 | 신규 다운로드 | 다운로드 크기 |\n|---|---|---|---|\n")
            for cat, (total, newCount, mb) in summary.items():
                f.write(f"| {cat} | {total} | {newCount} | {mb:.1f}MB |\n")


if __name__ == "__main__":
    main()
