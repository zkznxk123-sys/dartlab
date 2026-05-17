"""서버 API 공통 유틸 테스트."""

import pytest

pytestmark = pytest.mark.unit

import polars as pl

from dartlab.server.api.common import computeEtag, sanitizeError, serializePayload


class TestSanitizeError:
    def test_removes_unix_path(self):
        exc = FileNotFoundError("/home/user/data/secret.csv")
        msg = sanitizeError(exc)
        assert "/home/user" not in msg
        assert "<path>" in msg

    def test_removes_windows_path(self):
        exc = FileNotFoundError("C:\\Users\\MSI\\data.csv")
        msg = sanitizeError(exc)
        assert "C:\\Users" not in msg
        assert "<path>" in msg

    def test_removes_api_key(self):
        exc = ValueError("api_key=sk-abc123xyz invalid")
        msg = sanitizeError(exc)
        assert "sk-abc123xyz" not in msg
        assert "api_key=***" in msg

    def test_removes_token(self):
        exc = RuntimeError("token=eyJhbGciOiJIUzI1NiJ9 expired")
        msg = sanitizeError(exc)
        assert "eyJhbGci" not in msg
        assert "token=***" in msg

    def test_removes_bearer(self):
        exc = ValueError("bearer sk-live-12345 expired")
        msg = sanitizeError(exc)
        assert "sk-live-12345" not in msg

    def test_preserves_normal_message(self):
        exc = ValueError("종목코드 005930을 찾을 수 없습니다")
        msg = sanitizeError(exc)
        assert "005930" in msg

    def test_combined_path_and_credential(self):
        exc = OSError("token=secret123 at /home/user/config.json")
        msg = sanitizeError(exc)
        assert "secret123" not in msg
        assert "/home/user" not in msg


class TestComputeEtag:
    def test_deterministic(self):
        data = {"x": 1, "y": "hello"}
        assert computeEtag(data) == computeEtag(data)

    def test_different_data_different_etag(self):
        assert computeEtag({"a": 1}) != computeEtag({"a": 2})

    def test_format_quoted(self):
        etag = computeEtag({"test": True})
        assert etag.startswith('"')
        assert etag.endswith('"')

    def test_key_order_independent(self):
        assert computeEtag({"a": 1, "b": 2}) == computeEtag({"b": 2, "a": 1})


class TestSerializePayload:
    def test_none(self):
        result = serializePayload(None)
        assert result["type"] == "none"
        assert result["data"] is None

    def test_string(self):
        result = serializePayload("hello")
        assert result["type"] == "text"
        assert result["data"] == "hello"

    def test_dict(self):
        result = serializePayload({"key": "value"})
        assert result["type"] == "dict"
        assert result["data"]["key"] == "value"

    def test_dataframe(self):
        df = pl.DataFrame({"A": [1, 2, 3], "B": ["a", "b", "c"]})
        result = serializePayload(df)
        assert result["type"] == "table"
        assert result["columns"] == ["A", "B"]
        assert len(result["rows"]) == 3
        assert result["totalRows"] == 3
        assert result["truncated"] is False

    def test_dataframe_truncation(self):
        df = pl.DataFrame({"x": list(range(500))})
        result = serializePayload(df, maxRows=10)
        assert len(result["rows"]) == 10
        assert result["totalRows"] == 500
        assert result["truncated"] is True

    def test_unknown_type(self):
        result = serializePayload(42)
        assert result["type"] == "unknown"
        assert "42" in result["data"]
