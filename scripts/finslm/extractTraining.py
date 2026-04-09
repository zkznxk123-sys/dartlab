"""Stage A — 학습 데이터 추출.

소스:
1. data/dart/auditAnalysis/*.md (170개) → 구조화 QA 페어
2. blog/05-company-reports/*/index.md (6개) → 6막 서사 QA
3. KnowledgeDB (executions G등급 + skills + playbook)
4. (Stage B에서) publishBatch 결과 → review QA

실행:
    uv run python -X utf8 scripts/finslm/extractTraining.py

출력:
    data/finslm/raw/audit_pairs.jsonl
    data/finslm/raw/blog_pairs.jsonl
    data/finslm/raw/db_pairs.jsonl
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT_DIR = ROOT / "data" / "dart" / "auditAnalysis"
BLOG_DIR = ROOT / "blog" / "05-company-reports"
OUT_DIR = ROOT / "data" / "finslm" / "raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 시스템 프롬프트 축약본 (학습용)
SYSTEM_PROMPT = (
    "당신은 dartlab 한국/미국 공시 분석 전문가입니다. "
    "재무제표 데이터를 기반으로 기업을 분석합니다. "
    "숫자는 원본 그대로 인용하고, 근거 없는 주장은 하지 않습니다. "
    "6막 서사 구조(사업이해→수익성→현금→안정성→자본배분→전망)로 분석합니다."
)


def _sharegpt(system: str, human: str, gpt: str, meta: dict) -> dict:
    """ShareGPT 포맷."""
    return {
        "conversations": [
            {"from": "system", "value": system},
            {"from": "human", "value": human},
            {"from": "gpt", "value": gpt},
        ],
        "metadata": meta,
    }


# ── 1. auditAnalysis 추출 ─────────────────────────────────


def _splitSections(text: str) -> dict[str, str]:
    """## 또는 #### 헤더 기준으로 섹션 분리."""
    sections: dict[str, str] = {}
    current_key = "_header"
    current_lines: list[str] = []

    for line in text.split("\n"):
        m = re.match(r"^(#{2,4})\s+(.+)", line)
        if m:
            if current_lines:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = m.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections[current_key] = "\n".join(current_lines).strip()
    return sections


def _extractStockCode(filename: str) -> str:
    return filename.replace(".md", "")


def extractAuditAnalysis() -> list[dict]:
    """170개 auditAnalysis → QA 페어."""
    pairs = []
    files = sorted(AUDIT_DIR.glob("*.md"))
    print(f"[audit] {len(files)}개 파일 처리...")

    for f in files:
        code = _extractStockCode(f.name)
        text = f.read_text(encoding="utf-8")
        sections = _splitSections(text)

        # 첫 줄에서 회사명 추출
        first_line = text.split("\n")[0] if text else ""
        corp_match = re.match(r"^##\s*(.+?)\s*\(", first_line)
        corp_name = corp_match.group(1) if corp_match else code

        # 전체 보고서
        if len(text) > 200:
            pairs.append(_sharegpt(
                SYSTEM_PROMPT,
                f"{corp_name}({code}) 종합 재무분석을 해줘.",
                text[:8000],  # 8K cap
                {"stock_code": code, "intent": "act_all", "source": "auditAnalysis", "type": "full"},
            ))

        # 섹션별 QA
        _SECTION_QUESTIONS = {
            "부문별 매출 구성": (f"{corp_name} 사업 구성과 매출 비중을 알려줘.", "act1_business"),
            "부문별 매출 추이": (f"{corp_name} 부문별 매출 추세는?", "act1_business"),
            "매출 성장률": (f"{corp_name} 매출 성장률과 CAGR은?", "act1_business"),
            "매출 집중도": (f"{corp_name} 매출 집중도(HHI)는?", "act1_business"),
            "마진 추이": (f"{corp_name} 영업이익률 추세를 분석해줘.", "act2_profit"),
            "수익률 추이 (Return Trend)": (f"{corp_name} ROE와 ROIC 추이는?", "act2_profit"),
            "DuPont 분해": (f"{corp_name} DuPont 분해 결과는?", "act2_profit"),
            "현금흐름 개요": (f"{corp_name} 현금흐름 패턴은?", "act3_cash"),
            "현금 품질 (Cash Quality)": (f"{corp_name} 이익품질 어때?", "act3_cash"),
            "자금 원천": (f"{corp_name} 자금조달 구조는?", "act4_stability"),
            "레버리지 추이": (f"{corp_name} 부채비율 추이는?", "act4_stability"),
            "부실 판별 (Z-Score)": (f"{corp_name} Z-Score로 부실 위험 봐줘.", "act4_stability"),
            "자산 구조": (f"{corp_name} 자산 구성은?", "act5_capital"),
            "ROIC 추이": (f"{corp_name} ROIC vs WACC 추이는?", "act5_capital"),
            "배당 정책": (f"{corp_name} 배당정책 알려줘.", "act5_capital"),
            "비용구조": (f"{corp_name} 비용구조 분해해줘.", "act2_profit"),
            "밸류에이션 요약": (f"{corp_name} 적정가 얼마야?", "act6_outlook"),
            "스코어카드": (f"{corp_name} 재무 종합 등급은?", "act_all"),
            "매출 품질": (f"{corp_name} 매출 품질은?", "act3_cash"),
        }

        for sec_name, (question, intent) in _SECTION_QUESTIONS.items():
            content = sections.get(sec_name, "")
            if not content or len(content) < 30:
                continue
            pairs.append(_sharegpt(
                SYSTEM_PROMPT,
                question,
                content[:4000],
                {"stock_code": code, "intent": intent, "source": "auditAnalysis", "type": "section"},
            ))

    print(f"[audit] {len(pairs)}개 페어 추출")
    return pairs


# ── 2. Blog 추출 ──────────────────────────────────────────


def extractBlog() -> list[dict]:
    """6개 블로그 보고서 → 6막별 QA."""
    pairs = []
    dirs = sorted(BLOG_DIR.glob("*/"))

    for d in dirs:
        idx = d / "index.md"
        if not idx.exists():
            continue
        text = idx.read_text(encoding="utf-8")

        # frontmatter에서 메타 추출
        fm_match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        meta = {}
        if fm_match:
            for line in fm_match.group(1).split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"')

        code = meta.get("stockCode", "")
        corp = meta.get("corpName", d.name)
        template = meta.get("storyTemplate", "")

        # 전체 보고서
        body = text[fm_match.end():] if fm_match else text
        if len(body) > 500:
            pairs.append(_sharegpt(
                SYSTEM_PROMPT,
                f"{corp}({code}) 종합 분석 보고서를 써줘. 템플릿: {template}",
                body[:12000],
                {"stock_code": code, "intent": "act_all", "source": "blog", "type": "full_report"},
            ))

        # 막별 분리 (# 제N막 패턴)
        act_pattern = re.compile(r"^(#{1,2})\s*(제\d막.+)", re.MULTILINE)
        acts = list(act_pattern.finditer(body))
        for i, m in enumerate(acts):
            start = m.end()
            end = acts[i + 1].start() if i + 1 < len(acts) else len(body)
            act_title = m.group(2).strip()
            act_body = body[start:end].strip()
            if len(act_body) > 100:
                pairs.append(_sharegpt(
                    SYSTEM_PROMPT,
                    f"{corp}({code})의 {act_title}을 분석해줘.",
                    act_body[:6000],
                    {"stock_code": code, "intent": f"blog_act_{i+1}", "source": "blog", "type": "act"},
                ))

    print(f"[blog] {len(pairs)}개 페어 추출")
    return pairs


# ── 3. KnowledgeDB 추출 ──────────────────────────────────


def extractDB() -> list[dict]:
    """KnowledgeDB executions/skills/playbook → QA."""
    pairs = []
    try:
        from dartlab.ai.persistence import KnowledgeDB
        db = KnowledgeDB.get()
        conn = db.connection
    except (ImportError, OSError):
        print("[db] KnowledgeDB 접근 불가 — skip")
        return pairs

    # executions (G등급)
    rows = conn.execute(
        "SELECT stock_code, question, result_summary, grade FROM executions "
        "WHERE grade IN ('G', 'P') AND length(result_summary) > 100 "
        "ORDER BY created_at DESC LIMIT 500"
    ).fetchall()
    for code, q, summary, grade in rows:
        pairs.append(_sharegpt(
            SYSTEM_PROMPT,
            q,
            summary[:4000],
            {"stock_code": code or "", "intent": "execution", "source": "knowledgedb", "grade": grade},
        ))

    # skills
    skill_rows = conn.execute(
        "SELECT question, code_template, category FROM skills "
        "WHERE quality_score >= 0.7 AND length(code_template) > 50 "
        "ORDER BY quality_score DESC LIMIT 100"
    ).fetchall()
    for q, code_tmpl, cat in skill_rows:
        pairs.append(_sharegpt(
            SYSTEM_PROMPT,
            q,
            f"```python\n{code_tmpl[:3000]}\n```",
            {"intent": "coding", "source": "knowledgedb_skill", "category": cat},
        ))

    # playbook
    pb_rows = conn.execute(
        "SELECT intent, sector, bullet FROM playbook "
        "WHERE quality >= 0.5 ORDER BY quality DESC LIMIT 200"
    ).fetchall()
    # intent별 그룹핑
    intent_bullets: dict[str, list[str]] = {}
    for intent, sector, bullet in pb_rows:
        key = f"{intent}:{sector}" if sector else intent
        intent_bullets.setdefault(key, []).append(bullet)
    for key, bullets in intent_bullets.items():
        intent = key.split(":")[0]
        sector = key.split(":")[1] if ":" in key else ""
        bullet_text = "\n".join(f"- {b}" for b in bullets[:8])
        pairs.append(_sharegpt(
            SYSTEM_PROMPT,
            f"{intent} 분석 시 핵심 관점은 무엇인가?{f' (섹터: {sector})' if sector else ''}",
            f"이전 분석에서 검증된 핵심 관점:\n\n{bullet_text}",
            {"intent": intent, "source": "knowledgedb_playbook", "sector": sector},
        ))

    print(f"[db] {len(pairs)}개 페어 추출 (exec={len(rows)}, skill={len(skill_rows)}, pb={len(intent_bullets)})")
    return pairs


# ── 메인 ──────────────────────────────────────────────────


def main() -> int:
    print("=" * 60)
    print("Stage A — 학습 데이터 추출")
    print("=" * 60)

    all_pairs: dict[str, list[dict]] = {}

    # 1. auditAnalysis
    audit_pairs = extractAuditAnalysis()
    all_pairs["audit"] = audit_pairs

    # 2. Blog
    blog_pairs = extractBlog()
    all_pairs["blog"] = blog_pairs

    # 3. KnowledgeDB
    db_pairs = extractDB()
    all_pairs["db"] = db_pairs

    # 저장
    total = 0
    for name, pairs in all_pairs.items():
        out_path = OUT_DIR / f"{name}_pairs.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for p in pairs:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
        total += len(pairs)
        print(f"  → {out_path.name}: {len(pairs)}개")

    print(f"\n총 {total}개 페어 → {OUT_DIR}")

    # 통계
    sources = {}
    intents = {}
    for pairs in all_pairs.values():
        for p in pairs:
            src = p["metadata"].get("source", "?")
            intent = p["metadata"].get("intent", "?")
            sources[src] = sources.get(src, 0) + 1
            intents[intent] = intents.get(intent, 0) + 1

    print("\n소스별:")
    for k, v in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    print("\nintent별:")
    for k, v in sorted(intents.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
