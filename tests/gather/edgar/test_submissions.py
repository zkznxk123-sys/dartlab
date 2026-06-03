"""providers/edgar/openapi/submissions.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.core.edgarClient  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_filings_frame_callable() -> None:
    """filingsFrame() callable smoke."""
    from dartlab.gather.edgar.submissions import filingsFrame

    assert callable(filingsFrame)


def test_find_regular_filings_callable() -> None:
    """findRegularFilings() callable smoke."""
    from dartlab.gather.edgar.submissions import findRegularFilings

    assert callable(findRegularFilings)


def test_get_submissions_json_callable() -> None:
    """getSubmissionsJson() callable smoke."""
    from dartlab.gather.edgar.submissions import getSubmissionsJson

    assert callable(getSubmissionsJson)


def test_merge_submission_filings_callable() -> None:
    """mergeSubmissionFilings() callable smoke."""
    from dartlab.gather.edgar.submissions import mergeSubmissionFilings

    assert callable(mergeSubmissionFilings)
