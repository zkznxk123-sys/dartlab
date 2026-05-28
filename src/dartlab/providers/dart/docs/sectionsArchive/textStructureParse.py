"""sections textStructure 파서 진입점 — textStructure.py 분할 (규칙 3 LoC).

parseTextStructureWithState / parseTextStructure — 본문 텍스트를 heading 계층 +
segment 트리로 변환하는 메인 파서.
"""

from __future__ import annotations

from typing import Any

from dartlab.providers.dart.docs.sectionsArchive.textStructure import (
    _bodyAnchor,
    _canonicalHeadingKey,
    _cleanLine,
    _detectHeading,
    _headingKey,
    _normalizeHeadingText,
    _repairLineBreaks,
    _semanticSegmentKey,
    _splitInlineMultiHeading,
)


def parseTextStructureWithState(
    text: str,
    *,
    sourceBlockOrder: int,
    topic: str | None = None,
    initialHeadings: list[dict[str, Any]] | None = None,
    promoteKorean: bool | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, Any]], bool]:
    """텍스트를 소제목 계층 구조로 파싱하고, 최종 heading stack도 함께 반환한다.

    Args:
        text: 인자.
        sourceBlockOrder: 인자.
        topic: 인자.
        initialHeadings: 인자.

    Raises:
        없음.

    Example:
        >>> parseTextStructureWithState(...)

    Returns:
        tuple[list[dict], list[dict]] — (노드, 엣지) 페어.
    """
    nodes: list[dict[str, object]] = []
    # Copy-on-write — shallow list copy 만 (items dict ref 공유). 후속 mutation
    # (item['label'] = ...) 시점에 해당 item 만 dict() copy 후 교체 (line 873-877).
    # 메모리 churn 감소: 13k 호출 × ~5 stack items = ~65k dict copy 회피.
    stack: list[dict[str, object]] = list(initialHeadings or [])
    bodyLines: list[str] = []
    segmentOrder = 0

    def flushBody() -> None:
        """누적 bodyLines 를 body 노드 1 개로 flush — segmentOrder 증가 + 다음 line 대비 buffer 비움.

        Raises:
            없음.

        Example:
            >>> flushBody()
        """
        nonlocal bodyLines, segmentOrder
        body = "\n".join(bodyLines).strip()
        bodyLines = []
        if not body:
            return

        # 1 패스 — body flush 시 stack → 5 path 문자열 동시 생성.
        pathLabels: list[str] = []
        pathKeys: list[str] = []
        semanticPathKeys: list[str] = []
        for item in stack:
            pathLabels.append(str(item["label"]))
            k = str(item["key"])
            if k:
                pathKeys.append(k)
            sk = str(item["semanticKey"])
            if sk:
                semanticPathKeys.append(sk)
        pathText = " > ".join(pathLabels) if pathLabels else None
        pathKey = " > ".join(pathKeys) if pathKeys else None
        parentPathKey = " > ".join(pathKeys[:-1]) if len(pathKeys) > 1 else None
        semanticPathKey = " > ".join(semanticPathKeys) if semanticPathKeys else None
        semanticParentPathKey = " > ".join(semanticPathKeys[:-1]) if len(semanticPathKeys) > 1 else None
        level = int(stack[-1]["level"]) if stack else 0
        anchor = _bodyAnchor(body)
        # Text row identity should follow outline path first.
        # Raw coarse block order is preserved separately as sourceBlockOrder.
        stableKeyBase = f"body|p:{semanticPathKey}" if semanticPathKey else f"body|lv:{level}|a:{anchor}"
        nodes.append(
            {
                "textNodeType": "body",
                "textStructural": True,
                "textLevel": level,
                "textPath": pathText,
                "textPathKey": pathKey,
                "textParentPathKey": parentPathKey,
                "textSemanticPathKey": semanticPathKey,
                "textSemanticParentPathKey": semanticParentPathKey,
                "segmentOrder": segmentOrder,
                "segmentKeyBase": stableKeyBase,
                "text": body,
            }
        )
        segmentOrder += 1

    # parquet 본문 줄바꿈 누락 회사 (현대모비스 등) — 한국어 종결사 후 한글 heading
    # prefix 등장 시 줄바꿈 복원. 정규화 후 line 단위 처리.
    text = _repairLineBreaks(text)
    rawLines = text.splitlines()
    splitLines: list[str] = []
    for rawLine in rawLines:
        cleaned = _cleanLine(rawLine)
        s = cleaned.strip()
        if not s:
            splitLines.append("")
            continue
        # parquet 본문 줄바꿈 누락 회사 (하나금융/신한지주/현대모비스 등) 정규화 —
        # 한 줄 안 multi-heading prefix 를 별 line 으로 분리.
        splitLines.extend(_splitInlineMultiHeading(s))

    # chunk 내 위계 추론 — 첫 detected heading 의 prefix 가 한글이면 한글이 contextual
    # root, numeric "1./2." 는 한글의 child (level 4) 로 강등. DART 본문 위계 표준
    # (numeric > 한글) 이 비표준 본문 (현대차/LG/삼성물산 등 "가. ... / 1. ...
    # sub-numbering" 구조) 에서 역전되어 후속 한글 sibling 들이 numeric 의 sub 로
    # 박히는 회귀 차단. Roman 은 항상 chapter top 이라 강등 대상 X.
    # promoteKorean 파라미터: None = chunk 첫 heading 으로 결정, True/False = 강제
    # (topic-level sticky). expansion.py 가 topic 단위 sticky 보관.
    effectivePromoteKorean: bool
    if promoteKorean is None:
        effectivePromoteKorean = False
        for s in splitLines:
            if not s:
                continue
            h = _detectHeading(s)
            if h is None:
                continue
            firstLevel = h[0]
            if firstLevel == 3:  # 한글이 chunk root
                effectivePromoteKorean = True
            break  # 첫 heading 만 봄
    else:
        effectivePromoteKorean = bool(promoteKorean)

    for stripped in splitLines:
        if not stripped:
            if bodyLines:
                bodyLines.append("")
            continue

        heading = _detectHeading(stripped)
        if heading is None:
            bodyLines.append(stripped)
            continue

        flushBody()
        level, label, structural = heading
        # 한글 contextual root chunk 안 numeric heading → 한글 (level 3) 의 child (4)
        if effectivePromoteKorean and level == 2:
            level = 4
        labelText = _normalizeHeadingText(label)
        labelKey = _headingKey(label)
        stackKey = _canonicalHeadingKey(labelText, labelKey, level=level, topic=topic)
        semanticStackKey = _semanticSegmentKey(stackKey, topic=topic)
        # @topic alias 가 stack 의 *어느 위치든* 중복이면 alias marker 처리.
        # 이전 룰은 stack[-1] 만 검사 → 다른 heading 사이에 끼인 같은 @topic alias 가
        # stack 깊은 위치에 살아있어도 다시 push 되어 "@topic > X > @topic" 같은
        # 누적 chain 발생. semantic 위배. stack 전체 검사로 차단.
        redundantTopicAlias = (
            structural
            and bool(stack)
            and str(stackKey).startswith("@topic:")
            and any(str(item["key"]) == stackKey for item in stack)
        )

        if structural and not redundantTopicAlias:
            while stack and int(stack[-1]["level"]) >= level:
                stack.pop()
            stack.append({"level": level, "label": labelText, "key": stackKey, "semanticKey": semanticStackKey})
            # 1 패스 — 3 list comprehension 통합 (expansion.py _headingPathStrings 와 동일 패턴).
            pathLabels: list[str] = []
            pathKeys: list[str] = []
            semanticPathKeys: list[str] = []
            for item in stack:
                pathLabels.append(str(item["label"]))
                k = str(item["key"])
                if k:
                    pathKeys.append(k)
                sk = str(item["semanticKey"])
                if sk:
                    semanticPathKeys.append(sk)
            pathText = " > ".join(pathLabels) if pathLabels else None
            pathKey = " > ".join(pathKeys) if pathKeys else None
            parentPathKey = " > ".join(pathKeys[:-1]) if len(pathKeys) > 1 else None
            semanticPathKey = " > ".join(semanticPathKeys) if semanticPathKeys else None
            semanticParentPathKey = " > ".join(semanticPathKeys[:-1]) if len(semanticPathKeys) > 1 else None
            # heading segmentKey 는 path 만 — level prefix 제거 (SSOT 정공법).
            # 옛 룰 `heading|lv:{level}|p:{path}` 은 같은 path 인데 source format
            # 차이로 level 만 다른 경우 (예: 기간 A 가 "가. X" 한글 L=3, 기간 B 가
            # "1. X" numeric L=2) segmentKey 분리 → 같은 의미 다른 row 위배.
            # path 가 stack 끝 자신 포함이므로 ancestor chain + label 동일 = 같은 heading.
            segmentKeyBase = f"heading|p:{semanticPathKey or semanticStackKey}"
        else:
            # redundantTopicAlias 인 경우 — 같은 @topic alias 의 sibling sub-section.
            # 1) stack 의 해당 entry label 을 latest 로 갱신 → 자식 textPath 정확.
            # 2) 그 entry 이후의 *모든* descendant pop — 직전 sub-section 의 stack
            #    entry (L=7 bracket marker / 등) 가 새 sibling 의 descendant 로 오염되는
            #    회귀 차단.
            #
            # 회귀 사례 (000660 companyOverview bo=16): 직전 "가. 연결대상 종속회사 개황"
            # sub-section 후 [연결대상회사의 변동내용] L=7 push → stack [@topic, L:7].
            # 새 "나. 회사의 법적·상업적 명칭" alias 가 redundantTopicAlias. 옛 룰은
            # label 만 갱신 → stack [@topic(label:법적·상업적 명칭), L:7] 잔존 → 후속 body
            # textPath = "회사의 법적·상업적 명칭 > 연결대상회사의 변동내용" 오염.
            # 정공법: alias entry 이후 stack 모두 pop.
            if redundantTopicAlias:
                aliasIdx: int | None = None
                for i, item in enumerate(stack):
                    if str(item["key"]) == stackKey:
                        aliasIdx = i
                        # Copy-on-write: stack 의 item 은 initialHeadings 와 공유 가능.
                        # mutation 직전 단일 item dict copy 후 교체.
                        newItem = dict(item)
                        newItem["label"] = labelText
                        stack[i] = newItem
                        break
                if aliasIdx is not None and aliasIdx + 1 < len(stack):
                    del stack[aliasIdx + 1 :]
            currentPathKeys = [str(item["key"]) for item in stack if str(item["key"])]
            currentSemanticPathKeys = [str(item["semanticKey"]) for item in stack if str(item["semanticKey"])]
            pathText = labelText
            keyPrefix = "@alias" if redundantTopicAlias else "@marker"
            pathKey = f"{keyPrefix}:{labelKey}"
            parentPathKey = " > ".join(currentPathKeys) if currentPathKeys else None
            semanticPathKey = pathKey
            semanticParentPathKey = " > ".join(currentSemanticPathKeys) if currentSemanticPathKeys else None
            segmentKind = "alias" if redundantTopicAlias else "marker"
            segmentKeyBase = f"heading|{segmentKind}|lv:{level}|p:{pathKey}"
        nodes.append(
            {
                "textNodeType": "heading",
                "textStructural": structural and not redundantTopicAlias,
                "textLevel": level,
                "textPath": pathText,
                "textPathKey": pathKey,
                "textParentPathKey": parentPathKey,
                "textSemanticPathKey": semanticPathKey,
                "textSemanticParentPathKey": semanticParentPathKey,
                "segmentOrder": segmentOrder,
                "segmentKeyBase": segmentKeyBase,
                "text": stripped,
            }
        )
        segmentOrder += 1

    flushBody()
    return nodes, [dict(item) for item in stack], effectivePromoteKorean


def parseTextStructure(
    text: str,
    *,
    sourceBlockOrder: int,
    topic: str | None = None,
) -> list[dict[str, object]]:
    """텍스트를 소제목 계층 구조로 파싱하여 노드 리스트를 반환한다.

    Args:
        text: 인자.
        sourceBlockOrder: 인자.
        topic: 인자.

    Raises:
        없음.

    Example:
        >>> parseTextStructure(...)

    Returns:
        list[dict] — 결과 dict 리스트.
    """
    nodes, _stack, _promote = parseTextStructureWithState(text, sourceBlockOrder=sourceBlockOrder, topic=topic)
    return nodes
