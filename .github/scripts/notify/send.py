"""발행 감지 → pushHub /send 호출 + 응답 집계 헬스게이트.

워크플로: .github/workflows/notify-publish.yml (push paths: blog/**/index.md, blog/_issues/**/cards.plan.json).
헬스게이트(brokerageSync 패턴 미러): 발송 이벤트가 있었는데 전 실패(sent==0 & failed/pruned>0)·HTTP 자체실패
(401/409 등)·failed 비율 임계 초과 시 비-0 exit → 워크플로 RED → 운영자 자동알림. 구독 0(no-op)은 정상 종료.
재시도 = P1 비범위(결정적 nonce 라 재실행은 전부 409). 발행 알림은 저-stakes 단발.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib import error, request

import yaml

from notify.authHeaders import authHeaders
from notify.payload import PublishEvent, buildPayload

_BLOG = re.compile(r"^blog/[^/]+/\d+-([^/]+)/index\.md$")
_ISSUE = re.compile(r"^blog/_issues/([^/]+)/cards\.plan\.json$")
_ZERO = re.compile(r"^0+$")
_FAIL_RATIO = 0.5  # failed/(sent+failed) 초과 시 RED


def _repo_root() -> Path:
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
    return Path(out.stdout.strip())


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout


def parse_frontmatter(text: str) -> dict:
    """`---`…`---` 사이 통째 yaml.safe_load(라인파서 금지 — nested carousel dict·멀티라인 caption 처리)."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    data = yaml.safe_load(text[3:end])
    return data if isinstance(data, dict) else {}


def detect(before: str, sha: str, root: Path | None = None) -> list[PublishEvent]:
    root = root or _repo_root()
    # 신규 브랜치/force(before all-zero) → sha~1 폴백
    base = f"{sha}~1" if (not before or _ZERO.match(before)) else before
    files = _git(root, "diff", "--name-only", base, sha).splitlines()
    events: list[PublishEvent] = []
    for f in files:
        m = _BLOG.match(f)
        if m:
            slug = m.group(1)  # \d+- 뒤 그룹 = 라이브 normalizePath 와 동형
            front = parse_frontmatter((root / f).read_text("utf-8"))
            title = front.get("title", slug)
            desc = front.get("description", "")  # 키 = description (summary 0건 실측)
            events.append(PublishEvent("blogPublish", slug, title, desc))
            if front.get("carousel"):  # carousel: nested dict → 카드도 발행
                events.append(PublishEvent("cardPublish", slug, title, desc))
            continue
        m = _ISSUE.match(f)
        if m:
            plan = json.loads((root / f).read_text("utf-8"))
            tgt = plan.get("target", {})  # title/slug 는 target 하위(top-level 부재)
            slug = tgt.get("slug", m.group(1))
            title = tgt.get("title", m.group(1))
            body = plan.get("planning", {}).get("cardThesis", "")  # description 부재 → cardThesis
            events.append(PublishEvent("cardPublish", slug, title, body))
    return events


def _post(url: str, token: str, raw: bytes, headers: dict) -> tuple[int, dict]:
    req = request.Request(url.rstrip("/") + "/send", data=raw, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {token}")
    for k, v in headers.items():
        req.add_header(k, v)
    with request.urlopen(req, timeout=20) as resp:
        payload = resp.read().decode("utf-8") or "{}"
        return resp.status, json.loads(payload)


def _is_red(status: int, body: dict) -> bool:
    if status >= 400:
        return True  # 401/409 등 HTTP 자체 실패
    sent = int(body.get("sent", 0))
    failed = int(body.get("failed", 0))
    pruned = int(body.get("pruned", 0))
    if sent == 0 and (failed > 0 or pruned > 0):
        return True  # 전 실패 — 구독 0(no-op) 과 구분
    if failed and failed / max(1, sent + failed) > _FAIL_RATIO:
        return True
    return False


def _write_summary(rows: list[tuple[str, str, str]]) -> None:
    gh = os.environ.get("GITHUB_STEP_SUMMARY")
    if not gh:
        return
    lines = ["### Notify Publish", "", "| topic | slug | result |", "|---|---|---|"]
    lines += [f"| {t} | {s} | {r} |" for (t, s, r) in rows]
    with open(gh, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True)
    ap.add_argument("--sha", required=True)
    args = ap.parse_args(argv)

    url = os.environ.get("PUSHHUB_URL", "")
    token = os.environ.get("PUSHHUB_SEND_TOKEN", "")
    root = _repo_root()
    events = detect(args.before, args.sha, root)

    rows: list[tuple[str, str, str]] = []
    failures = 0
    for ev in events:
        payload = buildPayload(ev)
        ts = int(time.time())
        raw, headers = authHeaders(payload, ts, ev.topic, ev.slug)
        if not url or not token:
            rows.append((ev.topic, ev.slug, "skip (no PUSHHUB config)"))
            continue
        try:
            status, body = _post(url, token, raw, headers)
        except error.HTTPError as e:
            rows.append((ev.topic, ev.slug, f"HTTP {e.code}"))
            failures += 1
            continue
        except Exception as e:  # noqa: BLE001 — 네트워크/파싱 어떤 실패든 RED
            rows.append((ev.topic, ev.slug, f"ERR {type(e).__name__}"))
            failures += 1
            continue
        red = _is_red(status, body)
        rows.append((ev.topic, ev.slug, f"{status} sent={body.get('sent', 0)} failed={body.get('failed', 0)} pruned={body.get('pruned', 0)}" + (" RED" if red else "")))
        if red:
            failures += 1

    _write_summary(rows)
    if not events:
        print("발행 이벤트 없음 — no-op")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
