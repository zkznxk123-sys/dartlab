"""Loader and search utilities for the generated DartLab Intelligence Pack."""

from __future__ import annotations

import json
import re
from importlib import resources
from typing import Any

PACK_SCHEMA_VERSION = 1


def loadIntelligencePack() -> dict[str, Any]:
    """Load the bundled Intelligence Pack.

    The pack is a generated artifact.  Runtime code may consume it, but must not
    treat it as the rule source; docstrings/capabilities/AIContract remain SSOT.
    """
    try:
        text = resources.files("dartlab.ai.intelligence").joinpath("pack.json").read_text(encoding="utf-8")
        pack = json.loads(text)
    except (FileNotFoundError, ModuleNotFoundError, json.JSONDecodeError, OSError) as exc:
        return _fallback_pack(f"unavailable: {exc}")

    if not isinstance(pack, dict):
        return _fallback_pack("invalid pack payload")
    if pack.get("schemaVersion") != PACK_SCHEMA_VERSION:
        out = dict(pack)
        out["available"] = False
        out["stale"] = True
        out["error"] = f"unsupported schemaVersion: {pack.get('schemaVersion')!r}"
        return out
    if not pack.get("sourceHash") or not pack.get("generatedAt"):
        out = dict(pack)
        out["available"] = False
        out["stale"] = True
        out["error"] = "missing sourceHash/generatedAt"
        return out
    out = dict(pack)
    out["available"] = True
    return out


def packSummary(pack: dict[str, Any] | None = None) -> dict[str, Any]:
    pack = pack or loadIntelligencePack()
    return _drop_empty(
        {
            "available": bool(pack.get("available")),
            "schemaVersion": pack.get("schemaVersion"),
            "generatedAt": pack.get("generatedAt"),
            "sourceHash": pack.get("sourceHash"),
            "error": pack.get("error"),
            "apiCount": len(pack.get("apiMap") or []),
            "capabilityCount": len(pack.get("capabilitySkillMap") or []),
            "processCount": len(pack.get("processMap") or {}),
            "datasetCount": len(pack.get("dataCatalog") or []),
            "recipeCount": len((pack.get("recipeMap") or {}).get("recipes") or []),
        }
    )


def searchIntelligencePack(query: str, *, kind: str = "any", limit: int = 10) -> list[dict[str, Any]]:
    """Search the generated pack with a compact deterministic score."""
    terms = _terms(query)
    if not terms:
        return []
    pack = loadIntelligencePack()
    if not pack.get("available"):
        return []

    limit = max(1, min(int(limit or 10), 50))
    rows = _index_pack(pack)
    out: list[dict[str, Any]] = []
    for row in rows:
        if not _kind_allowed(row, kind):
            continue
        score = _score_row(row, terms, query)
        if score <= 0:
            continue
        out.append(
            _drop_empty(
                {
                    **row,
                    "score": score + float(row.get("baseScore") or 0),
                    "packSchemaVersion": pack.get("schemaVersion"),
                    "packSourceHash": pack.get("sourceHash"),
                }
            )
        )
    out.sort(key=lambda item: (-float(item.get("score") or 0), str(item.get("path") or "")))
    return out[:limit]


def _fallback_pack(reason: str) -> dict[str, Any]:
    return {
        "available": False,
        "schemaVersion": PACK_SCHEMA_VERSION,
        "sourceHash": "unavailable",
        "generatedAt": None,
        "error": reason,
    }


def _index_pack(pack: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "path": "intelligence-pack://architecture",
            "kind": "intelligence.architecture",
            "summary": pack.get("name") or "DartLab Financial Workspace Agent",
            "detail": " ".join(pack.get("officialAgentTools") or []),
            "baseScore": 0.5,
        }
    ]
    for item in pack.get("apiMap") or []:
        rows.append(
            {
                "path": f"intelligence-pack://api/{item.get('name')}",
                "kind": "capability",
                "summary": item.get("summary") or item.get("name"),
                "detail": " ".join(str(item.get(key) or "") for key in ("name", "apiRef", "kind", "guide")),
                "baseScore": 0.6,
            }
        )
    for item in pack.get("capabilitySkillMap") or []:
        rows.append(
            {
                "path": f"intelligence-pack://capability/{item.get('key')}",
                "kind": "capability.skill",
                "summary": item.get("summary") or item.get("key"),
                "detail": _join_values(
                    item,
                    (
                        "key",
                        "apiRef",
                        "contractId",
                        "whenToUse",
                        "questionTypes",
                        "requiredInputs",
                        "outputShape",
                        "dataColumns",
                        "freshness",
                        "commonCalculations",
                        "verification",
                        "visualPolicy",
                        "failureModes",
                        "badUses",
                    ),
                ),
                "baseScore": 0.9,
            }
        )
    for process_id, process in (pack.get("processMap") or {}).items():
        rows.append(
            {
                "path": f"intelligence-pack://process/{process_id}",
                "kind": "intelligence.process",
                "summary": process.get("summary") or process.get("questionType") or process_id,
                "detail": _join_values(
                    process,
                    (
                        "questionType",
                        "requiredTools",
                        "requiredEvidence",
                        "requiredArtifacts",
                        "requiredVisuals",
                        "freshness",
                        "failurePolicy",
                        "acceptanceCriteria",
                    ),
                ),
                "baseScore": 1.0,
            }
        )
    for item in pack.get("dataCatalog") or []:
        rows.append(
            {
                "path": item.get("path") or f"intelligence-pack://data/{item.get('datasetId')}",
                "kind": "data",
                "summary": item.get("datasetId"),
                "detail": _join_values(
                    item,
                    (
                        "datasetId",
                        "path",
                        "latestDateColumn",
                        "entityColumns",
                        "metricCandidates",
                        "universe",
                        "freshness",
                    ),
                ),
                "baseScore": 1.2,
            }
        )
    for recipe in (pack.get("recipeMap") or {}).get("recipes") or []:
        rows.append(
            {
                "path": f"intelligence-pack://recipe/{recipe.get('id')}",
                "kind": "intelligence.recipe",
                "summary": recipe.get("summary") or recipe.get("id"),
                "detail": _join_values(recipe, ("questionType", "steps", "evidence", "visuals")),
                "baseScore": 1.4,
            }
        )
    return rows


def _kind_allowed(row: dict[str, Any], kind: str) -> bool:
    if kind in {"", "any", None}:
        return True
    row_kind = str(row.get("kind") or "")
    if kind == "capabilities":
        return row_kind.startswith("capability") or row_kind.startswith("intelligence.")
    if kind == "data":
        return row_kind == "data"
    return row_kind == kind or row_kind.endswith(f".{kind}")


def _score_row(row: dict[str, Any], terms: list[str], query: str) -> float:
    haystack = " ".join(str(row.get(key) or "") for key in ("path", "kind", "summary", "detail")).lower()
    path = str(row.get("path") or "").lower()
    q = (query or "").lower()
    score = 0.0
    for term in terms:
        if term in path:
            score += 3.0
        if term in haystack:
            score += 1.0
    if q and q in haystack:
        score += 4.0
    if any(token in q for token in ("지수", "index", "indices")) and "krx.indices" in haystack:
        score += 9.0
    if any(token in q for token in ("지수", "index", "indices")) and "krx.prices" in haystack:
        score -= 3.0
    if any(token in q for token in ("주가", "가격", "상승", "오른", "price")) and "krx.prices" in haystack:
        score += 5.0
    if any(token in q for token in ("공시", "filing", "disclosure")) and "dart" in haystack:
        score += 4.0
    if row.get("deprecated") or row.get("stale"):
        score -= 2.0
    return score


def _terms(query: str) -> list[str]:
    q = (query or "").lower()
    aliases: list[str] = []
    if any(word in q for word in ("지수", "index", "indices", "kospi", "kosdaq")):
        aliases.extend(["indices", "index", "krx.indices", "bas_dd", "idx_nm", "fluc_rt"])
    if any(word in q for word in ("주가", "가격", "price", "close", "종목", "상승", "오른")):
        aliases.extend(["prices", "price", "close", "krx.prices", "fluc_rt"])
    if any(word in q for word in ("공시", "dart", "filing")):
        aliases.extend(["dart", "filing", "disclosure"])
    raw = re.split(r"[^0-9a-zA-Z가-힣_./-]+", q)
    return [term for term in dict.fromkeys([*raw, *aliases]) if len(term) >= 2]


def _join_values(item: dict[str, Any], keys: tuple[str, ...]) -> str:
    values: list[str] = []
    for key in keys:
        value = item.get(key)
        if value in (None, "", [], {}):
            continue
        if isinstance(value, (list, tuple, set)):
            values.extend(str(part) for part in value)
        elif isinstance(value, dict):
            values.extend(f"{k}:{v}" for k, v in value.items())
        else:
            values.append(str(value))
    return " ".join(values)


def _drop_empty(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value not in (None, "", [], {})}
