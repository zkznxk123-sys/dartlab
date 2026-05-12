"""providers/dart/builder/dataDispatcher.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    import dartlab.providers.dart.builder.dataDispatcher  # noqa: F401


def test_horizontalize_table_block_callable() -> None:
    """horizontalizeTableBlock() callable smoke."""
    from dartlab.providers.dart.builder.dataDispatcher import horizontalizeTableBlock

    assert callable(horizontalizeTableBlock)


def test_report_frame_callable() -> None:
    """reportFrame() callable smoke."""
    from dartlab.providers.dart.builder.dataDispatcher import reportFrame

    assert callable(reportFrame)


def test_report_frame_inner_callable() -> None:
    """reportFrameInner() callable smoke."""
    from dartlab.providers.dart.builder.dataDispatcher import reportFrameInner

    assert callable(reportFrameInner)


def test_show_direct_topic_callable() -> None:
    """showDirectTopic() callable smoke."""
    from dartlab.providers.dart.builder.dataDispatcher import showDirectTopic

    assert callable(showDirectTopic)


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


def test_show_section_block_callable() -> None:
    """showSectionBlock() callable smoke."""
    from dartlab.providers.dart.builder.dataDispatcher import showSectionBlock

    assert callable(showSectionBlock)


def test_show_sections_topic_callable() -> None:
    """showSectionsTopic() callable smoke."""
    from dartlab.providers.dart.builder.dataDispatcher import showSectionsTopic

    assert callable(showSectionsTopic)


def test_show_segments_sub_callable() -> None:
    """showSegmentsSub() callable smoke."""
    from dartlab.providers.dart.builder.dataDispatcher import showSegmentsSub

    assert callable(showSegmentsSub)


def test_trace_finance_topic_callable() -> None:
    """traceFinanceTopic() callable smoke."""
    from dartlab.providers.dart.builder.dataDispatcher import traceFinanceTopic

    assert callable(traceFinanceTopic)
