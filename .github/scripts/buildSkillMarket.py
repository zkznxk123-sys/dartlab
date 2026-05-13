"""Build DartLab Skill Market static indexes from GitHub Discussions.

The script is safe for local builds without a token: it writes empty market
indexes so the static site can prerender.  In GitHub Actions, it reads the
`Skill Market` discussion category through GraphQL and optionally posts or
updates a Forge draft comment on the discussion that triggered the workflow.
If the repository has not created the dedicated category yet, it reads
`[Skill Market]` discussions from the Ideas category as a bootstrap path.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import textwrap
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "landing" / "static" / "skills" / "market"
FORGE_MARKER = "<!-- dartlab-skill-market-forge -->"
BOT_LOGINS = {"github-actions[bot]", "dependabot[bot]"}
BLOCK_PATTERNS = (
    "ignore previous instructions",
    "이전 지시",
    "secret",
    "token",
    "password",
    "curl ",
    "powershell",
    "rm -rf",
    "Invoke-WebRequest",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--category", default="Skill Market")
    parser.add_argument("--fallback-category", default="Ideas")
    parser.add_argument("--fallback-title-prefix", default="[Skill Market]")
    parser.add_argument("--write-comment", action="store_true")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    args = parser.parse_args(argv)

    outDir = Path(args.out)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    generatedAt = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    if not token or not args.repo or "/" not in args.repo:
        writeMarketFiles(outDir, emptyPayload(generatedAt, reason="missing GitHub token or repository"))
        return 0

    owner, repoName = args.repo.split("/", 1)
    client = GraphqlClient(token)
    sourceCategory = args.category
    try:
        categoryId = fetchCategoryId(client, owner, repoName, args.category)
        discussions = fetchDiscussions(client, owner, repoName, categoryId)
    except Exception as exc:  # noqa: BLE001 - workflow should keep Pages buildable.
        if "discussion category not found" not in str(exc) or not args.fallback_category:
            print(f"[skill-market] GitHub fetch failed: {exc}", file=sys.stderr)
            writeMarketFiles(outDir, emptyPayload(generatedAt, reason=f"github fetch failed: {type(exc).__name__}"))
            return 0
        try:
            fallbackId = fetchCategoryId(client, owner, repoName, args.fallback_category)
            fetched = fetchDiscussions(client, owner, repoName, fallbackId)
            discussions = [
                discussion
                for discussion in fetched
                if isMarketDiscussion(discussion, args.category, args.fallback_title_prefix)
            ]
            sourceCategory = f"{args.fallback_category}:{args.fallback_title_prefix}"
            print(
                f"[skill-market] category {args.category!r} not found; "
                f"using {args.fallback_category!r} discussions with prefix {args.fallback_title_prefix!r}"
            )
        except Exception as fallbackExc:  # noqa: BLE001 - workflow should keep Pages buildable.
            print(f"[skill-market] GitHub fallback fetch failed: {fallbackExc}", file=sys.stderr)
            writeMarketFiles(
                outDir,
                emptyPayload(generatedAt, reason=f"github fallback failed: {type(fallbackExc).__name__}"),
            )
            return 0

    curatorLogins = curatorSet(owner)
    skills = [buildMarketSkill(discussion, curatorLogins=curatorLogins) for discussion in discussions]
    skills.sort(key=lambda item: (trustRank(item["trustTier"]), item.get("updatedAt") or ""), reverse=True)
    payload = {
        "index": {
            "meta": {
                "schemaVersion": "1",
                "source": "github-discussions",
                "category": sourceCategory,
                "generatedAt": generatedAt,
                "skillCount": len(skills),
                "trustPolicy": "community market entries are untrusted until curated",
            },
            "skills": skills,
        },
        "credits": buildCredits(skills, generatedAt),
        "graph": buildGraph(skills, generatedAt),
    }
    writeMarketFiles(outDir, payload)

    if args.write_comment:
        eventDiscussion = loadEventDiscussion()
        if eventDiscussion and isMarketDiscussion(eventDiscussion, args.category, args.fallback_title_prefix):
            skill = next(
                (item for item in skills if item.get("discussionNumber") == eventDiscussion.get("number")), None
            )
            if skill is not None:
                try:
                    upsertForgeComment(client, eventDiscussion["node_id"], skill)
                except Exception as exc:  # noqa: BLE001 - comment failure should not block index.
                    print(f"[skill-market] forge comment failed: {exc}", file=sys.stderr)
    return 0


def isMarketDiscussion(discussion: dict[str, Any], categoryName: str, titlePrefix: str) -> bool:
    category = ((discussion.get("category") or {}).get("name")) or ""
    title = str(discussion.get("title") or "")
    if category == categoryName:
        return True
    return bool(titlePrefix and title.lower().startswith(titlePrefix.lower()))


class GraphqlClient:
    def __init__(self, token: str) -> None:
        self.token = token

    def call(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        request = urllib.request.Request(
            "https://api.github.com/graphql",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/vnd.github+json",
                "User-Agent": "dartlab-skill-market-forge/1",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - GitHub API endpoint.
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub GraphQL HTTP {exc.code}: {body[:500]}") from exc
        if data.get("errors"):
            raise RuntimeError(json.dumps(data["errors"], ensure_ascii=False))
        return data.get("data") or {}


def fetchCategoryId(client: GraphqlClient, owner: str, repoName: str, categoryName: str) -> str:
    data = client.call(
        """
        query($owner:String!, $name:String!) {
          repository(owner:$owner, name:$name) {
            discussionCategories(first:50) {
              nodes { id name }
            }
          }
        }
        """,
        {"owner": owner, "name": repoName},
    )
    nodes = ((data.get("repository") or {}).get("discussionCategories") or {}).get("nodes") or []
    for node in nodes:
        if node.get("name") == categoryName:
            return str(node["id"])
    raise RuntimeError(f"discussion category not found: {categoryName}")


def fetchDiscussions(client: GraphqlClient, owner: str, repoName: str, categoryId: str) -> list[dict[str, Any]]:
    discussions: list[dict[str, Any]] = []
    cursor: str | None = None
    query = """
    query($owner:String!, $name:String!, $categoryId:ID!, $cursor:String) {
      repository(owner:$owner, name:$name) {
        discussions(first:50, after:$cursor, categoryId:$categoryId, orderBy:{field:UPDATED_AT, direction:DESC}) {
          pageInfo { hasNextPage endCursor }
          nodes {
            id
            number
            title
            body
            url
            createdAt
            updatedAt
            author { login }
            category { name }
            comments(first:50) {
              nodes {
                id
                body
                url
                createdAt
                updatedAt
                author { login }
              }
            }
          }
        }
      }
    }
    """
    while True:
        data = client.call(
            query,
            {"owner": owner, "name": repoName, "categoryId": categoryId, "cursor": cursor},
        )
        chunk = (data.get("repository") or {}).get("discussions") or {}
        discussions.extend(chunk.get("nodes") or [])
        pageInfo = chunk.get("pageInfo") or {}
        if not pageInfo.get("hasNextPage"):
            break
        cursor = pageInfo.get("endCursor")
    return discussions


def buildMarketSkill(discussion: dict[str, Any], *, curatorLogins: set[str]) -> dict[str, Any]:
    title = str(discussion.get("title") or "Untitled Skill")
    body = str(discussion.get("body") or "")
    comments = ((discussion.get("comments") or {}).get("nodes")) or []
    originator = ((discussion.get("author") or {}).get("login")) or "unknown"
    parsed = parseSkillText(title, body)
    moderation = readModeratorState(comments, curatorLogins)
    state = moderation.get("state") or parsed["state"]
    trustTier = moderation.get("trustTier") or trustTierForState(state, parsed)
    itemId = f"market.{stableSlug(title)}.{discussion.get('number')}"
    reviewers = sorted(
        {
            ((comment.get("author") or {}).get("login"))
            for comment in comments
            if ((comment.get("author") or {}).get("login"))
            and ((comment.get("author") or {}).get("login")) not in BOT_LOGINS
            and ((comment.get("author") or {}).get("login")) != originator
        }
    )
    return {
        "id": itemId,
        "title": title,
        "summary": parsed["summary"],
        "intent": parsed["intent"],
        "inputs": parsed["inputs"],
        "outputs": parsed["outputs"],
        "criteria": parsed["criteria"],
        "examples": parsed["examples"],
        "tags": parsed["tags"],
        "state": state,
        "trustTier": trustTier,
        "missingDetails": parsed["missingDetails"],
        "warnings": parsed["warnings"],
        "mappedBuiltinSkills": parsed["mappedBuiltinSkills"],
        "sourceType": "githubDiscussion",
        "sourceUrl": discussion.get("url"),
        "discussionNumber": discussion.get("number"),
        "author": originator,
        "createdAt": discussion.get("createdAt"),
        "updatedAt": discussion.get("updatedAt"),
        "credits": {
            "originator": [originator],
            "reviewer": reviewers,
            "curator": sorted(moderation.get("curators") or []),
            "coAuthor": coAuthorsFromComments(comments, originator),
            "implementer": [],
        },
    }


def parseSkillText(title: str, body: str) -> dict[str, Any]:
    text = normalizeText(body)
    inputs = extractList(text, ("입력", "inputs", "input"))
    outputs = extractList(text, ("기대 결과", "결과", "출력", "outputs", "output"))
    criteria = extractList(text, ("판단 기준", "기준", "판단", "criteria", "threshold"))
    examples = extractList(text, ("예시 질문", "예시", "example", "examples"))
    if not inputs:
        inputs = inferInputs(text)
    if not outputs:
        outputs = inferOutputs(text)
    if not criteria:
        criteria = inferCriteria(text)
    warnings = [pattern for pattern in BLOCK_PATTERNS if pattern.lower() in text.lower()]
    missingDetails: list[str] = []
    if not inputs:
        missingDetails.append("inputs")
    if not outputs:
        missingDetails.append("outputs")
    if not criteria:
        missingDetails.append("criteria")
    mappedBuiltinSkills = mapBuiltinSkills(f"{title}\n{text}")
    state = (
        "blocked" if warnings else "runnable" if not missingDetails else "specified" if inputs or outputs else "idea"
    )
    return {
        "summary": firstSentence(text) or title,
        "intent": firstParagraph(text) or title,
        "inputs": inputs,
        "outputs": outputs,
        "criteria": criteria,
        "examples": examples,
        "tags": inferTags(f"{title}\n{text}"),
        "missingDetails": missingDetails,
        "warnings": warnings,
        "mappedBuiltinSkills": mappedBuiltinSkills,
        "state": state,
    }


def extractList(text: str, labels: tuple[str, ...]) -> list[str]:
    lines = text.splitlines()
    values: list[str] = []
    labelPattern = "|".join(re.escape(label) for label in labels)
    for index, line in enumerate(lines):
        stripped = line.strip()
        match = re.match(rf"^(?:#+\s*)?(?:{labelPattern})\s*[:：]?\s*(.*)$", stripped, flags=re.IGNORECASE)
        if not match:
            continue
        inline = match.group(1).strip(" -")
        if inline:
            values.extend(splitItems(inline))
        for follow in lines[index + 1 : index + 7]:
            item = follow.strip()
            if not item:
                if values:
                    break
                continue
            if re.match(r"^(?:#+\s*)?[\w가-힣 ]+\s*[:：]\s*", item) and not item.startswith(("-", "*")):
                break
            if item.startswith(("-", "*")):
                values.append(item[1:].strip())
            elif values:
                values.extend(splitItems(item))
    return dedupeClean(values)[:8]


def inferInputs(text: str) -> list[str]:
    found: list[str] = []
    if any(term in text for term in ("회사", "종목", "티커", "stock", "company")):
        found.append("company")
    if any(term in text for term in ("기간", "연도", "분기", "period", "asOf")):
        found.append("period")
    if any(term in text for term in ("시장", "코스피", "나스닥", "market")):
        found.append("market")
    return found


def inferOutputs(text: str) -> list[str]:
    pairs = [
        ("매출", "revenueSignal"),
        ("매출채권", "receivableSignal"),
        ("재고", "inventorySignal"),
        ("현금흐름", "cashflowSignal"),
        ("위험", "riskComment"),
        ("밸류", "valuationSignal"),
        ("peer", "peerComparison"),
        ("비교", "comparison"),
    ]
    return [value for key, value in pairs if key.lower() in text.lower()]


def inferCriteria(text: str) -> list[str]:
    candidates = []
    for line in text.splitlines():
        if any(term in line for term in ("이상", "이하", "미만", "초과", "배", "%", "warning", "위험")):
            candidates.append(line.strip(" -*"))
    return dedupeClean(candidates)[:6]


def mapBuiltinSkills(text: str) -> list[str]:
    lowered = text.lower()
    mapping = [
        (("현금흐름", "cfo", "cashflow"), "engines.analysis.cashflow"),
        (("성장", "매출", "growth"), "engines.analysis.growth"),
        (("peer", "비교", "횡단"), "engines.scan"),
        (("신용", "부도", "credit"), "engines.credit"),
        (("거시", "금리", "macro"), "engines.macro"),
        (("cpi", "fomc", "금통위", "경제 이벤트", "서프라이즈"), "engines.macro.rates"),
        (("고용", "실업률", "침체확률"), "engines.macro.forecast"),
        (("섹터", "업종", "sector"), "recipes.macro.sectorRotation"),
        (("퀀트", "팩터", "quant"), "engines.quant"),
        (("산업", "밸류체인", "industry"), "engines.industry"),
        (("공시", "disclosure", "filing"), "engines.search"),
        (("종합", "deep", "깊게"), "recipes.credit.deepDive"),
    ]
    out: list[str] = []
    for terms, skillId in mapping:
        if any(term.lower() in lowered for term in terms):
            out.append(skillId)
    return out[:6]


def inferTags(text: str) -> list[str]:
    lowered = text.lower()
    tags: list[str] = []
    for key, tag in [
        ("현금흐름", "cashflow"),
        ("위험", "risk"),
        ("매출", "growth"),
        ("peer", "peer"),
        ("공시", "disclosure"),
        ("거시", "macro"),
        ("cpi", "macro-event"),
        ("fomc", "policy"),
        ("금통위", "policy"),
        ("서프라이즈", "surprise"),
        ("퀀트", "quant"),
    ]:
        if key.lower() in lowered:
            tags.append(tag)
    return tags[:6]


def readModeratorState(comments: list[dict[str, Any]], curatorLogins: set[str]) -> dict[str, Any]:
    state = None
    curators: set[str] = set()
    for comment in comments:
        author = ((comment.get("author") or {}).get("login")) or ""
        if author not in curatorLogins:
            continue
        commands = {
            line.strip().lower()
            for line in str(comment.get("body") or "").splitlines()
            if line.strip().startswith("/market ")
        }
        if any(command.startswith("/market curated") for command in commands):
            state = "curated"
            curators.add(author)
        elif any(command.startswith("/market builtin-candidate") for command in commands):
            state = "builtin-candidate"
            curators.add(author)
        elif any(command.startswith("/market runnable") for command in commands):
            state = "runnable"
            curators.add(author)
        elif any(command.startswith("/market blocked") for command in commands):
            state = "blocked"
            curators.add(author)
    trustTier = {
        "curated": "marketCurated",
        "builtin-candidate": "builtinCandidate",
        "runnable": "marketRunnable",
        "blocked": "blocked",
    }.get(state or "")
    return {"state": state, "trustTier": trustTier, "curators": curators}


def trustTierForState(state: str, parsed: dict[str, Any]) -> str:
    if state == "blocked":
        return "blocked"
    if state == "runnable" and not parsed.get("missingDetails"):
        return "marketRunnable"
    return "marketDraft"


def coAuthorsFromComments(comments: list[dict[str, Any]], originator: str) -> list[str]:
    out = set()
    for comment in comments:
        author = ((comment.get("author") or {}).get("login")) or ""
        if not author or author == originator or author in BOT_LOGINS:
            continue
        body = str(comment.get("body") or "")
        if any(term in body for term in ("기준", "입력", "출력", "예시", "criteria", "input", "output")):
            out.add(author)
    return sorted(out)


def buildCredits(skills: list[dict[str, Any]], generatedAt: str) -> dict[str, Any]:
    return {
        "meta": {
            "schemaVersion": "1",
            "generatedAt": generatedAt,
            "policy": "DartLab credit ledger, independent from GitHub repository contributors graph",
        },
        "skills": [
            {
                "skillId": item["id"],
                "sourceUrl": item["sourceUrl"],
                "credits": item["credits"],
            }
            for item in skills
        ],
    }


def buildGraph(skills: list[dict[str, Any]], generatedAt: str) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    seen = set()
    for item in skills:
        nodes.append(
            {
                "id": item["id"],
                "title": item["title"],
                "kind": "marketSkill",
                "trustTier": item["trustTier"],
                "state": item["state"],
            }
        )
        seen.add(item["id"])
        for skillId in item.get("mappedBuiltinSkills") or []:
            if skillId not in seen:
                nodes.append({"id": skillId, "title": skillId, "kind": "builtinSkill"})
                seen.add(skillId)
            edges.append({"src": item["id"], "dst": skillId, "kind": "mapsToBuiltin"})
    return {
        "meta": {"schemaVersion": "1", "generatedAt": generatedAt},
        "nodes": nodes,
        "edges": edges,
    }


def writeMarketFiles(outDir: Path, payload: dict[str, Any]) -> None:
    outDir.mkdir(parents=True, exist_ok=True)
    files = {
        "marketIndex.json": payload["index"],
        "marketCredits.json": payload["credits"],
        "marketGraph.json": payload["graph"],
    }
    for name, data in files.items():
        (outDir / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[skill-market] wrote {len(files)} files to {outDir}")


def emptyPayload(generatedAt: str, *, reason: str) -> dict[str, Any]:
    return {
        "index": {
            "meta": {
                "schemaVersion": "1",
                "source": "github-discussions",
                "generatedAt": generatedAt,
                "skillCount": 0,
                "trustPolicy": "community market entries are untrusted until curated",
                "emptyReason": reason,
            },
            "skills": [],
        },
        "credits": {
            "meta": {
                "schemaVersion": "1",
                "generatedAt": generatedAt,
                "policy": "DartLab credit ledger, independent from GitHub repository contributors graph",
            },
            "skills": [],
        },
        "graph": {
            "meta": {"schemaVersion": "1", "generatedAt": generatedAt},
            "nodes": [],
            "edges": [],
        },
    }


def upsertForgeComment(client: GraphqlClient, discussionId: str, skill: dict[str, Any]) -> None:
    existingId = findForgeCommentId(client, discussionId)
    body = forgeCommentBody(skill)
    if existingId:
        client.call(
            """
            mutation($id:ID!, $body:String!) {
              updateDiscussionComment(input:{commentId:$id, body:$body}) { comment { id } }
            }
            """,
            {"id": existingId, "body": body},
        )
        return
    client.call(
        """
        mutation($id:ID!, $body:String!) {
          addDiscussionComment(input:{discussionId:$id, body:$body}) { comment { id } }
        }
        """,
        {"id": discussionId, "body": body},
    )


def findForgeCommentId(client: GraphqlClient, discussionId: str) -> str | None:
    data = client.call(
        """
        query($id:ID!) {
          node(id:$id) {
            ... on Discussion {
              comments(first:100) { nodes { id body author { login } } }
            }
          }
        }
        """,
        {"id": discussionId},
    )
    comments = ((data.get("node") or {}).get("comments") or {}).get("nodes") or []
    for comment in comments:
        if FORGE_MARKER in str(comment.get("body") or ""):
            return str(comment["id"])
    return None


def forgeCommentBody(skill: dict[str, Any]) -> str:
    missing = skill.get("missingDetails") or []
    missingText = ", ".join(missing) if missing else "없음"
    mapped = ", ".join(skill.get("mappedBuiltinSkills") or []) or "아직 없음"
    return textwrap.dedent(
        f"""\
        {FORGE_MARKER}
        **DartLab Forge 자동 초안**

        이 댓글은 커뮤니티 Skill Market 후보를 자동 구조화한 초안입니다. 공식 Skill OS 승인이나 curated 판정이 아닙니다.

        - 상태: `{skill.get("state")}`
        - trust tier: `{skill.get("trustTier")}`
        - 추정 의도: {skill.get("intent")}
        - 입력 후보: {", ".join(skill.get("inputs") or []) or "미정"}
        - 출력 후보: {", ".join(skill.get("outputs") or []) or "미정"}
        - 판단 기준: {", ".join(skill.get("criteria") or []) or "미정"}
        - 매핑된 builtin skill: {mapped}
        - 보완 필요: {missingText}

        작성자와 커뮤니티는 댓글로 입력, 출력, 판단 기준, 예시를 보완할 수 있습니다. Maintainer만 `/market curated`, `/market runnable`, `/market builtin-candidate`, `/market blocked` 명령으로 상태를 확정합니다.
        """
    ).strip()


def loadEventDiscussion() -> dict[str, Any] | None:
    eventPath = os.environ.get("GITHUB_EVENT_PATH")
    if not eventPath:
        return None
    try:
        payload = json.loads(Path(eventPath).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    discussion = payload.get("discussion")
    return discussion if isinstance(discussion, dict) else None


def curatorSet(owner: str) -> set[str]:
    raw = os.environ.get("DARTLAB_MARKET_CURATORS") or owner
    return {item.strip() for item in raw.split(",") if item.strip()}


def trustRank(tier: str) -> int:
    return {
        "marketCurated": 4,
        "builtinCandidate": 3,
        "marketRunnable": 2,
        "marketDraft": 1,
        "blocked": 0,
    }.get(tier, 0)


def normalizeText(text: str) -> str:
    return text.replace("\r\n", "\n").strip()


def splitItems(text: str) -> list[str]:
    return [item.strip(" ,;") for item in re.split(r"[,;/]| · |ㆍ", text) if item.strip(" ,;")]


def dedupeClean(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        clean = re.sub(r"\s+", " ", value).strip(" -*`")
        if clean and clean not in out:
            out.append(clean)
    return out


def firstParagraph(text: str) -> str:
    for part in re.split(r"\n\s*\n", text):
        lines = [line for line in part.splitlines() if not line.strip().startswith("#")]
        clean = re.sub(r"\s+", " ", "\n".join(lines)).strip()
        if clean:
            return clean[:500]
    return ""


def firstSentence(text: str) -> str:
    paragraph = firstParagraph(text)
    if not paragraph:
        return ""
    parts = re.split(r"(?<=[.!?。])\s+|다\.\s*", paragraph, maxsplit=1)
    return (parts[0] + ("다." if "다." in paragraph and not parts[0].endswith("다.") else ""))[:220]


def stableSlug(title: str) -> str:
    base = re.sub(r"[^a-z0-9가-힣]+", "-", title.lower()).strip("-")
    if not base:
        base = hashlib.sha1(title.encode("utf-8")).hexdigest()[:8]
    return base[:48].strip("-") or "skill"


if __name__ == "__main__":
    raise SystemExit(main())
