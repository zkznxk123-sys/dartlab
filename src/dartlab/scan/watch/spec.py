"""watch 엔진 스펙 — 코드에서 자동 추출."""

from __future__ import annotations


def buildSpec() -> dict:
    """watch 엔진 스펙을 코드에서 자동 추출하여 반환한다.

    Returns
    -------
    dict
        watch 엔진 메타 정보. 구조:

        - name : str — 엔진명 ("watch")
        - description : str — 엔진 설명
        - summary : dict
            - scoringFactors : int — 스코어링 요소 수
            - highWeightTopics : int — 고가중 topic 수
            - lowWeightTopics : int — 저가중 topic 수
            - maxScore : int — 최대 점수 (점, 100)
        - detail : dict
            - scoringFactors : list[str] — 스코어링 요소 설명
            - highWeightTopics : list[str] — 고가중 topic 목록
            - lowWeightTopics : list[str] — 저가중 topic 목록
            - publicAPI : list[str] — 공개 API 사용법
    """
    from dartlab.scan.watch.scorer import _HIGH_WEIGHT_TOPICS, _LOW_WEIGHT_TOPICS

    return {
        "name": "watch",
        "description": "sections diff 기반 공시 변화 감지 + 중요도 스코어링",
        "summary": {
            "scoringFactors": 4,
            "highWeightTopics": len(_HIGH_WEIGHT_TOPICS),
            "lowWeightTopics": len(_LOW_WEIGHT_TOPICS),
            "maxScore": 100,
        },
        "detail": {
            "scoringFactors": [
                "changeRate 기반 기본 점수 (최대 50점)",
                "topic 유형 가중치 (핵심 경영 1.5x, 저가중 0.6x)",
                "텍스트 크기 변화율 (최대 30점)",
                "트렌드/리스크 키워드 매칭 (최대 20점)",
            ],
            "highWeightTopics": sorted(_HIGH_WEIGHT_TOPICS),
            "lowWeightTopics": sorted(_LOW_WEIGHT_TOPICS),
            "publicAPI": [
                "Company.watch() — 단일 기업 변화 요약",
                "Company.watch(topic) — 특정 topic 상세",
                "dartlab.digest() — 시장 전체 다이제스트",
                "dartlab.digest(sector=) — 섹터별 다이제스트",
            ],
        },
    }
