"""데이터 릴리즈 중앙 설정.

디렉토리, 라벨을 1곳에서 관리.
새 카테고리 추가 시 DATA_RELEASES에 한 줄만 추가하면 전체 반영.

모든 데이터는 HuggingFace 데이터셋(eddmpython/dartlab-data)에서 제공.
"""

HF_REPO = "eddmpython/dartlab-data"
HF_BASE_URL = f"https://huggingface.co/datasets/{HF_REPO}/resolve/main"

DATA_RELEASES: dict[str, dict] = {
    # ── 사용자 공개 (brand.ts 동기화 대상) ──
    # ipcMirror: True 면 sync ETL 이 parquet 외에 .arrow IPC mirror artifact 도 빌드.
    # Phase D 의 pl.read_ipc(memory_map=True) 진입점이 사용. mmap 안 되는 환경 (pyodide)
    # 은 무시 후 parquet fallback.
    "docs": {
        "dir": "dart/docs",
        "label": "DART 공시 문서 데이터",
        "public": True,
        "ipcMirror": True,
    },
    # docs 농장 은퇴 — "sections" SSOT artifact category 제거(buildSections/sectionsStorage 삭제,
    # sync/runtime 참조 0). HF 기존 sections 데이터는 보존(코드만 제거). panel 이 공시 수평화 표면.
    "panel": {
        # panel(공시 수평화) SSOT artifact — **flat** data/dart/panel/{code}.parquet (회사당 1파일,
        # 17-col). providers.dart.panel.build 가 zip→17col 생산(disclosureKey 부착) → providers.dart.panel
        # 이 read_parquet read(reader/uploader 모두 flat). EDGAR edgarPanel 과 동일 flat 정책.
        # ⚠ nested 금지: 옛 period-sharded {code}/{period}.parquet 표기는 폐기됨 — nested:True 면
        # uploader rglob·downloadAll glob 이 옛 nested 트리를 잘못 휩쓸어 reader(flat)와 어긋난다.
        "dir": "dart/panel",
        "label": "DART 공시 panel 수평화 artifact (회사당 flat, 17-col)",
        "public": True,
    },
    "finance": {
        "dir": "dart/finance",
        "label": "재무 숫자 데이터",
        "public": True,
        "ipcMirror": True,
    },
    "report": {
        "dir": "dart/report",
        "label": "정기보고서 데이터",
        "public": True,
        "ipcMirror": True,
    },
    "scan": {
        "dir": "dart/scan",
        "label": "전종목 횡단분석 프리빌드 데이터",
        "public": True,
    },
    "edgarDocs": {
        # plan delegated-prancing-tower PR-E7a — deprecated 마킹.
        # 안전 게이트 (4 주 sectionsParityEdgar 0 violations + D.1 2 주 + viewer
        # Playwright 0 + sync 14 일 무사고 + 운영자 명시 결정) 통과 후 PR-E7b 가 완전
        # 제거. 본 마킹 후에도 dual-write (fetchEdgarDocs) 가 계속 emit — 옛 path 호출자
        # 회귀 0 보장.
        "dir": "edgar/docs",
        "label": "SEC EDGAR 공시 문서 데이터 (deprecated — edgarSections 로 이행 중)",
        "public": True,
        "deprecated": True,
        "successor": "edgarSections",
    },
    "edgarSections": {
        # plan delegated-prancing-tower — EDGAR sections SSOT 통합 artifact.
        # nested: data/edgar/sections/{ticker}/{period}.parquet (period-sharded).
        # sectionsBuilder (PR-E2) 가 1 회 영속화 + HF push (PR-E3).
        # 런타임은 sectionsStorage.loadSectionsWide → mmap parquet → 콜드 1s 목표.
        # 2 content column: content_raw (iXBRL HTML, viewer SSOT) + content_plain (markdown, 분석 SSOT).
        "dir": "edgar/sections",
        "label": "SEC EDGAR sections SSOT artifact (period-sharded, raw+plain 2 column)",
        "public": True,
        "nested": True,
    },
    "edgarPanel": {
        # EDGAR panel(공시 수평화) SSOT artifact — DART panel 미러.
        # flat: data/edgar/panel/{ticker}.parquet (회사당 1파일, HF 폭발 회피 — DART flat 정책 미러).
        # providers.edgar.panel.build 가 SEC full-submission text → cross-market 16-col remap 생산,
        # providers.dart.panel 이 read_parquet (marketNs="us"). nested=False (flat 1파일).
        "dir": "edgar/panel",
        "label": "SEC EDGAR 공시 panel 수평화 artifact (회사당 flat, cross-market 16-col)",
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
    "krxPriceCompany": {
        "dir": "krx/prices/company",
        "label": "KRX 회사별 일별 OHLCV+시총 타임라인 (landing dashboard artifact)",
        "public": True,
    },
    "krxIndices": {
        "dir": "krx/indices",
        "label": "KRX 시장군별 지수 일별 OHLCV+거래대금+시가총액 (raw, long parquet)",
        "public": True,
    },
    "macroFred": {
        "dir": "macro/fred",
        "label": "FRED 거시경제 시계열 (HF 벌크, latest-revised)",
        "public": True,
    },
    "macroEcos": {
        "dir": "macro/ecos",
        "label": "ECOS 한국은행 거시경제 시계열 (HF 벌크, latest-revised)",
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
    "dartOriginal": {
        # 원본=SSOT 전략([[project_original_ssot_strategy]]) — DART 정기보고서(사업·분기·반기)
        # document.xml zip 보관 (재빌드 가치 높은 분석 핵심). nested: original/dart/docs/{code}/{rcept}.zip.
        # allFilings(비정기)는 월별 parquet 이라 zip 안함. EDGAR 는 panel 만(raw 폐기).
        "dir": "original/dart/docs",
        "label": "DART 정기보고서 원본 zip (재빌드용, 비공개)",
        "public": False,  # 재배포 안전 — private repo
        "nested": True,
        "repo": "eddmpython/dartlab-dart-original",
    },
    "stemIndex": {
        "dir": "dart/stemIndex",
        "label": "Ngram+Synonym 통합 검색 인덱스",
        "public": False,
    },
    "contentIndex": {
        "dir": "dart/contentIndex",
        "label": "의미검색 content 인덱스 (BM25 CSR + 경험그래프 meaning.json + gateRef) — 런타임 lazy pull",
        "public": True,
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
    "newsHeadlines": {
        # Phase A — Google News RSS 일별 헤드라인 archive (forward-only).
        # `data/news/headlines/{market}/{YYYY}-{MM}-{DD}.parquet` 일별 sharding.
        # 본문 archive 영구 제외 (ToS) — headline + url + source + date 메타데이터만.
        # syncNewsHeadlines.py cron 박제, enrichNewsHeadlines.py (Phase B) 가 sentiment/topic 추가.
        "dir": "news/headlines",
        "label": "Google News RSS 일별 헤드라인 archive (forward-only, 메타데이터만)",
        "public": True,
        "nested": True,
    },
    "newsEnriched": {
        # Phase B — sentiment + topic enrichment 결과.
        # `data/news/enriched/{market}/{YYYY}-{MM}-{DD}.parquet` raw 와 동일 sharding.
        # raw 컬럼 + (sentiment_score, sentiment_label, model_version, topic_id, topic_label, topic_prob).
        # enrichNewsHeadlines.py cron, narrativePulse.buildNarrativePulse 가 입력.
        "dir": "news/enriched",
        "label": "news headlines enriched (sentiment + topic, Phase B 산출)",
        "public": True,
        "nested": True,
    },
    "newsGdelt": {
        # Phase D — GDELT 2.0 GKG 글로벌 5 년 백필.
        # `data/news/gdelt/{market}/{YYYY}-{MM}-{DD}.parquet` 일별 sharding.
        # newsEnriched 와 호환 schema + (themes list, language, tone_raw) 추가.
        # syncGdeltBackfill.py 가 GDELT 슬롯 15-min 부터 일별 통합.
        # narrativePulse 호환 (sentiment_score + topic_label 동일 의미).
        "dir": "news/gdelt",
        "label": "GDELT 2.0 GKG 글로벌 뉴스 archive (URL + sentiment + themes, Phase D 백필)",
        "public": True,
        "nested": True,
    },
}


def repoFor(category: str) -> str:
    """카테고리별 HuggingFace repo id — 전용 repo 가 지정됐으면 그것, 아니면 기본 HF_REPO.

    Capabilities:
        무거운 nested 카테고리(panel ~9 만 파일 · gdelt ~6 만)를 전용 repo 로 분리해 per-repo
        파일수 한계(~10 만/repo)·tree 열거 429 를 회피하기 위한 라우팅 단일 진입점.
    AIContext:
        업로드(uploadData/bulkUploadHf)·다운로드(dataLoader/ensure*FromHf) 양쪽이 repo_id 를
        하드코딩하는 대신 본 함수로 해석 → 전용 repo 전환이 dataConfig 한 곳에서 끝난다.
    Guide:
        데이터 이전(운영자 트리거) 전까지는 어떤 카테고리도 `repo` 필드를 두지 않아 전부 기본
        repo 를 공유 → 동작 무변경. 이전 완료 후 해당 카테고리에 `"repo": "..."` 한 줄 추가.
    When:
        HF 업로드/다운로드 대상 repo 를 결정할 때.
    How:
        DATA_RELEASES[category].get("repo") 가 truthy 면 그 값, 아니면 HF_REPO.
    Requires:
        없음 — 미등록 category 도 HF_REPO 로 graceful.
    Raises:
        없음.
    Args:
        category: DATA_RELEASES 카테고리 키 (미등록이어도 HF_REPO 반환).
    Returns:
        해당 카테고리 데이터가 사는 HuggingFace dataset repo id.
    Example:
        >>> repoFor("contentIndex")
        'eddmpython/dartlab-data'
    SeeAlso:
        DATA_RELEASES: 카테고리별 `repo`(선택)·`dir`·공개 여부.
        hfBaseUrl: repoFor 를 사용해 resolve URL 을 만든다.
    """
    return DATA_RELEASES.get(category, {}).get("repo") or HF_REPO


def hfBaseUrl(category: str = "docs") -> str:
    """HuggingFace 데이터셋 base URL.

    Capabilities:
        DATA_RELEASES에 등록된 데이터 카테고리를 HuggingFace resolve URL로 변환한다.
    AIContext:
        데이터 다운로드 경로를 설명하거나 캐시 출처를 추적할 때 사용하는 L0 설정 함수다.
    Guide:
        새 데이터 카테고리는 DATA_RELEASES에 먼저 추가하고, 호출자는 카테고리 키만 넘긴다.
    When:
        dataLoader가 원격 parquet, zip, json 경로의 base URL을 만들 때 호출한다.
    How:
        repoFor(category) 로 repo 를 해석해 resolve base 를 만들고 DATA_RELEASES[category]["dir"] 를 붙인다.
    Requires:
        category가 DATA_RELEASES에 등록되어 있어야 한다.
    Raises:
        KeyError: category가 DATA_RELEASES에 없을 때.
    Args:
        category: DATA_RELEASES에 등록된 데이터 카테고리 키.
    Returns:
        HuggingFace resolve URL의 카테고리별 base 경로.
    Example:
        >>> hfBaseUrl("finance").endswith("/dart/finance")
        True
    SeeAlso:
        DATA_RELEASES: 카테고리별 원격 디렉터리와 공개 여부.
        dartlab.core.dataLoader.download: 반환 URL을 실제 다운로드에 사용한다.
    """
    dirPath = DATA_RELEASES[category]["dir"]
    return f"https://huggingface.co/datasets/{repoFor(category)}/resolve/main/{dirPath}"
