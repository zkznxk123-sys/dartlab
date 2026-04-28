"""Audit 로그 수집기 — Phase O (Observe).

`POST /api/ask` · `dartlab.ask()` 직호출 양쪽에서 요청 종료 시
`{dataDir}/audit/ai-ask/YYYY-MM-DD.jsonl` 에 한 줄씩 append 한다.
자가개선 루프 (Phase P/R/F/A) 의 원천 데이터.

jsonl v2 스키마 (ops/coreloop.md §B.3)
=====================================

한 줄 = 1 요청::

    {
      "schema_version": 2,
      "ts": "2026-04-25T09:30:00.000000+00:00",
      "request_id": "req-abc123",
      "question": "삼성전자 수익성 분석해줘",
      "question_hash": "sha256:...",
      "category_hash": "FIN-profitability-KR-tech",
      "stockCode_hint": "005930",
      "provider": "oauth-codex",
      "model": "gpt-5-codex",
      "tool_calls": [{"name": "...", "args": {...}, "args_hash": "...",
                      "ok": true, "error": null, "duration_ms": 1823,
                      "result_size_bytes": 4012, "overrides_used": null,
                      "extreme_flags": []}, ...],
      "tool_sequence_hash": "seq:a1b2c3d4",
      "override_calls": [{"tool": "...", "override_keys": [...],
                          "trigger": "...", "succeeded": true}, ...],
      "rounds": 2,
      "chunk_len": 1823,
      "error": null,
      "violation": null,
      "skill_used": null,
      "duration_total_ms": 4521,
      "judgment": {"verdict": null, "judged_at": null,
                   "judged_by": null, "pr_url": null}
    }
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 2
MANUAL_JUDGMENT_SCHEMA_VERSION = 1


def _sha16(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _seq_hash(tool_calls: list[dict[str, Any]]) -> str:
    parts = []
    for tc in tool_calls:
        name = tc.get("name", "")
        args_hash = tc.get("args_hash", "")
        parts.append(f"{name}:{args_hash}")
    return "seq:" + hashlib.sha256(",".join(parts).encode("utf-8")).hexdigest()[:16]


def _args_hash(args: dict[str, Any]) -> str:
    try:
        serialized = json.dumps(args, sort_keys=True, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        serialized = repr(args)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def _truncate_args(args: dict[str, Any], cap: int = 500) -> dict[str, Any]:
    """args 값 중 500 자 초과하는 문자열은 truncate 표시."""
    out: dict[str, Any] = {}
    for k, v in args.items():
        if isinstance(v, str) and len(v) > cap:
            out[k] = {"truncated": True, "size": len(v), "preview": v[:cap]}
        else:
            out[k] = v
    return out


class AuditCollector:
    """요청 단위 audit 로그 누적기.

    사용::

        auditor = AuditCollector(question="삼성전자 수익성", stockCode_hint="005930")
        auditor.observe_tool_call("analysis", {"axis": "수익성"}, ok=True,
                                  duration_ms=1823, result_size=4012)
        auditor.observe_override("analysis", ["wacc"], trigger="...", succeeded=True)
        auditor.flush(chunk_len=1823, error=None)
    """

    def __init__(
        self,
        *,
        question: str = "",
        stockCode_hint: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        data_dir: Path | str | None = None,
    ):
        self.schema_version = SCHEMA_VERSION
        self.ts = datetime.now(timezone.utc).isoformat()
        self.request_id = f"req-{uuid.uuid4().hex[:12]}"
        self.question = question
        self.question_hash = _sha16(_normalize_q(question)) if question else ""
        self.category_hash: str = ""  # post-resolve by caller
        self.stockCode_hint = stockCode_hint
        self.provider = provider
        self.model = model
        self.tool_calls: list[dict[str, Any]] = []
        self.override_calls: list[dict[str, Any]] = []
        self.violation: str | None = None
        self.quality_issues: list[str] = []
        self.skill_used: str | None = None
        self.chunk_len = 0
        self.error: str | None = None
        self._start_mono = time.monotonic()
        self._data_dir = Path(data_dir) if data_dir else _resolve_data_dir()

    # ── observations ──────────────────────────────────────────────

    def observe_tool_call(
        self,
        name: str,
        args: dict[str, Any] | None = None,
        *,
        ok: bool = True,
        error: str | None = None,
        duration_ms: int | None = None,
        result_size_bytes: int | None = None,
        overrides_used: dict[str, Any] | None = None,
        extreme_flags: list[str] | None = None,
    ) -> None:
        safe_args = _truncate_args(args or {})
        self.tool_calls.append(
            {
                "name": name,
                "args": safe_args,
                "args_hash": _args_hash(safe_args),
                "ok": bool(ok),
                "error": (error[:200] if error else None),
                "duration_ms": duration_ms,
                "result_size_bytes": result_size_bytes,
                "overrides_used": overrides_used,
                "extreme_flags": extreme_flags or [],
            }
        )

    def observe_override(
        self,
        tool: str,
        override_keys: list[str],
        *,
        trigger: str = "",
        succeeded: bool = True,
    ) -> None:
        self.override_calls.append(
            {
                "tool": tool,
                "override_keys": list(override_keys),
                "trigger": trigger,
                "succeeded": bool(succeeded),
            }
        )

    def observe_violation(self, message: str) -> None:
        self.violation = message[:200]

    def set_category_hash(self, value: str) -> None:
        self.category_hash = value

    def observe(self, kind: str, data: dict[str, Any]) -> None:
        """core.runAsk 이벤트를 audit 스키마로 누적한다."""
        if kind == "tool_call":
            name = str(data.get("name") or data.get("tool") or "")
            args = data.get("arguments") or data.get("args") or {}
            self.observe_tool_call(name, args if isinstance(args, dict) else {})
        elif kind == "chunk":
            self.chunk_len += len(str(data.get("text", "")))
        elif kind == "error":
            self.error = str(data.get("error") or "")
            if "VIOLATION" in self.error:
                self.observe_violation(self.error)
        elif kind == "quality_check":
            issues = data.get("issues") or []
            if isinstance(issues, list):
                self.quality_issues = [str(i) for i in issues]
            if data.get("passed", True):
                self.quality_issues = []
            elif data.get("action") == "record_violation" and self.quality_issues:
                self.observe_violation(",".join(self.quality_issues))

    # ── flush ─────────────────────────────────────────────────────

    def flush(self, *, chunk_len: int | None = None, error: str | None = None) -> None:
        if os.environ.get("DARTLAB_AUDIT_DISABLE") == "1":
            return
        final_chunk_len = self.chunk_len if chunk_len is None else chunk_len
        final_error = self.error if error is None else error
        rounds = max(1, len(self.tool_calls))
        entry = {
            "schema_version": self.schema_version,
            "ts": self.ts,
            "request_id": self.request_id,
            "question": self.question,
            "question_hash": self.question_hash,
            "category_hash": self.category_hash,
            "stockCode_hint": self.stockCode_hint,
            "provider": self.provider,
            "model": self.model,
            "tool_calls": self.tool_calls,
            "tool_sequence_hash": _seq_hash(self.tool_calls),
            "override_calls": self.override_calls,
            "rounds": rounds,
            "chunk_len": int(final_chunk_len),
            "error": (final_error[:200] if final_error else None),
            "violation": self.violation,
            "quality_issues": self.quality_issues,
            "skill_used": self.skill_used,
            "duration_total_ms": int((time.monotonic() - self._start_mono) * 1000),
            "judgment": {"verdict": None, "judged_at": None, "judged_by": None, "pr_url": None},
        }
        try:
            day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            out_dir = self._data_dir / "audit" / "ai-ask"
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / f"{day}.jsonl"
            line = json.dumps(entry, ensure_ascii=False, default=str)
            if len(line) > 4096:
                # 라인 4KB 초과 시 args 를 요약본으로 강제 cap
                for tc in entry["tool_calls"]:
                    tc["args"] = {"truncated": True, "size": len(str(tc.get("args", "")))}
                line = json.dumps(entry, ensure_ascii=False, default=str)
            with path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
        except OSError:
            # I/O 실패는 응답 경로 깨지 않도록 조용히 무시.
            pass


# Backward-compat alias — 기존 `_AuditCollector` import 호환.
_AuditCollector = AuditCollector


def writeManualJudgment(
    *,
    request_id: str,
    verdict: str,
    reason: str,
    issue_code: str | None = None,
    suggested_fix: str | None = None,
    accepted_by: str | None = None,
    question: str | None = None,
    data_dir: Path | str | None = None,
) -> Path | None:
    """직접 P/T/C/V 판정을 UTF-8 JSONL 로 남긴다.

    자동 violation 이 아니라 사람이 답변 원문을 읽고 확정한 품질 개선 루프의
    원천 로그다.
    """
    if verdict not in {"P", "T", "C", "V"}:
        raise ValueError("verdict must be one of P/T/C/V")
    root = Path(data_dir) if data_dir else _resolve_data_dir()
    entry = {
        "schema_version": MANUAL_JUDGMENT_SCHEMA_VERSION,
        "ts": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "question": question,
        "verdict": verdict,
        "reason": reason,
        "issue_code": issue_code,
        "suggested_fix": suggested_fix,
        "accepted_by": accepted_by,
    }
    try:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out_dir = root / "audit" / "ai-judgment"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{day}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        return path
    except OSError:
        return None


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────


def _normalize_q(q: str) -> str:
    """question 해시를 위한 정규화 — 소문자·공백 축소·구두점 제거."""
    import re

    q = q.lower().strip()
    q = re.sub(r"[^\w\s가-힣]", "", q)
    q = re.sub(r"\s+", " ", q)
    return q


def _resolve_data_dir() -> Path:
    """`dartlab.dataDir()` 동등. 순환 import 회피."""
    try:
        from dartlab import dataDir as _dd

        return Path(_dd())
    except Exception:
        # fallback: 프로젝트 루트 data/
        here = Path(__file__).resolve()
        for parent in here.parents:
            if (parent / "pyproject.toml").exists():
                return parent / "data"
        return Path.cwd() / "data"
