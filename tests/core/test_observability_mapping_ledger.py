"""mapping_ledger — ENV gate, ndjson append, readAll, path override 단위 테스트.

본 ledger 는 prod 동작 0 영향이 핵심. ENV OFF 가 기본이며 어떤 호출도
file IO 를 일으키면 안 된다. 본 모듈은 옵트인 안전장치.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from dartlab.core.observability import mapping_ledger

pytestmark = pytest.mark.unit


@pytest.fixture
def _clearEnv(monkeypatch: pytest.MonkeyPatch) -> None:
    """ENV gate 와 path override 를 매 테스트마다 제거."""
    monkeypatch.delenv("DARTLAB_MAPPING_LEDGER", raising=False)
    monkeypatch.delenv("DARTLAB_MAPPING_LEDGER_PATH", raising=False)


class TestIsEnabled:
    def test_default_off(self, _clearEnv) -> None:
        assert mapping_ledger.isEnabled() is False

    @pytest.mark.parametrize("flag", ["1", "true", "True", "YES", "on", "ON"])
    def test_truthy_values_enable(self, _clearEnv, monkeypatch, flag) -> None:
        monkeypatch.setenv("DARTLAB_MAPPING_LEDGER", flag)
        assert mapping_ledger.isEnabled() is True

    @pytest.mark.parametrize("flag", ["0", "false", "no", "off", "", "random"])
    def test_falsy_values_disable(self, _clearEnv, monkeypatch, flag) -> None:
        monkeypatch.setenv("DARTLAB_MAPPING_LEDGER", flag)
        assert mapping_ledger.isEnabled() is False


class TestLedgerPath:
    def test_default_path(self, _clearEnv) -> None:
        path = mapping_ledger.ledgerPath()
        assert path.name == "mapping_candidates_raw.ndjson"
        assert path.parent.name == "data"

    def test_env_override(self, _clearEnv, monkeypatch, tmp_path: Path) -> None:
        custom = tmp_path / "custom.ndjson"
        monkeypatch.setenv("DARTLAB_MAPPING_LEDGER_PATH", str(custom))
        assert mapping_ledger.ledgerPath() == custom


class TestAppend:
    def test_env_off_returns_zero_and_no_file(self, _clearEnv, monkeypatch, tmp_path: Path) -> None:
        target = tmp_path / "off.ndjson"
        monkeypatch.setenv("DARTLAB_MAPPING_LEDGER_PATH", str(target))
        # ENV flag 미설정 = OFF
        n = mapping_ledger.append(
            [{"accountId": "x", "accountNm": "y", "sjDiv": "BS", "occurrenceCount": 1}],
            stockCode="005930",
        )
        assert n == 0
        assert not target.exists()

    def test_env_on_writes_ndjson_line(self, _clearEnv, monkeypatch, tmp_path: Path) -> None:
        target = tmp_path / "on.ndjson"
        monkeypatch.setenv("DARTLAB_MAPPING_LEDGER", "1")
        monkeypatch.setenv("DARTLAB_MAPPING_LEDGER_PATH", str(target))

        n = mapping_ledger.append(
            [
                {
                    "accountId": "-표준계정코드 미사용-",
                    "accountNm": "기타의금융자산",
                    "sjDiv": "BS",
                    "occurrenceCount": 14,
                }
            ],
            stockCode="005930",
        )
        assert n == 1
        assert target.exists()

        lines = target.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["accountNm"] == "기타의금융자산"
        assert record["stockCode"] == "005930"
        assert record["sjDiv"] == "BS"
        assert record["occurrenceCount"] == 14
        assert "observedAt" in record

    def test_multiple_records_append_multiple_lines(self, _clearEnv, monkeypatch, tmp_path: Path) -> None:
        target = tmp_path / "multi.ndjson"
        monkeypatch.setenv("DARTLAB_MAPPING_LEDGER", "1")
        monkeypatch.setenv("DARTLAB_MAPPING_LEDGER_PATH", str(target))

        records = [
            {"accountId": "a", "accountNm": "기타의금융자산", "sjDiv": "BS", "occurrenceCount": 14},
            {"accountId": "b", "accountNm": "출자금의 중간분배", "sjDiv": "CF", "occurrenceCount": 6},
        ]
        n = mapping_ledger.append(records, stockCode="000660")
        assert n == 2

        lines = target.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

    def test_append_creates_parent_directory(self, _clearEnv, monkeypatch, tmp_path: Path) -> None:
        nested = tmp_path / "deep" / "tree" / "ledger.ndjson"
        monkeypatch.setenv("DARTLAB_MAPPING_LEDGER", "1")
        monkeypatch.setenv("DARTLAB_MAPPING_LEDGER_PATH", str(nested))

        n = mapping_ledger.append([{"accountId": "", "accountNm": "test", "sjDiv": "IS", "occurrenceCount": 1}])
        assert n == 1
        assert nested.exists()

    def test_append_preserves_extra_keys(self, _clearEnv, monkeypatch, tmp_path: Path) -> None:
        target = tmp_path / "extras.ndjson"
        monkeypatch.setenv("DARTLAB_MAPPING_LEDGER", "1")
        monkeypatch.setenv("DARTLAB_MAPPING_LEDGER_PATH", str(target))

        records = [
            {
                "accountId": "x",
                "accountNm": "y",
                "sjDiv": "BS",
                "occurrenceCount": 3,
                "extraKey": "extraValue",
            }
        ]
        mapping_ledger.append(records)

        record = json.loads(target.read_text(encoding="utf-8").strip())
        assert record["extraKey"] == "extraValue"


class TestReadAll:
    def test_missing_file_returns_empty(self, _clearEnv, monkeypatch, tmp_path: Path) -> None:
        target = tmp_path / "nope.ndjson"
        monkeypatch.setenv("DARTLAB_MAPPING_LEDGER_PATH", str(target))
        assert mapping_ledger.readAll() == []

    def test_read_after_append(self, _clearEnv, monkeypatch, tmp_path: Path) -> None:
        target = tmp_path / "roundtrip.ndjson"
        monkeypatch.setenv("DARTLAB_MAPPING_LEDGER", "1")
        monkeypatch.setenv("DARTLAB_MAPPING_LEDGER_PATH", str(target))

        mapping_ledger.append(
            [
                {
                    "accountId": "id1",
                    "accountNm": "name1",
                    "sjDiv": "BS",
                    "occurrenceCount": 1,
                }
            ]
        )
        rows = mapping_ledger.readAll()
        assert len(rows) == 1
        assert rows[0]["accountNm"] == "name1"

    def test_skips_blank_and_invalid_lines(self, _clearEnv, monkeypatch, tmp_path: Path) -> None:
        target = tmp_path / "dirty.ndjson"
        monkeypatch.setenv("DARTLAB_MAPPING_LEDGER_PATH", str(target))
        target.write_text(
            '\n{"a": 1}\nnot-json\n   \n{"b": 2}\n',
            encoding="utf-8",
        )

        rows = mapping_ledger.readAll()
        assert rows == [{"a": 1}, {"b": 2}]
