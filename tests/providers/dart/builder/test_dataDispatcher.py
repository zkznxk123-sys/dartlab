"""providers/dart/builder/dataDispatcher.py mirror smoke — P6.

공개 show + docs 농장 은퇴 후 finance-only dispatch. sections/segments/direct dead
함수는 제거됨 — 본 미러는 생존 finance/report/strong 표면만 검증.
"""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    import dartlab.providers.dart.builder.dataDispatcher  # noqa: F401


def test_report_frame_callable() -> None:
    """reportFrame() callable smoke."""
    from dartlab.providers.dart.builder.dataDispatcher import reportFrame

    assert callable(reportFrame)


def test_report_frame_inner_callable() -> None:
    """reportFrameInner() callable smoke."""
    from dartlab.providers.dart.builder.dataDispatcher import reportFrameInner

    assert callable(reportFrameInner)


def test_show_finance_statement_callable() -> None:
    """showFinanceStatement() callable smoke."""
    from dartlab.providers.dart.builder.dataDispatcher import showFinanceStatement

    assert callable(showFinanceStatement)


def test_show_finance_topic_callable() -> None:
    """showFinanceTopic() callable smoke."""
    from dartlab.providers.dart.builder.dataDispatcher import showFinanceTopic

    assert callable(showFinanceTopic)


def test_show_impl_callable() -> None:
    """showImpl() callable smoke."""
    from dartlab.providers.dart.builder.dataDispatcher import showImpl

    assert callable(showImpl)


def test_show_report_topic_callable() -> None:
    """showReportTopic() callable smoke."""
    from dartlab.providers.dart.builder.dataDispatcher import showReportTopic

    assert callable(showReportTopic)


def test_trace_finance_topic_callable() -> None:
    """traceFinanceTopic() callable smoke."""
    from dartlab.providers.dart.builder.dataDispatcher import traceFinanceTopic

    assert callable(traceFinanceTopic)


def test_is_strong_topic_callable() -> None:
    """isStrongTopic() callable smoke — panel facade 강한 소스 라우팅 SSOT."""
    from dartlab.providers.dart.builder.dataDispatcher import isStrongTopic

    assert callable(isStrongTopic)
