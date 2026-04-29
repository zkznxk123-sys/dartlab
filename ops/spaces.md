# HuggingFace Spaces — API + MCP 서버

**주체**: HF Space 원격 서버 (`https://eddmpython-dartlab.hf.space`).
**현재**: REST API + MCP SSE 동시 제공 · DART API 키 없이도 실시간 공시 조회 · 설치 없는 사용 경로.
**방향**: Space GPU 업그레이드 검토 · 캐시 정책 최적화 · MCP tool 목록 자동 동기화.

**설치 없이** dartlab 전체 엔진을 사용할 수 있는 원격 서버. REST API + MCP SSE 동시 제공. DART API 키 없이도 실시간 공시 조회.

각 섹션은 **"이렇게 한다"** 명제로 열고, 반복된 실수는 섹션 하단 **"반복 실패"** 에 정리한다.

---

## 1. 한눈에 보기

| 항목 | 내용 |
|---|---|
| URL | `https://eddmpython-dartlab.hf.space` |
| 인프라 | HuggingFace Spaces (CPU 2 코어 · 16GB · 무료) |
| MCP | `/mcp/sse` — 자동 생성 도구 + API discovery + Analysis Graph/Process Map |
| REST API | `/api/dart/*` — 공시·재무·보고서 프록시 |
| DART 키 | 서버 측 Secret 으로 관리, 사용자 불필요 |
| 자동 배포 | `v*` 릴리즈 시 GitHub Actions → HF push |
| 절전 | 48 시간 비활성 시 sleep → 요청 시 자동 기동 (~30 초) |

---

## 2. 접근 방법 — 3 경로로 쓴다

### 1) MCP (설치 없이 AI 에서 직접)

MCP 호환 실행 환경 설정:

```json
{
  "mcpServers": {
    "dartlab": {
      "url": "https://eddmpython-dartlab.hf.space/mcp/sse"
    }
  }
}
```

자동 생성 도구 즉시 사용:
- 개별 종목 — `companyInsights` · `companyAnalysis` · `companyStory` · `companyValuation` · `companyCredit` · `companyGather` · `companyQuant` …
- 시장·거시 — `macroAnalysis` · `marketScan` · `gatherData` · `quantAnalysis` · `topdownScreen`.
- 검색·목록 — `searchCompany` · `dartlabSearch` · `dartlabListing`.

### 2) REST API (curl · 브라우저)

```bash
# 공시 목록
curl "https://eddmpython-dartlab.hf.space/api/dart/filings?corp=005930&start=20260101"

# 기업 정보
curl "https://eddmpython-dartlab.hf.space/api/dart/company/005930"

# 재무제표
curl "https://eddmpython-dartlab.hf.space/api/dart/finance/005930?year=2024"

# 보고서 (배당, 직원, 임원 등 56개 카테고리)
curl "https://eddmpython-dartlab.hf.space/api/dart/report/005930/배당?year=2023"
```

### 3) dartlab 설치 + 키 없음 (자동 fallback)

```python
from dartlab import OpenDart
d = OpenDart()  # 키 없으면 자동으로 서버 프록시 사용
d.filings("삼성전자", start="20260101")
```

---

## 3. 아키텍처

```
사용자
 ├─ MCP 실행 환경 → /mcp/sse → MCP Server (generated tools) → dartlab 엔진 전체
 ├─ curl/브라우저  → /api/dart/* → DART 프록시 → OpenDART API (서버 키)
 └─ dartlab 패키지 → RemoteDartClient → /api/dart/* (키 없을 때 fallback)
```

### 서버 내부 구조

```
FastAPI app (src/dartlab/server/__init__.py)
 ├─ /api/dart/*     DART 프록시 라우터 (server/api/dart.py)
 ├─ /api/company/*  Company 데이터 (기존)
 ├─ /api/status     헬스체크 (기존)
 ├─ /mcp/           MCP SSE ASGI 앱 (mcp/__init__.py → create_sse_app())
 └─ /*              Svelte SPA (기존)
```

### MCP 전송 방식

| 모드 | 전송 | 용도 |
|---|---|---|
| stdio | stdin · stdout | 로컬 workspace |
| SSE | HTTP `/mcp/sse` | 원격 (HF Spaces · 설치 없이) |

두 모드 모두 같은 `create_server()` → 같은 자동 생성 도구. 코드 공유.

---

## 4. DART 프록시 엔드포인트

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/dart/filings` | 공시 목록 (`corp` · `start` · `end` · `type`) |
| GET | `/api/dart/company/{corp}` | 기업 기본 정보 |
| GET | `/api/dart/finance/{corp}` | 재무제표 (`year` · `quarter`) |
| GET | `/api/dart/report/{corp}/{category}` | 보고서 56 카테고리 (`year`) |

### 보안

- `crtfc_key` 필드 자동 제거 (키 노출 방지).
- 결과 최대 100 행 (남용 방지).
- HF Secret 에 `DART_API_KEY` 저장.

**반복 실패** — 프록시 응답에 `crtfc_key` 그대로 포함 → API 키 노출. 응답 직전에 필드 필터링 필수.

---

## 5. MCP 도구 — 자동 생성으로 간다

MCP 도구 목록은 이 문서에서 수동 관리하지 않는다. Python API docstring/capabilities/Analysis Graph 를 `scripts/build/generateSpec.py` 가 읽어 `src/dartlab/mcp/_generated_tools.py` 로 생성한다.

### 개별 종목

| 도구 | 설명 |
|---|---|
| companyInsights | 7 영역 등급 + 프로파일 |
| companyAnalysis | 14 축 재무 심층분석 |
| companyStory | 6 막 종합 보고서 |
| companyValuation | DCF + DDM + 상대가치 |
| companyForecast | 매출 예측 |
| companyFinancials | 재무제표 원본 |
| companyRatios | 55 비율 시계열 |
| companyShow | 공시 토픽 원문 |
| companyTopics | 토픽 목록 |
| companyDiff | 기간간 변경 비교 |
| companyGovernance | 지배구조 |
| companyAudit | 감사 리스크 |
| companyProfile | 기본 정보 |
| companySections | 데이터 지도 |
| **companyCredit** | 독립 신용등급 7 축 |
| **companyGather** | 주가·수급·뉴스 |
| **companyQuant** | 기술적 분석 |
| **companyFilings** | 공시 목록 |
| searchCompany | 종목 검색 |

### 시장·거시

| 도구 | 설명 |
|---|---|
| **macroAnalysis** | 경제 사이클·금리·자산·심리·유동성·종합 |
| **marketScan** | 전종목 횡단분석 |
| **gatherData** | 주가·거시지표·뉴스 수집 |
| **quantAnalysis** | 기술적 분석 |
| **topdownScreen** | 사이클→섹터→종목 선별 |
| **dartlabSearch** | 공시 원문 검색 |
| **dartlabListing** | 상장종목·공시 목록 |

---

## 6. RemoteDartClient — DART 키 없을 때 자동 fallback

DART 키가 없을 때 `Dart()` 생성 시 자동으로 원격 서버 프록시로 전환.

```python
# src/dartlab/providers/dart/openapi/dart.py
class Dart:
    def __init__(self, keys=None):
        try:
            self._client = DartClient(...)  # 키 탐색
        except ValueError:
            self._client = RemoteDartClient()  # 서버 fallback
```

서버 URL — `DARTLAB_SERVER_URL` 환경변수 또는 기본값 `https://eddmpython-dartlab.hf.space`.

---

## 7. HF Spaces 배포

### 파일 구조

```
spaces/
├── Dockerfile    # python:3.12-slim + uv + dartlab
└── README.md     # HF Space 메타데이터 (YAML frontmatter)
```

### 환경변수 (HF Secrets)

| 변수 | 용도 |
|---|---|
| `DART_API_KEY` | OpenDART API 키 |
| `SPACE_ID` | 자동 (HF 제공) |

### 자동 배포

`.github/workflows/deploySpaces.yml`:
- `v*` 릴리즈 시 자동 트리거.
- `spaces/` + `src/` + `pyproject.toml` → HF Space repo push.
- 수동 — `workflow_dispatch`.

### 메모리 안전

HF 무료 티어 16GB 에서:
- Company 캐시 — `MAX_SIZE=3` · `TTL=300` 초.
- `SPACE_ID` 감지 시 서버가 자동으로 `0.0.0.0:7860` 바인드.

**반복 실패** — 캐시 `MAX_SIZE` 를 크게 키우면 16GB 한계에서 OOM 직전. 3 개 TTL 300 초 고정.

---

## 관련 코드

| 파일 | 역할 |
|---|---|
| `src/dartlab/mcp/__init__.py` | MCP 서버 (자동 생성 도구 + SSE 전송) |
| `src/dartlab/server/__init__.py` | FastAPI 앱 + MCP SSE 마운트 |
| `src/dartlab/server/api/dart.py` | DART 프록시 라우터 |
| `src/dartlab/providers/dart/openapi/remote.py` | RemoteDartClient |
| `src/dartlab/providers/dart/openapi/dart.py` | Dart 클래스 (fallback 로직) |
| `spaces/Dockerfile` | HF Spaces Docker 배포 |
| `.github/workflows/deploySpaces.yml` | 자동 배포 |

---

## 요약 — 명제 7 줄

1. HF Space 는 `/mcp/sse` + `/api/dart/*` 동시 제공하는 원격 서버, 설치 없이 dartlab 전체 엔진 사용.
2. 접근 3 경로 — MCP · REST (curl · 브라우저) · dartlab 패키지 fallback.
3. MCP 는 stdio·SSE 두 전송 모두 같은 자동 생성 도구 공유, 코드 한 곳.
4. DART 프록시는 4 엔드포인트 (filings · company · finance · report), `crtfc_key` 제거 + 100 행 제한.
5. MCP 도구는 Python API docstring/capabilities/Analysis Graph 에서 자동 생성한다.
6. `RemoteDartClient` 가 키 없을 때 자동 fallback, `DARTLAB_SERVER_URL` 환경변수로 오버라이드.
7. HF 배포는 `deploySpaces.yml` 자동, 16GB 무료 티어에서 캐시 `MAX_SIZE=3 · TTL=300`.
