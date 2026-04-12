"""Generate Flux background image for an SNS carousel hook card.

Reads  dartlab-sns/posts/<post>/hook.json   (fluxPrompt field)
Writes dartlab-sns/posts/<post>/flux/bg-hook.webp
Also writes a copy into remotion-sns/public/<post>/bg-hook.webp  so the
HookCard can reference it via staticFile("<post>/bg-hook.webp").

Usage:
  python scripts/sns/generate_flux.py --post 001-018880-hanon-systems

hook.json must contain a top-level string "fluxPrompt" describing the
image. If absent, this script prints a friendly message and exits 0.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

try:
    import replicate  # noqa: F401
except ImportError:
    print("replicate not installed. pip install replicate", file=sys.stderr)
    sys.exit(1)

import replicate  # type: ignore


ROOT = Path(__file__).resolve().parents[2]
MODEL = "black-forest-labs/flux-1.1-pro"


def generate(prompt: str, out_path: Path) -> None:
    print(f"  → flux generate: {out_path.name}", flush=True)
    for attempt in range(5):
        try:
            output = replicate.run(
                MODEL,
                input={
                    "prompt": prompt,
                    "aspect_ratio": "4:5",
                    "output_format": "webp",
                    "output_quality": 90,
                    "safety_tolerance": 5,
                },
            )
            data = urllib.request.urlopen(str(output)).read()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(data)
            print(f"    OK ({len(data) // 1024} KB)", flush=True)
            return
        except Exception as exc:  # noqa: BLE001
            if "429" in str(exc):
                wait = 15 * (attempt + 1)
                print(f"    rate limit {wait}s ...", flush=True)
                time.sleep(wait)
            else:
                print(f"    ERROR: {exc}", flush=True)
                return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--post", required=True, help="post folder name")
    parser.add_argument(
        "--force",
        action="store_true",
        help="regenerate even if flux/bg-hook.webp exists",
    )
    args = parser.parse_args()

    post_dir = ROOT / "dartlab-sns" / "posts" / args.post
    hook_file = post_dir / "hook.json"
    if not hook_file.exists():
        print(f"missing {hook_file}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(hook_file.read_text(encoding="utf-8"))
    prompt = data.get("fluxPrompt")
    if not prompt:
        print("no fluxPrompt in hook.json — skipping flux generation")
        sys.exit(0)

    out_flux = post_dir / "flux" / "bg-hook.webp"
    if out_flux.exists() and not args.force:
        print(f"already exists: {out_flux}")
    else:
        generate(prompt, out_flux)

    # mirror into remotion public dir so HookCard can pick it up
    public_copy = (
        ROOT / "scripts" / "sns" / "remotion-sns" / "public" / args.post / "bg-hook.webp"
    )
    if out_flux.exists():
        public_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out_flux, public_copy)
        print(f"  mirrored → {public_copy.relative_to(ROOT)}")

        # patch hook.json bgImage reference so HookCard consumes it
        if data.get("bgImage") != f"{args.post}/bg-hook.webp":
            data["bgImage"] = f"{args.post}/bg-hook.webp"
            hook_file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print("  updated hook.json bgImage")


if __name__ == "__main__":
    main()
