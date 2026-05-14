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
import urllib.error
import urllib.request
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "landing" / "static" / "skills" / "market"
FORGE_MARKER = "<!-- dartlab-skill-market-forge -->"
BOT_LOGINS = {"github-actions[bot]", "dependabot[bot]"}
ACCEPTED_SNAPSHOT_STATES = {"curated", "builtin-candidate"}
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
    skills, items = prepareMarketSnapshots(skills, outDir=outDir, generatedAt=generatedAt)
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
        "items": items,
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
            lastEditedAt
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
    revision = revisionState(discussion, comments, moderation)
    itemId = f"market.{stableSlug(title)}.{discussion.get('number')}"
    itemPath = f"items/{itemId}.json"
    hasAcceptedSnapshot = (
        state in ACCEPTED_SNAPSHOT_STATES and bool(revision["acceptedAt"]) and not parsed["missingDetails"]
    )
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
        "dataSources": parsed["dataSources"],
        "procedure": parsed["procedure"],
        "executionPlan": parsed["executionPlan"],
        "outputSchema": parsed["outputSchema"],
        "criteria": parsed["criteria"],
        "forbidden": parsed["forbidden"],
        "completionCriteria": parsed["completionCriteria"],
        "examples": parsed["examples"],
        "tags": parsed["tags"],
        "state": state,
        "trustTier": trustTier,
        "missingDetails": parsed["missingDetails"],
        "warnings": parsed["warnings"],
        "mappedBuiltinSkills": parsed["mappedBuiltinSkills"],
        "canonicalSource": "marketItemSnapshot" if hasAcceptedSnapshot else "githubDiscussion",
        "itemPath": itemPath if hasAcceptedSnapshot else None,
        "acceptedAt": revision["acceptedAt"] if hasAcceptedSnapshot else None,
        "canonicalUpdatedAt": revision["canonicalUpdatedAt"],
        "finalizedAt": revision["finalizedAt"],
        "revisionStatus": revision["revisionStatus"],
        "pendingCommentCount": revision["pendingCommentCount"],
        "pendingCommentUrls": revision["pendingCommentUrls"],
        "pendingSince": revision["pendingSince"],
        "revisionPolicy": "Accepted market item snapshots are canonical. Later comments do not change the final skill until reviewed and accepted.",
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
    dataSources = extractList(text, ("데이터 소스 후보", "데이터 소스", "자료", "data sources", "sources"))
    procedure = extractList(text, ("실행 절차", "절차", "procedure", "steps"))
    executionPlan = extractExecutionPlan(text)
    outputs = extractList(text, ("기대 결과", "결과", "출력", "outputs", "output"))
    outputSchema = extractList(text, ("출력 스키마", "스키마", "output schema", "schema"))
    criteria = extractList(text, ("판단 기준", "기준", "판단", "criteria", "threshold"))
    forbidden = extractList(text, ("금지와 한계", "금지", "한계", "forbidden", "limitations"))
    completionCriteria = extractList(text, ("완료 기준", "완성 기준", "completion criteria", "done criteria"))
    examples = extractList(text, ("예시 질문", "예시", "example", "examples"))
    if not inputs:
        inputs = inferInputs(text)
    if not outputs:
        outputs = inferOutputs(text)
    if not outputSchema:
        outputSchema = inferOutputSchema(text, outputs)
    if not criteria:
        criteria = inferCriteria(text)
    mappedBuiltinSkills = mapBuiltinSkills(f"{title}\n{text}")
    if not hasExecutablePlan(executionPlan):
        executionPlan = inferExecutionPlan(mappedBuiltinSkills, outputs, criteria)
    if not examples:
        examples = inferExamples(title, inputs, outputs, criteria)
    explicitMissingDetails = extractList(text, ("보완 필요", "남은 질문", "needs detail", "missing details"))
    warnings = [pattern for pattern in BLOCK_PATTERNS if pattern.lower() in text.lower()]
    missingDetails: list[str] = []
    if not inputs:
        missingDetails.append("inputs")
    if not outputs:
        missingDetails.append("outputs")
    if not criteria:
        missingDetails.append("criteria")
    if not hasExecutablePlan(executionPlan):
        missingDetails.append("DartLab 엔진별 executionPlan")
    if not examples:
        missingDetails.append("예시 입력과 기대 출력")
    missingDetails = dedupeClean([*missingDetails, *explicitMissingDetails])
    isExplicitDraft = any(
        marker in text.lower()
        for marker in (
            "초안 상태",
            "아직 최종 스킬이 아닙니다",
            "아직 완성 스킬이 아닙니다",
            "needs detail",
            "missing details",
        )
    )
    state = (
        "blocked"
        if warnings
        else "specified"
        if isExplicitDraft
        else "runnable"
        if not missingDetails
        else "specified"
        if inputs or outputs
        else "idea"
    )
    return {
        "summary": firstSentence(text) or title,
        "intent": firstParagraph(text) or title,
        "inputs": inputs,
        "dataSources": dataSources,
        "procedure": procedure,
        "executionPlan": executionPlan,
        "outputs": outputs,
        "outputSchema": outputSchema,
        "criteria": criteria,
        "forbidden": forbidden,
        "completionCriteria": completionCriteria,
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
        match = re.match(
            rf"^(?:#+\s*)?(?:{labelPattern})(?:\s*[:：]\s*(.*)|\s*)$",
            stripped,
            flags=re.IGNORECASE,
        )
        if not match:
            continue
        inline = (match.group(1) or "").strip(" -")
        if inline:
            values.extend(splitItems(inline))
        for follow in lines[index + 1 : index + 20]:
            item = follow.strip()
            if not item:
                if values:
                    break
                continue
            if item.startswith("#"):
                break
            if re.match(r"^(?:#+\s*)?[\w가-힣 ]+\s*[:：]\s*", item) and not item.startswith(("-", "*")):
                break
            if item.startswith(("-", "*")):
                values.append(item[1:].strip())
            elif re.match(r"^\d+[.)]\s+", item):
                values.append(re.sub(r"^\d+[.)]\s+", "", item).strip())
            elif values:
                values.extend(splitItems(item))
    return dedupeClean(values)[:8]


def extractExecutionPlan(text: str) -> list[dict[str, Any]]:
    steps = extractList(
        text,
        (
            "DartLab 실행 계획",
            "실행 계획",
            "엔진 호출",
            "엔진 실행",
            "execution plan",
            "engine calls",
        ),
    )
    out: list[dict[str, Any]] = []
    for index, step in enumerate(steps, start=1):
        engineMatch = re.search(r"\b(?:engines|recipes|runtime|start|operation)\.[A-Za-z0-9_.]+", step)
        out.append(
            {
                "step": index,
                "engine": engineMatch.group(0) if engineMatch else None,
                "purpose": step,
                "inputs": [],
                "outputs": [],
                "failureMode": None,
            }
        )
    return out


def hasExecutablePlan(executionPlan: list[dict[str, Any]]) -> bool:
    return any(step.get("engine") for step in executionPlan)


def inferExecutionPlan(
    mappedBuiltinSkills: list[str],
    outputs: list[str],
    criteria: list[str],
) -> list[dict[str, Any]]:
    if not mappedBuiltinSkills:
        return []
    purposeBits = [*outputs[:3], *criteria[:1]]
    purpose = " / ".join(purposeBits) if purposeBits else "discussion criteria"
    return [
        {
            "step": index,
            "engine": engine,
            "purpose": f"{purpose} 산출",
            "inputs": [],
            "outputs": outputs[:4],
            "failureMode": None,
        }
        for index, engine in enumerate(mappedBuiltinSkills[:4], start=1)
    ]


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


def inferOutputSchema(text: str, outputs: list[str]) -> list[str]:
    haystack = f"{text}\n{' '.join(outputs)}".lower()
    schema: list[str] = []
    if any(term in haystack for term in ("서프라이즈", "surprise")):
        schema.append("surpriseScore: number")
    if any(term in haystack for term in ("정책", "policy", "중앙은행", "fed", "금통위")):
        schema.append("policyImpact: string")
    if any(term in haystack for term in ("금리", "환율", "주식", "수익률", "asset", "market")):
        schema.append("assetReaction: table")
    if any(term in haystack for term in ("섹터", "업종", "sector")):
        schema.append("sectorReaction: table")
    if any(term in haystack for term in ("체크포인트", "다음", "next")):
        schema.append("nextChecks: list[str]")
    if schema:
        schema.append("refs: {skillRef, sourceRef, tableRef, valueRef}")
    return dedupeClean(schema)[:8]


def inferCriteria(text: str) -> list[str]:
    candidates = []
    for line in text.splitlines():
        if any(term in line for term in ("이상", "이하", "미만", "초과", "배", "%", "warning", "위험")):
            candidates.append(line.strip(" -*"))
    return dedupeClean(candidates)[:6]


def inferExamples(title: str, inputs: list[str], outputs: list[str], criteria: list[str]) -> list[str]:
    if not (inputs and outputs and criteria):
        return []
    return [(f"{title}: inputs={', '.join(inputs[:3])} -> outputs={', '.join(outputs[:3])}; criteria={criteria[0]}")]


def mapBuiltinSkills(text: str) -> list[str]:
    lowered = text.lower()
    mapping = [
        (("현금흐름", "cfo", "cashflow"), "engines.analysis.cashflow"),
        (("성장", "매출", "growth"), "engines.analysis.growth"),
        (("peer", "비교", "횡단"), "engines.scan"),
        (("신용", "부도", "credit"), "engines.credit"),
        (("거시", "금리", "macro"), "engines.macro"),
        (("fred", "ecos", "bok", "한국은행", "경제 원자료", "gather"), "engines.gather.macro"),
        (("cpi", "fomc", "금통위", "경제 이벤트", "서프라이즈"), "engines.macro.rates"),
        (("고용", "실업률", "침체확률"), "engines.macro.forecast"),
        (("섹터", "업종", "sector"), "recipes.macro.sectorRotation"),
        (("시계열", "차트", "그래프", "time series"), "recipes.macro.timeSeriesChart"),
        (("퀀트", "팩터", "quant"), "engines.quant"),
        (("산업", "밸류체인", "industry"), "engines.industry"),
        (("공시", "disclosure", "filing"), "engines.search"),
        (("종합", "deep", "깊게"), "recipes.credit.deepDive"),
    ]
    out: list[str] = []
    for terms, skillId in mapping:
        if any(term.lower() in lowered for term in terms):
            out.append(skillId)
    return dedupeClean(out)[:12]


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
    return dedupeClean(tags)[:6]


def readModeratorState(comments: list[dict[str, Any]], curatorLogins: set[str]) -> dict[str, Any]:
    state = None
    curators: set[str] = set()
    updatedAt = ""
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
            updatedAt = max(updatedAt, str(comment.get("updatedAt") or ""))
        elif any(command.startswith("/market builtin-candidate") for command in commands):
            state = "builtin-candidate"
            curators.add(author)
            updatedAt = max(updatedAt, str(comment.get("updatedAt") or ""))
        elif any(command.startswith("/market runnable") for command in commands):
            state = "runnable"
            curators.add(author)
            updatedAt = max(updatedAt, str(comment.get("updatedAt") or ""))
        elif any(command.startswith("/market blocked") for command in commands):
            state = "blocked"
            curators.add(author)
            updatedAt = max(updatedAt, str(comment.get("updatedAt") or ""))
    trustTier = {
        "curated": "marketCurated",
        "builtin-candidate": "builtinCandidate",
        "runnable": "marketRunnable",
        "blocked": "blocked",
    }.get(state or "")
    return {"state": state, "trustTier": trustTier, "curators": curators, "updatedAt": updatedAt}


def revisionState(
    discussion: dict[str, Any],
    comments: list[dict[str, Any]],
    moderation: dict[str, Any],
) -> dict[str, Any]:
    canonicalUpdatedAt = str(discussion.get("lastEditedAt") or discussion.get("updatedAt") or "")
    acceptedAt = str(moderation.get("updatedAt") or "")
    finalizedAt = acceptedAt or canonicalUpdatedAt
    pending = [
        comment
        for comment in comments
        if isRevisionComment(comment) and str(comment.get("updatedAt") or "") > finalizedAt
    ]
    bodyPending = bool(acceptedAt and canonicalUpdatedAt > acceptedAt)
    pending.sort(key=lambda item: str(item.get("updatedAt") or ""))
    return {
        "canonicalUpdatedAt": canonicalUpdatedAt or None,
        "acceptedAt": acceptedAt or None,
        "finalizedAt": finalizedAt or None,
        "revisionStatus": "pendingReview" if pending or bodyPending else "current",
        "pendingCommentCount": len(pending),
        "pendingCommentUrls": [str(comment.get("url") or "") for comment in pending[:8] if comment.get("url")],
        "pendingSince": str(pending[0].get("updatedAt") or "")
        if pending
        else canonicalUpdatedAt
        if bodyPending
        else None,
    }


def isRevisionComment(comment: dict[str, Any]) -> bool:
    author = ((comment.get("author") or {}).get("login")) or ""
    body = str(comment.get("body") or "")
    if not author or author in BOT_LOGINS:
        return False
    if FORGE_MARKER in body:
        return False
    stripped = body.strip().lower()
    if stripped.startswith("/market "):
        return False
    return bool(stripped)


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


REVISION_FIELDS = (
    "revisionStatus",
    "pendingCommentCount",
    "pendingCommentUrls",
    "pendingSince",
    "revisionPolicy",
    "canonicalUpdatedAt",
    "finalizedAt",
)


def prepareMarketSnapshots(
    skills: list[dict[str, Any]],
    *,
    outDir: Path,
    generatedAt: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    indexed: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    for skill in skills:
        if not skill.get("itemPath"):
            indexed.append(skill)
            continue
        previous = readPreviousSnapshot(outDir / str(skill.get("itemPath") or ""))
        if skill.get("revisionStatus") == "pendingReview" and previous:
            snapshot = dict(previous)
            for key in REVISION_FIELDS:
                snapshot[key] = skill.get(key)
            snapshot["sourceDiscussionUpdatedAt"] = skill.get("updatedAt")
        else:
            previousVersion = int(previous.get("version") or 0) if previous else 0
            previousAcceptedAt = str(previous.get("acceptedAt") or "") if previous else ""
            acceptedAt = str(skill.get("acceptedAt") or "")
            version = previousVersion if previousVersion and previousAcceptedAt == acceptedAt else previousVersion + 1
            snapshot = {
                "schemaVersion": "1",
                "snapshotType": "marketSkill",
                "version": max(1, version),
                "snapshotGeneratedAt": generatedAt,
                **skill,
            }
        indexed.append(snapshot)
        snapshots.append(snapshot)
    return indexed, snapshots


def readPreviousSnapshot(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) and data.get("id") else None


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
    itemDir = outDir / "items"
    itemDir.mkdir(parents=True, exist_ok=True)
    files = {
        "marketIndex.json": payload["index"],
        "marketCredits.json": payload["credits"],
        "marketGraph.json": payload["graph"],
    }
    for name, data in files.items():
        (outDir / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    currentItemPaths = {str(item.get("itemPath") or "") for item in payload.get("items") or []}
    for stalePath in itemDir.glob("*.json"):
        rel = stalePath.relative_to(outDir).as_posix()
        if rel not in currentItemPaths:
            stalePath.unlink()
    for item in payload.get("items") or []:
        itemPath = outDir / str(item.get("itemPath") or "")
        if itemPath.parent != itemDir:
            continue
        itemPath.write_text(json.dumps(item, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[skill-market] wrote {len(files)} index files and {len(payload.get('items') or [])} item files to {outDir}")


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


def markdownBullets(values: list[Any], *, emptyText: str, limit: int = 5) -> str:
    clean = dedupeClean(str(value).strip() for value in values if str(value).strip())
    if not clean:
        return f"- {emptyText}"
    lines = [f"- {value}" for value in clean[:limit]]
    if len(clean) > limit:
        lines.append(f"- 외 {len(clean) - limit}개")
    return "\n".join(lines)


def markdownInline(values: list[Any], *, emptyText: str, limit: int = 6) -> str:
    clean = dedupeClean(str(value).strip() for value in values if str(value).strip())
    if not clean:
        return emptyText
    shown = clean[:limit]
    suffix = f", 외 {len(clean) - limit}개" if len(clean) > limit else ""
    return ", ".join(f"`{value}`" for value in shown) + suffix


def markdownExecutionPlan(values: list[dict[str, Any]], *, limit: int = 5) -> str:
    if not values:
        return "- 정해지지 않았습니다."
    lines: list[str] = []
    for step in values[:limit]:
        engine = step.get("engine") or "엔진 미정"
        purpose = step.get("purpose") or "목적 미정"
        lines.append(f"- `{engine}` - {purpose}")
    if len(values) > limit:
        lines.append(f"- 외 {len(values) - limit}개")
    return "\n".join(lines)


def forgeCommentBody(skill: dict[str, Any]) -> str:
    missing = skill.get("missingDetails") or []
    missingText = markdownInline(missing, emptyText="없습니다.", limit=8)
    mapped = markdownInline(skill.get("mappedBuiltinSkills") or [], emptyText="없습니다.", limit=5)
    inputs = markdownBullets(skill.get("inputs") or [], emptyText="정해지지 않았습니다.", limit=5)
    executionPlan = markdownExecutionPlan(skill.get("executionPlan") or [], limit=5)
    outputs = markdownBullets(skill.get("outputs") or [], emptyText="정해지지 않았습니다.", limit=5)
    criteria = markdownBullets(skill.get("criteria") or [], emptyText="정해지지 않았습니다.", limit=4)
    completionCriteria = markdownBullets(
        skill.get("completionCriteria") or [],
        emptyText="정해지지 않았습니다.",
        limit=4,
    )
    revisionStatus = str(skill.get("revisionStatus") or "current")
    pendingCount = int(skill.get("pendingCommentCount") or 0)
    revisionText = (
        f"후속 댓글 {pendingCount}개가 검토 대기 중입니다."
        if revisionStatus == "pendingReview"
        else "후속 댓글 검토 대기는 없습니다."
    )
    itemPath = skill.get("itemPath") or "아직 없습니다."
    hasAcceptedSnapshot = bool(skill.get("itemPath") and skill.get("acceptedAt"))
    acceptedAt = skill.get("acceptedAt") if hasAcceptedSnapshot else "없습니다."
    version = skill.get("version") if hasAcceptedSnapshot else "없습니다."
    finalRule = (
        "랜딩과 AI가 읽는 최종 스킬은 accepted item snapshot입니다."
        if hasAcceptedSnapshot
        else "아직 랜딩과 AI가 실행 후보로 읽을 최종 스킬 snapshot이 없습니다."
    )
    nextAction = (
        "토론에서 입력, 출력, 데이터 소스, 실행 절차, 검증 기준을 더 채워야 합니다."
        if not hasAcceptedSnapshot
        else (
            "새 댓글은 최종본을 바로 바꾸지 않습니다. maintainer 검토 뒤 `/market curated`로 다시 확정합니다."
            if revisionStatus == "pendingReview"
            else "최종본 변경이 필요하면 댓글로 보강한 뒤 maintainer가 `/market curated`로 다시 확정합니다."
        )
    )
    body = f"""\
## DartLab Forge 상태판

이 댓글은 Skill Market 자동 상태판입니다. 공식 builtin Skill OS 승인이 아닙니다.

### 현재 상태
- 상태: `{skill.get("state")}`
- trust tier: `{skill.get("trustTier")}`
- revision status: `{revisionStatus}` - {revisionText}
- accepted snapshot: `{version}`
- accepted at: `{acceptedAt}`
- snapshot path: `{itemPath}`
- 보완 필요: {missingText}
- 매핑된 builtin skill: {mapped}

### 최종본 규칙
- Discussion 본문과 댓글은 토론 기록입니다.
- {finalRule}
- 패키지 builtin Skill OS에는 포함하지 않습니다.

### 스킬 요약
**입력**
{inputs}

**DartLab 실행 계획**
{executionPlan}

**출력**
{outputs}

**판단 기준**
{criteria}

**완료 기준**
{completionCriteria}

### 다음 액션
- {nextAction}
"""
    return f"{FORGE_MARKER}\n{body.strip()}"


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
    return text.replace("\r\n", "\n").lstrip("\ufeff").strip()


def splitItems(text: str) -> list[str]:
    return [item.strip(" ,;") for item in re.split(r"[,;/]| · |ㆍ", text) if item.strip(" ,;")]


def dedupeClean(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        clean = re.sub(r"\s+", " ", value).strip(" -*")
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
