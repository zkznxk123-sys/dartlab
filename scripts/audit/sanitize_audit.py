"""audit jsonl 민감정보 마스킹 — 공개 공유 전 필수.

사용
====

hash 모드 (기본) — question 을 question_hash 로 대체
    uv run python scripts/audit/sanitize_audit.py --in data/audit/ai-ask/ --out /tmp/sanitized/ --mode hash

drop 모드 — question 필드 완전 삭제
    uv run python scripts/audit/sanitize_audit.py --in data/audit/ai-ask/ --out /tmp/sanitized/ --mode drop

mask 모드 — 종목명·이메일·URL 만 마스킹 (공개 블로그용)
    uv run python scripts/audit/sanitize_audit.py --in data/audit/ai-ask/ --out /tmp/sanitized/ --mode mask

check 모드 — 민감 토큰 검출 리포트만 (파일 미작성)
    uv run python scripts/audit/sanitize_audit.py --check data/audit/ai-ask/

원본 jsonl 은 **절대 덮어쓰지 않는다**. 항상 `--out` 신 디렉토리.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

EMAIL_RX = re.compile(r"\b[\w.+-]+@[\w.-]+\.\w+\b")
URL_RX = re.compile(r"https?://\S+")
API_KEY_RX = re.compile(r"(?i)\b(api[_-]?key|token|secret)\s*[=:]\s*\S+")


def _hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _mask(text: str, corp_names: set[str]) -> str:
    # 종목명
    if corp_names:
        for name in sorted(corp_names, key=len, reverse=True):
            if name in text:
                text = text.replace(name, "[CORP]")
    text = EMAIL_RX.sub("[EMAIL]", text)
    text = URL_RX.sub("[URL]", text)
    text = API_KEY_RX.sub("[REDACTED]", text)
    return text


def _load_corp_names() -> set[str]:
    """KRX 상장 종목명. 실패 시 빈 set (마스킹 안 함)."""
    try:
        import dartlab

        df = dartlab.listing()
        return set(df["corpName"].to_list())
    except Exception:
        return set()


def _sanitize_entry(entry: dict, mode: str, corp_names: set[str]) -> dict:
    q = entry.get("question", "")
    if mode == "hash":
        entry.pop("question", None)
        entry["question_hash"] = _hash(q) if q else ""
    elif mode == "drop":
        entry.pop("question", None)
    elif mode == "mask":
        entry["question"] = _mask(q, corp_names)
    return entry


def _check_only(in_dir: Path) -> int:
    """민감 토큰 검출 리포트."""
    emails = 0
    urls = 0
    api_keys = 0
    lines = 0
    for path in sorted(in_dir.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                lines += 1
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                q = e.get("question", "") or ""
                if EMAIL_RX.search(q):
                    emails += 1
                if URL_RX.search(q):
                    urls += 1
                if API_KEY_RX.search(q):
                    api_keys += 1
    print(f"[sanitize:check] 총 {lines} 라인 스캔")
    print(f"  email 패턴 포함: {emails}")
    print(f"  url 패턴 포함: {urls}")
    print(f"  api_key 패턴 포함: {api_keys}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="in_dir", type=Path, default=None, help="원본 디렉토리")
    ap.add_argument("--out", dest="out_dir", type=Path, default=None, help="출력 디렉토리 (원본 불변)")
    ap.add_argument("--mode", choices=["hash", "drop", "mask"], default="hash")
    ap.add_argument("--check", type=Path, default=None, help="검출 리포트만 (입력 디렉토리)")
    args = ap.parse_args()

    if args.check is not None:
        return _check_only(args.check)

    if args.in_dir is None or args.out_dir is None:
        print("--in 과 --out 모두 필요 (또는 --check <dir>)", file=sys.stderr)
        return 2

    if args.in_dir.resolve() == args.out_dir.resolve():
        print("[fatal] --in 과 --out 이 같은 디렉토리입니다. 원본을 보존하려면 다른 경로.", file=sys.stderr)
        return 2

    args.out_dir.mkdir(parents=True, exist_ok=True)
    corp_names = _load_corp_names() if args.mode == "mask" else set()

    total = 0
    for path in sorted(args.in_dir.glob("*.jsonl")):
        out_path = args.out_dir / path.name
        with path.open("r", encoding="utf-8") as fin, out_path.open("w", encoding="utf-8") as fout:
            for line in fin:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                sanitized = _sanitize_entry(entry, args.mode, corp_names)
                fout.write(json.dumps(sanitized, ensure_ascii=False) + "\n")
                total += 1
        print(f"  {path.name}: sanitized → {out_path}")
    print(f"done. total lines: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
