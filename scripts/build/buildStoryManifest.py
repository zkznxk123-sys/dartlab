"""story SSOT -> landing/static/story/manifest.json.

GitHub Pages cannot execute Python at request time, so the web app consumes this
small manifest to follow story catalog/reportType/template changes without
duplicating section and block metadata in Svelte.
"""

from __future__ import annotations

import json
from pathlib import Path

from dartlab.story.catalog import ACT_HEADERS, listBlocks, listSections
from dartlab.story.reportTypes import REPORT_TYPES
from dartlab.story.templates import STORY_TEMPLATES, TEMPLATES

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "landing" / "static" / "story" / "manifest.json"


def _section_config(section_key: str) -> dict:
    cfg = TEMPLATES.get(section_key, {})
    return {
        "keys": cfg.get("keys", []),
        "helper": cfg.get("helper", ""),
        "aiGuide": cfg.get("aiGuide", ""),
    }


def main() -> int:
    sections = []
    for sec in listSections():
        sections.append(
            {
                "key": sec.key,
                "partId": sec.partId,
                "title": sec.title,
                "act": sec.act,
                **_section_config(sec.key),
            }
        )

    blocks = [
        {
            "key": block.key,
            "label": block.label,
            "section": block.section,
            "description": block.description,
        }
        for block in listBlocks()
    ]

    report_types = {
        key: {
            "key": rt.key,
            "label": rt.label,
            "description": rt.description,
            "sectionOrder": list(rt.sectionOrder),
            "emphasize": sorted(rt.emphasize),
            "focusQuestions": list(rt.focusQuestions),
            "detail": rt.detail,
        }
        for key, rt in REPORT_TYPES.items()
    }

    templates = {
        key: {
            "description": value.get("description", ""),
            "emphasize": sorted(value.get("emphasize", [])),
            "keyQuestions": list(value.get("keyQuestions", [])),
            "actFocus": value.get("actFocus", {}),
        }
        for key, value in STORY_TEMPLATES.items()
    }

    manifest = {
        "schemaVersion": 1,
        "source": "dartlab.story",
        "actHeaders": {key: {"title": v[0], "question": v[1]} for key, v in ACT_HEADERS.items()},
        "sections": sections,
        "blocks": blocks,
        "reportTypes": report_types,
        "templates": templates,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"story manifest: {OUT} ({len(sections)} sections, {len(blocks)} blocks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
