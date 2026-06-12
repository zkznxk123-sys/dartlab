"""파이프라인 건강 모니터 — 모든 실패 알림 + 단발은 자동 재실행 병행.

gh CLI로 각 워크플로우의 최근 실행을 조회한다. **실패는 단발이든 연속이든 모두 Issue 로
알린다**(운영자 가시성 우선 — 조용히 삼키지 않음). 단발 transient 실패는 알림과 **동시에 자동
재실행**(rerun)해 자가치유를 시도하고 Issue 에 "단발 — 자동 재실행 중"으로, **연속 2회+**
(persistent)는 "연속 — 조치 필요"로 표시해 심각도를 구분한다. 실패 로그/주석에서 원인(메모리/
디스크·HF 429·timeout·code)을 분류해 actionable 하게 적고, 전부 정상이면 열린 Issue 를 닫는다.

감시 대상 = **scheduled(cron) 데이터/자동화 파이프라인 전체**. 새 scheduled 워크플로우를
추가하면 여기 name 도 등록해야 그 실패가 알림된다(미등록 = 조용한 실패).

환경변수:
  GH_TOKEN: GitHub 토큰 (Actions에서 자동 제공). rerun 은 actions:write, Issue 는 issues:write.
"""

import json
import os
import subprocess
from datetime import datetime, timezone

# scheduled(cron) 데이터/자동화 파이프라인 전체 — gh run list 의 워크플로우 `name:` 값과 정확히 일치해야 함.
# (제외: 코드 CI/CodeQL/Policy·Deploy·Publish·Metrics·EDGAR Safety Gate·Data Audit 자기 자신·mapBuild(cron 없음))
MONITORED_WORKFLOWS = [
    "Original SSOT Sync",  # dart-zip · allfilings · edgar (cron 0 2) — 핵심 원본/panel 파이프라인
    "EDGAR Panel Rebuild (continue)",  # EDGAR 전 universe 부트스트랩 이어달리기 (cron 0 */6) — 수렴 시 자기 비활성화
    "Data Sync",
    "DART New Stocks Sync",
    "Data Prebuild (DART)",
    "EDGAR Data Sync (Bulk)",
    "Gov Price Sync (Bulk)",
    "Gov Index Sync (Bulk)",
    "Macro Data Sync (Bulk)",
    "News Archive Sync",
    "GDELT Sync",
    "Naver News Sync",  # 네이버 뉴스 private archive (cron 30 9) — 무키 시 green-noop, 키 설정 시 실데이터
    "Valuation Snapshot",
    "Search Index Delta (daily)",
    "Search Index Main (monthly)",
    "Quant Audit",
    "Update KindList",
    "Intent Model Pipeline",  # 공시 Q&A 라우팅 모델 빌드+회귀게이트+HF 업로드 (cron 0 20 일요일)
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


def _issueTitle(persistent: list[dict], retried: list[dict]) -> str:
    """실패 Issue 제목 — 연속 실패가 있으면 'Pipeline failure', 단발뿐이면 '(자동 재실행 중)' 표기.

    Args:
        persistent: 연속 2회+ 실패 entry list.
        retried: 단발 실패(자동 재실행) entry list.

    Returns:
        100자 이내 Issue 제목. 워크플로우가 많아 길면 개수 요약으로 축약.

    Raises:
        없음.

    Example:
        >>> _issueTitle([{"name": "Original SSOT Sync"}], [])
        'Pipeline failure: Original SSOT Sync'
        >>> _issueTitle([], [{"name": "Macro Data Sync (Bulk)"}])
        'Pipeline failure (자동 재실행 중): Macro Data Sync (Bulk)'
    """
    names = ", ".join(f["name"] for f in (persistent + retried))
    prefix = "Pipeline failure" if persistent else "Pipeline failure (자동 재실행 중)"
    title = f"{prefix}: {names}"
    if len(title) > 100:
        title = f"{prefix}: {len(persistent) + len(retried)}개 워크플로우"
    return title


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

    failing = persistent + retried  # 단발이든 연속이든 모든 실패를 알린다(가시성 우선 — 조용한 실패 0)
    if failing:
        body = _buildIssueBody(statuses, persistent, retried)
        if openIssue:
            _gh(["issue", "comment", str(openIssue), "--body", body])
            print(f"[monitor] 기존 Issue #{openIssue} 갱신 (연속 {len(persistent)} · 단발 {len(retried)})")
        else:
            title = _issueTitle(persistent, retried)
            out = _gh(["issue", "create", "--title", title, "--body", body, "--label", FAILURE_LABEL])
            print(f"[monitor] Issue 생성 (연속 {len(persistent)} · 단발 {len(retried)}): {out}")
    elif openIssue:
        _gh(["issue", "close", str(openIssue), "--comment", "모든 파이프라인 정상 복구 — 자동 닫기."])
        print(f"[monitor] Issue #{openIssue} 자동 닫기 (실패 0)")
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

    lines.append(
        f"\n> 자동 생성 by Pipeline Monitor ({now}). 모든 실패 알림 — 단발은 자동 재실행 병행(blip 이면 자가치유), "
        "연속 2회+ 는 조치 필요. 복구되면 자동 닫힘."
    )
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
