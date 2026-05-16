# `tests/_cassettes/` — HTTP record-replay 카세트 (Track 7)

> 본 디렉토리 SSOT — [tests/POLICY.md](../POLICY.md) §5 Track 7.

## 목적

`providers/{dart,edgar}/openapi/*` 의 외부 HTTP 호출을 **한 번 record → CI 에서 replay** 한다. DART/EDGAR API 가 응답 포맷을 바꾸면 fixture parquet 만으론 못 잡지만, 카세트 는 *raw HTTP body* 까지 동결한다.

## 디렉토리 구조

```
tests/_cassettes/
├── dart/
│   ├── corpCode_list.yaml    # corpCode 조회 응답
│   ├── disclosure_list.yaml  # 공시 목록 조회
│   └── ...
├── edgar/
│   ├── tickers.yaml
│   └── filings_AAPL.yaml
└── README.md (본 파일)
```

## Record 절차 (운영자 트리거 1 회)

```powershell
# 1. API key 환경변수 설정 (.env 로드)
$env:DART_API_KEY="..."

# 2. record 모드로 실행 — 카세트 없으면 record, 있으면 replay (`once`)
$env:DARTLAB_TEST_LOCKED="1"; $env:UV_NO_SYNC="1"
uv run python -X utf8 -m pytest tests/providers/dart/test_vcr_smoke.py -v -m network

# 3. 카세트 git 추가
git add tests/_cassettes/dart/*.yaml
git commit -o tests/_cassettes/dart -m "추가: dart openapi VCR 카세트 (YYYY-MM-DD record)"
```

## Replay (CI 기본)

CI 는 `record_mode='none'` (네트워크 차단) — 카세트 없으면 skip, 있으면 replay.

```powershell
$env:DARTLAB_TEST_LOCKED="1"
uv run python -X utf8 -m pytest tests/providers/dart/test_vcr_smoke.py -v
```

## Match 룰

기본:
- `method` · `scheme` · `host` · `port` · `path` · `query`

DART API 의 `api_key` 쿼리 파라미터는 **카세트 record 시 sanitize** 필요 (다음 절). 매칭에서 제외.

## 민감 정보 sanitize

```python
# tests/_helpers.py 의 helper 참조
my_vcr = vcr.VCR(
    cassette_library_dir='tests/_cassettes/dart',
    record_mode='once',
    filter_query_parameters=['crtfc_key', 'api_key'],   # DART · EDGAR key 제거
    filter_headers=['Authorization', 'Cookie'],
)
```

카세트 commit 전 `grep -r "crtfc_key" tests/_cassettes/` 로 잔재 확인.

## 갱신 시점

- DART/EDGAR API 가 응답 컬럼 변경
- 새 endpoint 추가
- 카세트 ≥ 6 개월 stale → 신선도 차원에서 re-record

## 갱신 절차

```powershell
# 기존 카세트 삭제 후 record
Remove-Item tests/_cassettes/dart/disclosure_list.yaml
uv run python -X utf8 -m pytest tests/providers/dart/test_vcr_smoke.py::test_disclosure_replay -v -m network

# diff 검토 후 commit
git diff tests/_cassettes/dart/disclosure_list.yaml
git commit -o tests/_cassettes/dart/disclosure_list.yaml -m "갱신: dart disclosure 카세트 (응답 컬럼 추가)"
```
