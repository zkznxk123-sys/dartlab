"""파이프라인 건강 모니터 — 자가치유 + 연속실패만 알림.

gh CLI로 각 워크플로우의 최근 실행을 조회한다. 단발 transient 실패는 **자동 재실행**(rerun)
하고 알림하지 않는다(다음 정기 실행이면 자가치유될 blip 으로 운영자를 깨우지 않음). **연속
2회 이상** 실패(persistent)만 Issue 로 알리며, 실패 로그/주석에서 원인(메모리/디스크·HF
429·timeout·code)을 분류해 actionable 하게 적는다. 전부 정상이면 열린 Issue 를 닫는다.

환경변수:
  GH_TOKEN: GitHub 토큰 (Actions에서 자동 제공). rerun 은 actions:write 권한 필요.
"""

import json
import os
import subprocess
from datetime import datetime, timezone

MONITORED_WORKFLOWS = [
    "Data Sync",
    "DART New Stocks Sync",
    "Data Prebuild (DART)",
    "EDGAR Data Sync (Bulk)",
    "KRX Data Sync (Bulk)",
    "KRX Index Data Sync (Bulk)",
    "Update KindList",
]

FAILURE_LABEL = "pipeline-failure"
RECENT_N = 3
_OK_CONCLUSIONS = ("success", "skipped")

# 실패 원인 분류 시그니처 (gh run view 출력 = 잡 목록 + ANNOTATIONS, 소문자 매칭).
_SIG = {
    "메모리/디스크 (runner)": ("lost communication", "out of memory", "killed", "no space left", "oom"),
    "HF rate-limit (429)": ("429", "too many requests", "rate limit", "retry this action"),
    "timeout/cancelled": ("timed out", "timeout", "cancel"),
}


def _gh(args: list[str], *, check: bool = True) -> str:
    """gh CLI 실행 후 stdout 반환."""
    result = subprocess.run(["gh"] + args, capture_output=True, text=True, env={**os.environ})
    if check and result.returncode != 0:
        print(f"[monitor] gh 실행 실패: {' '.join(args)}")
        print(f"  stderr: {result.stderr}")
    return result.stdout.strip()


def _recentRuns(workflowName: str, n: int = RECENT_N) -> list[dict]:
    """워크플로우의 최근 n 건 실행 조회 (최신순)."""
    raw = _gh(
        [
            "run",
            "list",
            "--workflow",
            workflowName,
            "--limit",
            str(n),
            "--json",
            "conclusion,status,databaseId,url,createdAt,displayTitle",
        ],
        check=False,
    )
    if not raw:
        return []
    try:
        runs = json.loads(raw)
        return runs if isinstance(runs, list) else []
    except json.JSONDecodeError:
        return []


def _classifyFailure(runId: int) -> str:
    """실패 run 의 원인 분류 — gh run view 출력(잡+ANNOTATIONS)에서 시그니처 매칭.

    Args:
        runId: 실패한 run 의 databaseId.

    Returns:
        분류 라벨 (메모리/디스크 · HF rate-limit · timeout · code/기타 · unknown).

    Raises:
        없음 — gh 실패/빈 출력은 'unknown' 으로 흡수.

    Example:
        >>> _classifyFailure(0)  # doctest: +SKIP
        'unknown'
    """
    out = _gh(["run", "view", str(runId)], check=False).lower()
    if not out:
        return "unknown"
    for label, sigs in _SIG.items():
        if any(s in out for s in sigs):
            return label
    return "code/기타"


def _rerunFailed(runId: int) -> bool:
    """실패 run 의 실패 잡만 자동 재실행 (actions:write 필요). 성공 트리거 시 True."""
    result = subprocess.run(
        ["gh", "run", "rerun", str(runId), "--failed"],
        capture_output=True,
        text=True,
        env={**os.environ},
    )
    if result.returncode != 0:
        print(f"[monitor] rerun 실패 (run {runId}): {result.stderr.strip()}")
        return False
    return True


def _triage(runs: list[dict]) -> dict:
    """최근 실행 목록 → 상태 판정 (부작용 없는 순수 함수, 테스트 대상).

    Args:
        runs: ``_recentRuns`` 결과 (최신순). 빈 목록 허용.

    Returns:
        ``{"state": ..., "conclusion": ..., "url": ..., "runId": ...}`` —
        state ∈ no_runs / running / ok / transient(첫 실패) / persistent(연속 2회+).

    Raises:
        없음.

    Example:
        >>> _triage([])["state"]
        'no_runs'
    """
    if not runs:
        return {"state": "no_runs", "conclusion": "-", "url": "-", "runId": None}

    latest = runs[0]
    conclusion = latest.get("conclusion") or ""
    status = latest.get("status") or ""
    url = latest.get("url", "-")
    runId = latest.get("databaseId")

    if status == "in_progress" or conclusion == "":
        return {"state": "running", "conclusion": status or "in_progress", "url": url, "runId": runId}
    if conclusion in _OK_CONCLUSIONS:
        return {"state": "ok", "conclusion": conclusion, "url": url, "runId": runId}

    # 최신 실패 — 직전 실행도 실패면 persistent, 아니면 첫 실패(transient).
    prevConclusion = runs[1].get("conclusion") if len(runs) > 1 else "success"
    prevFailed = prevConclusion not in (*_OK_CONCLUSIONS, "", None)
    state = "persistent" if prevFailed else "transient"
    return {"state": state, "conclusion": conclusion, "url": url, "runId": runId}


def _ensureLabel() -> None:
    """pipeline-failure 라벨이 없으면 생성."""
    existing = _gh(["label", "list", "--search", FAILURE_LABEL, "--json", "name"], check=False)
    if FAILURE_LABEL not in existing:
        _gh(
            ["label", "create", FAILURE_LABEL, "--color", "d73a4a", "--description", "데이터 파이프라인 자동 실패 알림"]
        )


def _findOpenIssue() -> int | None:
    """pipeline-failure 라벨의 열린 Issue 번호."""
    raw = _gh(
        ["issue", "list", "--label", FAILURE_LABEL, "--state", "open", "--json", "number", "--limit", "1"], check=False
    )
    if not raw:
        return None
    try:
        issues = json.loads(raw)
        return issues[0]["number"] if issues else None
    except (json.JSONDecodeError, IndexError):
        return None


def main():
    print(f"[monitor] {len(MONITORED_WORKFLOWS)}개 워크플로우 상태 확인")

    statuses: list[dict] = []
    persistent: list[dict] = []  # 연속 2회+ 실패 → Issue 알림
    retried: list[dict] = []  # 첫 실패 → 자동 rerun, 알림 보류

    for name in MONITORED_WORKFLOWS:
        runs = _recentRuns(name)
        triage = _triage(runs)
        entry = {"name": name, **triage}

        if triage["state"] in ("persistent", "transient"):
            entry["classification"] = _classifyFailure(triage["runId"]) if triage["runId"] else "unknown"

        if triage["state"] == "persistent":
            persistent.append(entry)
            icon = "FAIL×N"
        elif triage["state"] == "transient":
            entry["reran"] = _rerunFailed(triage["runId"]) if triage["runId"] else False
            retried.append(entry)
            icon = "retry" if entry["reran"] else "FAIL×1"
        elif triage["state"] == "running":
            icon = "running"
        elif triage["state"] == "ok":
            icon = "pass"
        else:
            icon = "no_runs"

        statuses.append(entry)
        print(
            f"  [{icon}] {name}: {entry['conclusion']}"
            + (f" — {entry.get('classification', '')}" if entry.get("classification") else "")
        )

    _ensureLabel()
    openIssue = _findOpenIssue()

    if persistent:
        body = _buildIssueBody(statuses, persistent, retried)
        if openIssue:
            _gh(["issue", "comment", str(openIssue), "--body", body])
            print(f"[monitor] 기존 Issue #{openIssue}에 코멘트 추가 (연속 실패 {len(persistent)}건)")
        else:
            failNames = ", ".join(f["name"] for f in persistent)
            title = f"Pipeline failure: {failNames}"
            if len(title) > 100:
                title = f"Pipeline failure: {len(persistent)}개 워크플로우 (연속 실패)"
            out = _gh(["issue", "create", "--title", title, "--body", body, "--label", FAILURE_LABEL])
            print(f"[monitor] Issue 생성: {out}")
    elif openIssue:
        note = "모든 파이프라인 워크플로우 연속 실패가 해소되었습니다. 자동 닫기."
        if retried:
            note += f" (단발 실패 {len(retried)}건은 자동 재실행 중)"
        _gh(["issue", "close", str(openIssue), "--comment", note])
        print(f"[monitor] Issue #{openIssue} 자동 닫기 (연속 실패 0)")
    elif retried:
        print(f"[monitor] 단발 실패 {len(retried)}건 자동 재실행 — Issue 생성 보류(자가치유 대기)")
    else:
        print("[monitor] 전부 정상, 열린 Issue 없음")

    _writeSummary(statuses, persistent, retried)


def _buildIssueBody(statuses: list[dict], persistent: list[dict], retried: list[dict]) -> str:
    """Issue 본문 생성 — 연속 실패 + 원인 분류 + 자동 재실행 현황."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"## Pipeline Monitor Report ({now})\n",
        "| 워크플로우 | 상태 | 원인 | 링크 |",
        "|-----------|------|------|------|",
    ]
    for s in statuses:
        icon = {
            "ok": ":white_check_mark:",
            "running": ":hourglass:",
            "persistent": ":x:",
            "transient": ":warning:",
        }.get(s["state"], ":grey_question:")
        cls = s.get("classification", "-")
        lines.append(f"| {s['name']} | {icon} {s['conclusion']} | {cls} | [보기]({s['url']}) |")

    lines.append("\n### 연속 실패 (조치 필요)")
    for f in persistent:
        lines.append(
            f"- **{f['name']}**: `{f['conclusion']}` — 원인: **{f.get('classification', 'unknown')}** — [로그]({f['url']})"
        )

    if retried:
        lines.append("\n### 단발 실패 — 자동 재실행 중 (알림 보류)")
        for r in retried:
            mark = "재실행됨" if r.get("reran") else "재실행 실패"
            lines.append(f"- {r['name']}: {r.get('classification', '-')} ({mark}) — [로그]({r['url']})")

    lines.append(f"\n> 자동 생성 by Pipeline Monitor ({now}). 연속 2회+ 실패만 알림, 단발은 자동 재실행.")
    return "\n".join(lines)


def _writeSummary(statuses: list[dict], persistent: list[dict], retried: list[dict]) -> None:
    """GitHub Actions step summary."""
    summaryPath = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summaryPath:
        return

    with open(summaryPath, "a", encoding="utf-8") as f:
        f.write("## Pipeline Health\n\n")
        f.write("| 워크플로우 | 상태 | 원인 |\n|-----------|------|------|\n")
        for s in statuses:
            icon = (
                ":white_check_mark:" if s["state"] == "ok" else (":x:" if s["state"] == "persistent" else ":warning:")
            )
            f.write(f"| {s['name']} | {icon} {s['conclusion']} | {s.get('classification', '-')} |\n")

        if persistent:
            f.write(f"\n**{len(persistent)}개 연속 실패** → Issue 생성/갱신됨\n")
        elif retried:
            f.write(f"\n**{len(retried)}개 단발 실패** → 자동 재실행 (알림 보류)\n")
        else:
            f.write("\n**전체 정상**\n")


if __name__ == "__main__":
    main()
