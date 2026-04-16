"""Insert HFDataLink component into all 05-company-reports blog posts.

Pattern (consistent across 37 posts):
  - Frontmatter has `stockCode: "XXXXXX"`
  - `<script>` block imports blog components
  - Metadata blockquote `> **...**` followed by `---` separator

Actions:
  1. Add `import HFDataLink from '$lib/components/blog/HFDataLink.svelte';` to <script>
  2. Insert `<HFDataLink code="..." />` right after the metadata blockquote,
     before the first `---` separator.

Idempotent: skips files already containing HFDataLink.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2] / "blog" / "05-company-reports"

IMPORT_LINE = "import HFDataLink from '$lib/components/blog/HFDataLink.svelte';"


def process(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if "HFDataLink" in text:
        return "skip"

    m = re.search(r'^stockCode:\s*"?([0-9A-Za-z]+)"?\s*$', text, re.MULTILINE)
    if not m:
        return "no-stockcode"
    code = m.group(1)

    # 1. Add import to <script> block (before </script>)
    script_m = re.search(r"(<script>\n)(.*?)(\n</script>)", text, re.DOTALL)
    if not script_m:
        return "no-script"
    script_body = script_m.group(2)
    new_script_body = script_body.rstrip() + "\n" + IMPORT_LINE
    text = text[: script_m.start(2)] + new_script_body + text[script_m.end(2) :]

    # 2. Insert component after the metadata blockquote, before next `---`.
    # Find first `>` blockquote block after </script>, then first `---` after it.
    after_script_idx = text.index("</script>") + len("</script>")
    bq_m = re.search(r"^> \*\*.*?(?:\n>.*)*", text[after_script_idx:], re.MULTILINE)
    if not bq_m:
        return "no-blockquote"
    bq_end_abs = after_script_idx + bq_m.end()
    sep_m = re.search(r"\n---\n", text[bq_end_abs:])
    if not sep_m:
        return "no-separator"
    insert_at = bq_end_abs + sep_m.start()
    snippet = f'\n\n<HFDataLink code="{code}" />\n'
    text = text[:insert_at] + snippet + text[insert_at:]

    path.write_text(text, encoding="utf-8")
    return f"ok ({code})"


def main() -> None:
    for folder in sorted(ROOT.iterdir()):
        idx = folder / "index.md"
        if not idx.exists():
            continue
        status = process(idx)
        print(f"{folder.name}: {status}")


if __name__ == "__main__":
    main()
