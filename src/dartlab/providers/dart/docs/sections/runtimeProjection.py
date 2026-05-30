"""sections projection 분배 — _routeChapterIISegment / applyProjections.

runtime.py 921 LoC 분할 (룰 3 LoC 임계 회피). 본 모듈은 chapter II 합산 topic
을 학습된 projection 규칙으로 개별 topic 에 분배.
"""

from __future__ import annotations

from dartlab.providers.dart.docs.sections.artifacts import loadProjectionRules
from dartlab.providers.dart.docs.sections.runtime import (
    _CHAPTER_II_SPLIT_FALLBACK_TARGETS,
    _CHAPTER_II_SPLIT_SOURCE,
    splitByMajorHeading,
)


def _routeChapterIISegment(sourceTopic: str, label: str, body: str) -> str | None:
    joined = f"{label}\n{body}"
    if sourceTopic != _CHAPTER_II_SPLIT_SOURCE:
        return None
    if "원재료" in joined or "생산설비" in joined:
        return "rawMaterial"
    if "제품" in joined or "서비스" in joined:
        return "productService"
    return None


def applyProjections(
    rows: list[dict[str, object]],
    teacherTopics: dict[str, set[str]],
) -> list[dict[str, object]]:
    """chapter II 합산 topic 을 학습된 projection 규칙으로 개별 topic 에 분배한다.

    Capabilities:
        - ``loadProjectionRules("chapterII")`` 가 반환한 ``{sourceTopic: [targetTopic, ...]}``
          매핑으로 chapter II row 를 복제 분배.
        - ``주요제품및원재료등`` source 는 ``splitByMajorHeading`` 으로 본문 쪼개기 → 각
          segment 를 ``_routeChapterIISegment`` 키워드 매칭 (원재료/생산설비 → rawMaterial /
          제품/서비스 → productService) 로 분류 → 분류된 buffer 를 새 row 로 생성.
        - 분류 실패 segment 가 있어도 fallback 으로 ``rawMaterial`` / ``productService`` 양쪽에
          원본 전체 복제 (teacher 토픽 set 안에 있을 때 한정).
        - 일반 source → ``rules`` 가 명시한 target 으로 직접 row 복제 (sourceTopic/projectionKind
          메타 동행).
        - 이미 존재하는 ``(chapter, topic)`` 쌍은 skip (중복 방지).

    Args:
        rows: section rows. 각 row 는 ``chapter``/``topic``/``text``/``blockType``/``blockOrder``/
            ``majorNum``/``orderSeq`` 키 보유 (모두 optional 안전 처리).
        teacherTopics: ``chapterTeacherTopics`` 결과 — ``{chapter: {topic, ...}}``. 본 함수는
            ``teacherTopics["II"]`` 만 사용 (chapter II 한정 분배).

    Returns:
        list[dict[str, object]] — rows 복사본 + 새 분배 row 추가. 입력 rows 변형 X (immutable
        가드). projection 규칙이 비면 입력 그대로 반환.

    Example:
        >>> from dartlab.providers.dart.docs.sections.runtime import applyProjections
        >>> rows = [{"chapter": "II", "topic": "X", "text": "ABC", "blockType": "text", "blockOrder": 0}]
        >>> result = applyProjections(rows, {"II": {"X"}})
        >>> len(result) >= 1
        True

    Guide:
        - "정기보고서 chapter II 의 합산 topic 을 개별 항목으로 분배" → 본 함수.
        - "삼성전자 사업의 내용 II 장 product/raw 분리" → ``주요제품및원재료등`` source 가 자동
          분할 (``splitByMajorHeading`` + 키워드 라우팅).
        - 분배 후 row 는 ``sourceTopic`` + ``projectionKind`` 메타로 추적 가능.

    SeeAlso:
        - ``chapterTeacherTopics`` — 본 함수가 받는 ``teacherTopics`` 의 source.
        - ``splitByMajorHeading`` — chapter II split source 의 본문 분할 헬퍼.
        - ``loadProjectionRules`` (artifacts) — projection 매핑 SSOT (학습된 규칙).
        - ``_routeChapterIISegment`` (모듈 private) — 분할 segment 의 키워드 라우팅 로직.

    Requires:
        - dartlab.providers.dart.docs.sections.artifacts.loadProjectionRules — 매핑 source.
        - 본 모듈 함수 ``splitByMajorHeading`` / ``_routeChapterIISegment`` — 분할/라우팅.

    AIContext:
        Workbench 가 "이 회사 사업의 내용 II 장 어떤 항목들" 질문 처리 시 sections 파이프 final
        step 으로 호출. 본 함수 없으면 chapter II 가 합산 topic 1 개로 뭉뜽그려져 AI 가
        세부 topic 별 검색 불가. ``projectionKind="directRule"``/``"headingRule"`` 메타로
        분배 출처 추적 → 잘못 분배된 row 는 사용자 검토 시 trace 가능.

    LLM Specifications:
        AntiPatterns:
            - projection 매핑 (parserMapper) 가 비어 있음 → 입력 rows 그대로 반환 (silent).
            - teacherTopics["II"] 가 비어 있음 → 분배 0 (모든 후보 skip).
            - ``주요제품및원재료등`` 본문이 segment 키워드 ("제품"/"원재료") 없음 → fallback
              으로 양쪽 target 에 동일 본문 복제 → 중복성 발생 (의도된 보수적 분배).
            - input rows 변형 X — 본 함수는 list copy 후 append (caller 의 다른 사용 안전).
        OutputSchema:
            - row: 입력 N + 분배 추가 K = N+K rows. K 는 projection 매핑 + 분할 결과 의존.
            - 새 row 의 필수 필드: chapter/topic/text/blockType/blockOrder/majorNum/orderSeq/
              sourceTopic/projectionKind.
        Prerequisites:
            - loadProjectionRules 가 정상 (parserMapper 학습된 매핑 보유).
            - teacherTopics 가 chapterTeacherTopics 결과로 채워짐.
        Freshness:
            - projection 매핑은 학습 (sectioning pipeline) 결과 — 학습 갱신 시 본 함수 결과 변화.
        Dataflow:
            - sections pipeline (chunker → mapper) → chapterTeacherTopics → 본 함수 → 최종 rows
              (sections.parquet).
        TargetMarkets:
            - KR (DART) 정기보고서 chapter II ("사업의 내용") 한정. III 장 이후는 분배 X.

    Raises:
        없음.
    """
    if not rows:
        return rows

    rules = loadProjectionRules("chapterII")
    if not rules:
        return rows

    out = list(rows)
    existing = {
        (row["chapter"], row["topic"])
        for row in rows
        if isinstance(row.get("chapter"), str) and isinstance(row.get("topic"), str)
    }
    splitBuffers: dict[tuple[str, str], list[str]] = {}

    for row in rows:
        chapter = row.get("chapter")
        topic = row.get("topic")
        text = row.get("text")
        if chapter != "II" or not isinstance(topic, str) or not isinstance(text, str):
            continue

        if topic == _CHAPTER_II_SPLIT_SOURCE:
            segments = splitByMajorHeading(text) or [("(root)", text)]
            matchedTargets: set[str] = set()
            for label, body in segments:
                target = _routeChapterIISegment(topic, label, body)
                if not target or target not in teacherTopics.get("II", set()):
                    continue
                splitBuffers.setdefault((chapter, target), []).append(body)
                matchedTargets.add(target)
            for target in _CHAPTER_II_SPLIT_FALLBACK_TARGETS:
                if target not in teacherTopics.get("II", set()) or target in matchedTargets:
                    continue
                splitBuffers.setdefault((chapter, target), []).append(text)
            continue

        for target in rules.get(topic, []):
            if target not in teacherTopics.get("II", set()):
                continue
            key = (chapter, target)
            if key in existing:
                continue
            out.append(
                {
                    "chapter": chapter,
                    "topic": target,
                    "text": text,
                    "blockType": row.get("blockType", "text"),
                    "blockOrder": row.get("blockOrder", 0),
                    "majorNum": row.get("majorNum"),
                    "orderSeq": row.get("orderSeq"),
                    "sourceTopic": topic,
                    "projectionKind": "directRule",
                }
            )
            existing.add(key)

    for (chapter, target), bodies in splitBuffers.items():
        key = (chapter, target)
        if key in existing or not bodies:
            continue
        out.append(
            {
                "chapter": chapter,
                "topic": target,
                "text": "\n".join(bodies),
                "blockType": "text",
                "blockOrder": 0,
                "majorNum": 2,
                "orderSeq": 0,
                "sourceTopic": _CHAPTER_II_SPLIT_SOURCE,
                "projectionKind": "headingRule",
            }
        )
        existing.add(key)

    return out
