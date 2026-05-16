"""story SSOT -> landing/static/story/manifest.json.

GitHub Pages cannot execute Python at request time, so the web app consumes this
small manifest to follow story catalog/reportType/template changes without
duplicating section and block metadata in Svelte.
"""

from __future__ import annotations

import json
from pathlib import Path

from dartlab.story.catalog import ACT_HEADERS, listBlocks, listSections
from dartlab.story.dashboard import listDashboardQuestions
from dartlab.story.reportTypes import REPORT_TYPES
from dartlab.story.templates import STORY_TEMPLATES, TEMPLATES
from dartlab.viz.spec.intents import listVizIntents

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "landing" / "static" / "story" / "manifest.json"

EXPECTED_DASHBOARD_QUESTIONS = (
    "한눈에 결론은 무엇인가?",
    "이 회사는 무엇으로 돈을 버나?",
    "번 돈은 얼마나 남나?",
    "이익은 현금으로 바뀌나?",
    "자산과 부채 구조는 안전한가?",
    "번 돈은 어디에 묶이고 어디에 재투자되나?",
    "현재 가격은 무엇을 반영하나?",
    "보고서와 원문은 숫자를 뒷받침하나?",
)


def _section_config(section_key: str) -> dict:
    cfg = TEMPLATES.get(section_key, {})
    return {
        "keys": cfg.get("keys", []),
        "helper": cfg.get("helper", ""),
        "aiGuide": cfg.get("aiGuide", ""),
    }


def _validate_dashboard_manifest(
    dashboard_questions: list[dict],
    viz_intents: list[dict],
    valid_sections: set[str],
    valid_blocks: set[str],
) -> None:
    questions = [q.get("question") for q in dashboard_questions]
    if tuple(questions) != EXPECTED_DASHBOARD_QUESTIONS:
        raise RuntimeError(f"dashboardQuestions must be the fixed 8-question company dashboard pack. got={questions!r}")

    valid_viz = {v.get("key") for v in viz_intents}
    errors: list[str] = []
    for q in dashboard_questions:
        qid = q.get("id", "?")
        for section_key in q.get("sectionKeys", []):
            if section_key not in valid_sections:
                errors.append(f"{qid}: unknown sectionKey {section_key!r}")
        for block_key in q.get("blockKeys", []):
            if block_key not in valid_blocks:
                errors.append(f"{qid}: unknown blockKey {block_key!r}")
        for viz_key in q.get("vizKeys", []):
            if viz_key not in valid_viz:
                errors.append(f"{qid}: unknown vizKey {viz_key!r}")

    required_intent_fields = {"component", "periodMode", "compareMode", "requiredMetricIds"}
    required_components = {
        "income_trend_matrix",
        "balance_structure_trend",
        "cashflow_signed_matrix",
        "capital_allocation_bridge",
        "evidence_link_strip",
    }
    component_keys = {intent.get("component") for intent in viz_intents}
    missing_components = sorted(required_components - component_keys)
    if missing_components:
        errors.append(f"missing dashboard viz components {missing_components}")
    for intent in viz_intents:
        missing = sorted(field for field in required_intent_fields if field not in intent)
        if missing:
            errors.append(f"{intent.get('key', '?')}: missing intent fields {missing}")
        for block_key in intent.get("blockKeys", []):
            if block_key not in valid_blocks:
                errors.append(f"{intent.get('key', '?')}: unknown blockKey {block_key!r}")

    if errors:
        raise RuntimeError("Invalid dashboard manifest:\n- " + "\n- ".join(errors))


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

    dashboard_questions = listDashboardQuestions()
    viz_intents = listVizIntents()
    _validate_dashboard_manifest(
        dashboard_questions,
        viz_intents,
        {section["key"] for section in sections},
        {block["key"] for block in blocks},
    )

    manifest = {
        "schemaVersion": 2,
        "source": "dartlab.story",
        "actHeaders": {key: {"title": v[0], "question": v[1]} for key, v in ACT_HEADERS.items()},
        "sections": sections,
        "blocks": blocks,
        "reportTypes": report_types,
        "templates": templates,
        "dashboardQuestions": dashboard_questions,
        "vizIntents": viz_intents,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"story manifest: {OUT} ({len(sections)} sections, {len(blocks)} blocks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
