"""데이터 릴리즈 중앙 설정.

디렉토리, 라벨을 1곳에서 관리.
새 카테고리 추가 시 DATA_RELEASES에 한 줄만 추가하면 전체 반영.

모든 데이터는 HuggingFace 데이터셋(eddmpython/dartlab-data)에서 제공.
"""

HF_REPO = "eddmpython/dartlab-data"
HF_BASE_URL = f"https://huggingface.co/datasets/{HF_REPO}/resolve/main"

DATA_RELEASES: dict[str, dict] = {
    # ── 사용자 공개 (brand.ts 동기화 대상) ──
    "docs": {
        "dir": "dart/docs",
        "label": "DART 공시 문서 데이터",
        "public": True,
    },
    "finance": {
        "dir": "dart/finance",
        "label": "재무 숫자 데이터",
        "public": True,
    },
    "report": {
        "dir": "dart/report",
        "label": "정기보고서 데이터",
        "public": True,
    },
    "scan": {
        "dir": "dart/scan",
        "label": "전종목 횡단분석 프리빌드 데이터",
        "public": True,
    },
    "edgarDocs": {
        "dir": "edgar/docs",
        "label": "SEC EDGAR 공시 문서 데이터",
        "public": True,
    },
    "edgar": {
        "dir": "edgar/finance",
        "label": "SEC EDGAR 재무 데이터 (companyfacts.zip 벌크 파생)",
        "public": True,
    },
    "edgarMeta": {
        "dir": "edgar/meta",
        "label": "SEC EDGAR 분기 벌크 메타 (sub/pre/tag)",
        "public": True,
    },
    "krxPrices": {
        "dir": "krx/prices",
        "label": "KRX 일별 전종목 OHLCV+시총+발행주식수 (raw, long parquet)",
        "public": True,
    },
    # ── generated artifact (landing 빌드 시 HF 에서 fetch) ──
    "industryMap": {
        "dir": "landing/map",
        "label": "산업지도 JSON (landing/ SvelteKit 정적 asset)",
        "public": True,
    },
    # ── 내부용 (brand.ts 동기화 불필요) ──
    "edgarScan": {
        "dir": "edgar/scan",
        "label": "EDGAR 전종목 scan 프리빌드 데이터",
        "public": False,
    },
    "allFilings": {
        "dir": "dart/allFilings",
        "label": "DART 전체 공시 원문 데이터",
        "public": False,
    },
    "stemIndex": {
        "dir": "dart/stemIndex",
        "label": "Ngram+Synonym 통합 검색 인덱스",
        "public": False,
    },
    "edinetDocs": {
        "dir": "edinet/docs",
        "label": "EDINET 공시 문서 데이터 (일본)",
        "public": False,
    },
    "edinet": {
        "dir": "edinet/finance",
        "label": "EDINET 재무 데이터 (일본)",
        "public": False,
    },
    "aiKnowledge": {
        "dir": "ai/knowledge",
        "label": "AI 분석 지식 (인사이트/스킬/에러패턴)",
        "public": False,
    },
}


def hfBaseUrl(category: str = "docs") -> str:
    """HuggingFace 데이터셋 base URL."""
    dirPath = DATA_RELEASES[category]["dir"]
    return f"{HF_BASE_URL}/{dirPath}"
