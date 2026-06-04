"""분석 추론 surfacing 도구 3 종 단위 테스트 — S3.

OutcomeLog · LookAheadGuard · GroundingCheck 가 registry SSOT 에 등록되고 dispatch 되는지,
각 도구의 입력 검증·반환 형태가 일관된지 검증.

LookAheadGuard 는 실제 DART/EDGAR provider 호출이 필요해서 외부 의존이 발생 — 거부 케이스
(asOf 누락) 만 unit 으로 검증, 실제 데이터 호출은 e2e probe 에 위임.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


# ── OutcomeLog ──────────────────────────────────────────────────────────────


def test_outcome_log_dispatch_via_registry():
    from dartlab.ai.tools.registry import executeTool

    result = executeTool(
        "OutcomeLog",
        {
            "stockCode": "005930",
            "market": "KR",
            "date": "2026-05-09",
            "decision": "Hold — 현금 비중 높음, ROE 안정.",
            "theme": "Quarterly Verdict",
        },
    )
    assert result.get("ok") is True
    assert "outcome_log" in (result.get("summary") or "")
    refs = result.get("refs") or []
    assert any(r.get("kind") == "decisionRef" for r in refs)


def test_outcome_log_rejects_invalid_stockcode():
    from dartlab.ai.tools.outcomeLog import outcomeLog

    result = outcomeLog(
        stockCode="../../../etc",  # path traversal 시도
        market="KR",
        date="2026-05-09",
        decision="should not write",
    )
    assert result.ok is False
    assert "stockCode" in (result.summary or "") or "invalid" in (result.error or "").lower()


def test_outcome_log_rejects_invalid_date():
    from dartlab.ai.tools.outcomeLog import outcomeLog

    result = outcomeLog(
        stockCode="005930",
        market="KR",
        date="not-a-date",  # _normalize_date 가 None 반환 → wrote=False
        decision="x",
    )
    # storeDecision 은 invalid date 시 False 반환 (예외 X). 도구는 ok=True + wrote=False.
    assert result.ok is True
    assert result.data.get("wrote") is False


def test_outcome_log_happy_path_writes_file(tmp_path, monkeypatch):
    """happy path — DARTLAB_HOME 격리 + 실 저장 검증 (도그푸드 격차 메우기).

    이전 단위 테스트는 dispatch 거부 경로만 검증했고 실 저장 동작은 검증 없었음. 도그푸드
    probe 가 발견한 LookAheadGuard market 버그처럼, registry 도구의 *외부 효과* 도 단위
    테스트에서 검증해야 함.
    """
    from dartlab.ai.tools.outcomeLog import outcomeLog

    monkeypatch.setenv("DARTLAB_HOME", str(tmp_path))
    result = outcomeLog(
        stockCode="005930",
        market="KR",
        date="2026-05-09",
        decision="Hold — 단위 테스트용 entry",
        theme="UnitTest",
    )
    assert result.ok is True
    assert result.data.get("wrote") is True

    # 실 파일 검증 — ~/.dartlab 의 ${DARTLAB_HOME}/decisions/KR/005930.md 에 기록됨.
    target = tmp_path / "decisions" / "KR" / "005930.md"
    assert target.exists(), f"outcome_log 파일 미생성: {target}"
    body = target.read_text(encoding="utf-8")
    assert "2026-05-09" in body
    assert "005930" in body
    assert "UnitTest" in body
    assert "pending" in body
    assert "Hold — 단위 테스트용 entry" in body


# ── LookAheadGuard ──────────────────────────────────────────────────────────


def test_lookahead_guard_rejects_missing_asof():
    from dartlab.ai.tools.lookAheadGuard import lookAheadGuard

    result = lookAheadGuard(stockCode="005930", asOf="")
    assert result.ok is False
    assert "asOf" in (result.summary or "")


def test_lookahead_guard_rejects_missing_stockcode():
    from dartlab.ai.tools.lookAheadGuard import lookAheadGuard

    result = lookAheadGuard(stockCode="", asOf="2024Q2")
    assert result.ok is False


def test_lookahead_guard_dispatch_via_registry_uses_correct_executor():
    """registry 가 LookAheadGuard → lookAheadGuard 함수 매핑 보유."""
    from dartlab.ai.tools.registry import _TOOLS, CANONICAL_TOOL_NAMES

    assert "LookAheadGuard" in CANONICAL_TOOL_NAMES
    assert "LookAheadGuard" in _TOOLS
    # 함수 자체 호출 가능 확인 (inspect)
    assert callable(_TOOLS["LookAheadGuard"])


@pytest.mark.requires_data
@pytest.mark.network
def test_lookahead_guard_happy_path_real_company():
    """happy path — 실제 dartlab.Company('005930').panel('BS', asOf=...) 호출.

    도그푸드 발견 회귀: tool 가 Company(stockCode, market=...) 으로 호출하면 TypeError —
    Company 는 market kwarg 미지원. unit 테스트가 거부 경로만 검증해서 못 잡았음.
    이 테스트가 happy path 보호.

    requires_data + network — DART API 캐시/HF parquet 필요. CI 에서 skip.
    """
    from dartlab.ai.tools.lookAheadGuard import lookAheadGuard

    result = lookAheadGuard(stockCode="005930", asOf="2024Q4", topic="BS")
    # 데이터 미설치 시 graceful fail 가능 — happy path 외 dispatch ok 만 검증.
    if not result.ok:
        pytest.skip(f"DART data 미설치 또는 provider 미설정 — {result.summary}")
    assert result.data.get("rowCount", 0) > 0
    refs = result.refs or []
    assert any(getattr(r, "kind", None) == "tableRef" for r in refs)


# ── GroundingCheck ──────────────────────────────────────────────────────────


def test_grounding_check_no_claim_no_refs_returns_grounded():
    """material claim 없는 본문 + ref 없음 → grounded=True (검증할 게 없음)."""
    from dartlab.ai.tools.groundingCheck import groundingCheck

    result = groundingCheck(answer="삼성전자는 한국 회사다.", refs=[])
    assert result.ok is True
    assert result.data.get("grounded") is True
    assert result.data.get("materialNumber") is False


def test_grounding_check_material_number_without_refs_unmatched():
    """수치 claim 있는데 ref 없음 → grounded=False."""
    from dartlab.ai.tools.groundingCheck import groundingCheck

    result = groundingCheck(answer="삼성전자 ROE 는 12.3% 다.", refs=[])
    assert result.ok is False
    assert result.data.get("materialNumber") is True
    assert result.data.get("grounded") is False


def test_grounding_check_fake_ref_token_detected():
    """본문에 fake `<valueRef:not_in_state>` 토큰 — fakeRefTokens 에 잡힘."""
    from dartlab.ai.tools.groundingCheck import groundingCheck

    answer = "ROE 는 12.3% <valueRef:value:samsung_fake:343> 이다."
    result = groundingCheck(answer=answer, refs=[])
    fake = result.data.get("fakeRefTokens") or []
    assert any("samsung_fake" in t or "fake" in t for t in fake)
    assert result.data.get("grounded") is False


def test_grounding_check_dispatch_via_registry():
    from dartlab.ai.tools.registry import executeTool

    result = executeTool(
        "GroundingCheck",
        {"answer": "ROE 12.3%", "refs": []},
    )
    # ToolResult.to_dict() — data 안에 grounded 등 분류 필드.
    assert "grounded" in (result.get("data") or {})
    assert result.get("data", {}).get("materialNumber") is True


# ── Korean disclosure evidence trail (cryptic-discovering-kettle E 트랙) ──


def test_grounding_check_korean_disclosure_claim_without_rcept_fails():
    """한국 공시 키워드 답변 + DART rceptNo payload 없음 → grounded=False + missing_dart_rcept."""
    from dartlab.ai.tools.groundingCheck import groundingCheck

    answer = "삼성전자 사외이사 비율 60% 다."
    result = groundingCheck(answer=answer, refs=[])
    assert result.data.get("koreanDisclosureClaim") is True
    assert result.data.get("dartRceptPresent") is False
    assert result.data.get("grounded") is False
    assert result.error == "grounding_check_missing_dart_rcept"


def test_grounding_check_korean_disclosure_claim_with_rcept_grounded():
    """한국 공시 키워드 답변 + ref payload.docId 14 자리 DART rcept → grounded=True."""
    from dartlab.ai.tools.groundingCheck import groundingCheck

    refs = [
        {
            "id": "doc:005930:20250404000000",
            "kind": "docRef",
            "title": "사업보고서",
            "source": "DART",
            "payload": {
                "docId": "20250404000000",
                "section": "II. 사업의 내용",
                "page": 42,
                "confidence": 95,
            },
        }
    ]
    answer = "삼성전자 사외이사 비율 60% <docRef:doc:005930:20250404000000> 다."
    result = groundingCheck(answer=answer, refs=refs)
    assert result.data.get("koreanDisclosureClaim") is True
    assert result.data.get("dartRceptPresent") is True
    assert result.data.get("grounded") is True


def test_grounding_check_non_korean_claim_not_affected():
    """한국 공시 키워드 없음 → koreanDisclosureClaim=False · DART rcept 검증 skip."""
    from dartlab.ai.tools.groundingCheck import groundingCheck

    answer = "Apple AAPL revenue grew 8% YoY."
    result = groundingCheck(answer=answer, refs=[])
    assert result.data.get("koreanDisclosureClaim") is False
    assert result.data.get("koreanEvidenceOk") is True


def test_evidence_gate_korean_skill_with_meta_rcept_missing():
    """engines.company.* skill 의 requiredEvidence 에 rceptNo 명시 → payload 안에 박힘 X 면 missing 분류."""
    from dartlab.ai.tools.evidenceGate import evidenceGate

    # ref 박혀있지만 payload.docId 없음 — 한국 공시 evidence 부족.
    refs = [
        {
            "id": "doc:005930:foo",
            "kind": "docRef",
            "title": "사업보고서",
            "payload": {"page": 42},  # docId 누락
        }
    ]
    result = evidenceGate("engines.company.executivePay", refs=refs)
    assert result.ok is True  # 도구 호출 자체는 성공
    assert result.data.get("isKoreanDisclosure") is True
    korean_missing = result.data.get("koreanMissing") or []
    assert any("rceptNo" in m for m in korean_missing)


def test_evidence_gate_korean_skill_with_full_payload_ok():
    """engines.company.* skill + payload.docId 14 자리 + section 박힘 → koreanMissing=[]."""
    from dartlab.ai.tools.evidenceGate import evidenceGate

    refs = [
        {
            "id": "doc:005930:20250404000000",
            "kind": "docRef",
            "title": "사업보고서",
            "payload": {
                "docId": "20250404000000",
                "section": "II. 사업의 내용",
                "page": 42,
            },
        }
    ]
    result = evidenceGate("engines.company.executivePay", refs=refs)
    assert result.data.get("isKoreanDisclosure") is True
    assert (result.data.get("koreanMissing") or []) == []


def test_evidence_gate_non_korean_skill_skips_dart_check():
    """non engines.company.* skill → isKoreanDisclosure=False · koreanMissing 검사 skip."""
    from dartlab.ai.tools.evidenceGate import evidenceGate

    result = evidenceGate("engines.scan", refs=[])
    assert result.data.get("isKoreanDisclosure") is False
    assert (result.data.get("koreanMissing") or []) == []


# ── 회귀: 새 도구 등록이 alias map / registry 다른 검사 안 깨뜨림 ────────


def test_new_tools_in_legacy_alias_map():
    """snake_case alias 도 함께 매핑."""
    from dartlab.ai.tools.registry import _LEGACY_NAME_MAP

    assert _LEGACY_NAME_MAP.get("outcome_log") == "OutcomeLog"
    assert _LEGACY_NAME_MAP.get("lookahead_guard") == "LookAheadGuard"
    assert _LEGACY_NAME_MAP.get("grounding_check") == "GroundingCheck"


def test_canonical_tool_names_includes_three_new_tools():
    from dartlab.ai.tools.registry import CANONICAL_TOOL_NAMES

    for name in ("OutcomeLog", "LookAheadGuard", "GroundingCheck"):
        assert name in CANONICAL_TOOL_NAMES, f"{name} 가 CANONICAL_TOOL_NAMES 에 없음"


# ── S4 RequestUserInput (elicit) ─────────────────────────────────────────────


def test_request_user_input_non_mcp_fallback():
    """non-MCP 컨텍스트 (CLI 직접 호출) — fallback dict 반환."""
    from dartlab.ai.tools.requestUserInput import requestUserInput

    result = requestUserInput(
        message="회사를 선택하세요",
        fields=[
            {"name": "company", "description": "분석 대상", "enum": ["005930", "AAPL"]},
        ],
    )
    assert result.ok is False
    assert result.error == "elicit_unsupported_transport"
    assert result.data.get("fallback") is True
    schema = result.data.get("requestedSchema") or {}
    assert schema.get("type") == "object"
    assert "company" in schema.get("properties", {})
    assert schema["properties"]["company"]["enum"] == ["005930", "AAPL"]


def test_request_user_input_dispatch_via_registry():
    from dartlab.ai.tools.registry import executeTool

    result = executeTool(
        "RequestUserInput",
        {"message": "select", "fields": [{"name": "x"}]},
    )
    # registry path 는 sync — non-MCP fallback.
    assert result.get("ok") is False
    assert result.get("error") == "elicit_unsupported_transport"


def test_build_elicit_schema_handles_missing_optional():
    from dartlab.ai.tools.requestUserInput import buildElicitSchema

    schema = buildElicitSchema(
        [
            {"name": "a"},
            {"name": "b", "type": "integer", "required": False},
        ]
    )
    assert schema["type"] == "object"
    assert schema["properties"]["a"] == {"type": "string"}
    assert schema["properties"]["b"] == {"type": "integer"}
    assert schema.get("required") == ["a"]


def test_request_user_input_in_legacy_alias_map():
    from dartlab.ai.tools.registry import _LEGACY_NAME_MAP

    assert _LEGACY_NAME_MAP.get("request_user_input") == "RequestUserInput"
