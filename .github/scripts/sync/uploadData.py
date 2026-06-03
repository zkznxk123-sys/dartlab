"""(shim) HF 업로드 — 본체는 dartlab.pipeline.hfUpload.uploadCategoryToHf 로 이동.

CLI(--target hf/gh) + SYNC_CATEGORY env 호환만 유지. GitHub Releases(--target gh)는
2026-04-08 폐지(no-op). 신규 코드는 ``python -m dartlab.pipeline ...`` 또는
``dartlab.pipeline.uploadCategoryToHf`` 를 직접 쓴다.
"""

import argparse
import os


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, choices=["hf", "gh"])
    args = parser.parse_args()

    if args.target == "gh":
        print("[uploadData] GitHub Releases 업로드는 폐지됨(2026-04-08, HF만 유지) — skip")
        return

    category = os.environ.get("SYNC_CATEGORY", "finance")
    if "DARTLAB_DATA_DIR" not in os.environ:
        os.environ["DARTLAB_DATA_DIR"] = os.path.join(os.getcwd(), "data")

    from dartlab.pipeline.hfUpload import uploadCategoryToHf

    uploadCategoryToHf(category)


if __name__ == "__main__":
    main()
