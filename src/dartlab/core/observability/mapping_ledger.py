"""미매핑 계정 관측 ledger — `accountMappings.json` 보강 후보 산출.

본 모듈은 `providers/dart/finance/pivot.py` 의 `_pivotToSeries` 가
미매핑 계정 (account_id 표준 X 또는 한글명 사전 미커버) 을 fallback
처리할 때 옵트인으로 호출. ndjson append 만 수행하며 prod 동작 0 영향.

ENV gate:
    `DARTLAB_MAPPING_LEDGER` ∈ {"1", "true", "yes", "on"} 일 때만 활성.
    경로는 `DARTLAB_MAPPING_LEDGER_PATH` 또는 기본 `data/mapping_candidates_raw.ndjson`.

산출물:
    ndjson 1 줄 = 1 관측 단위 (Company 1 회 호출당 unmapped 계정 1 종).
    schema:
        observedAt: ISO8601
        stockCode:  종목코드 (호출자 주입, 없으면 빈 문자열)
        accountId:  DART account_id (보통 "-표준계정코드 미사용-")
        accountNm:  한글 계정명
        sjDiv:      "BS" / "IS" / "CF" / "CIS"
        occurrenceCount: 본 Company 호출 단위 내 동일 키 등장 행 수

후속:
    `scripts/audit/mapping_ledger_compact.py` (Phase B) 가 ndjson →
    `data/mapping_candidates.parquet` 로 5 신호 평가 후 압축.

AIContext:
    - 자동화 안전장치: 본 모듈은 *관측* 만. accountMappings.json
      patch 는 별도 promote CLI 의 단독 권한 (관측·후보·승인·반영 4 단계 분리).
    - ENV OFF 가 기본. 사용자 영향 0.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

_ENV_FLAG = "DARTLAB_MAPPING_LEDGER"
_ENV_PATH = "DARTLAB_MAPPING_LEDGER_PATH"
_DEFAULT_REL_PATH = Path("data") / "mapping_candidates_raw.ndjson"
_TRUTHY = frozenset({"1", "true", "yes", "on"})


def isEnabled() -> bool:
    """Args: 없음.

    Returns:
        ENV `DARTLAB_MAPPING_LEDGER` 가 truthy 집합 ("1"/"true"/"yes"/"on",
        대소문자 무시) 이면 True. 기본 False.

    Example:
        >>> os.environ.pop("DARTLAB_MAPPING_LEDGER", None)
        >>> isEnabled()
        False
        >>> os.environ["DARTLAB_MAPPING_LEDGER"] = "1"
        >>> isEnabled()
        True

    Raises:
        없음.
    """
    raw = os.environ.get(_ENV_FLAG, "")
    return raw.strip().lower() in _TRUTHY


def ledgerPath() -> Path:
    """Args: 없음.

    Returns:
        ENV `DARTLAB_MAPPING_LEDGER_PATH` 가 있으면 그 경로, 없으면 cwd 기준
        ``data/mapping_candidates_raw.ndjson``. 경로 생성은 하지 않는다.

    Example:
        >>> os.environ.pop("DARTLAB_MAPPING_LEDGER_PATH", None)
        >>> ledgerPath().name
        'mapping_candidates_raw.ndjson'

    Raises:
        없음.
    """
    override = os.environ.get(_ENV_PATH, "").strip()
    if override:
        return Path(override)
    return _DEFAULT_REL_PATH


def append(records: Iterable[dict], stockCode: str | None = None) -> int:
    """ledger 에 nonstd 관측을 ndjson 으로 누적.

    Args:
        records: 각 dict 는 최소 ``accountId``·``accountNm``·``sjDiv``·
            ``occurrenceCount`` 키 보유. 추가 키는 그대로 보존.
        stockCode: 호출자가 알면 주입. None 이면 빈 문자열로 기록.

    Returns:
        실제 기록된 라인 수. ENV OFF 면 0.

    Example:
        >>> os.environ["DARTLAB_MAPPING_LEDGER"] = "1"
        >>> n = append([{"accountId": "", "accountNm": "기타의금융자산",
        ...              "sjDiv": "BS", "occurrenceCount": 14}], "005930")
        >>> n
        1

    Raises:
        OSError: ledger 디렉토리 생성·파일 append 실패 시.
    """
    if not isEnabled():
        return 0

    path = ledgerPath()
    path.parent.mkdir(parents=True, exist_ok=True)
    observedAt = datetime.now(timezone.utc).isoformat(timespec="seconds")
    code = (stockCode or "").strip()

    count = 0
    with path.open("a", encoding="utf-8") as f:
        for rec in records:
            line = {
                "observedAt": observedAt,
                "stockCode": code,
                "accountId": rec.get("accountId", ""),
                "accountNm": rec.get("accountNm", ""),
                "sjDiv": rec.get("sjDiv", ""),
                "occurrenceCount": int(rec.get("occurrenceCount", 0)),
            }
            extras = {k: v for k, v in rec.items() if k not in line}
            line.update(extras)
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
            count += 1
    return count


def readAll(path: Path | None = None) -> list[dict]:
    """ledger ndjson 전체를 list[dict] 로 로드.

    Args:
        path: None 이면 ``ledgerPath()`` 사용. 파일 부재 시 빈 list.

    Returns:
        파싱된 dict 리스트. 빈 라인·JSON 파싱 실패 라인은 skip.

    Example:
        >>> rows = readAll()  # ENV/파일 부재 시 []
        >>> isinstance(rows, list)
        True

    Raises:
        OSError: 파일은 있는데 읽기 실패 시.
    """
    target = path or ledgerPath()
    if not target.exists():
        return []
    out: list[dict] = []
    with target.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out
