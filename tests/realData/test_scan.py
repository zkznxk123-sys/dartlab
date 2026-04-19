"""scan 엔진 실제 데이터 스모크 — 전종목 횡단 프리빌드."""

from __future__ import annotations

import pytest


@pytest.mark.realData
@pytest.mark.integration
class TestScanEngine:
    """dartlab.scan(axis=...) 가 프리빌드 parquet 에서 즉시 로드 가능."""

    def test_axes_listed(self):
        """scan 이 노출하는 축 목록."""
        import dartlab

        axes = dartlab.scan.available_scans()
        assert axes
        assert isinstance(axes, list)

    def test_scanCallable_runsOnSampleAxis(self):
        """첫 번째 축을 실제로 호출해 None/빈 결과가 아님을 검증."""
        import dartlab

        axes = dartlab.scan.available_scans()
        if not axes:
            pytest.skip("scan axis 목록이 비어있음")
        sampleAxis = axes[0]
        result = dartlab.scan(axis=sampleAxis)
        # scan 은 DataFrame 또는 dict 반환 가능
        assert result is not None
        if hasattr(result, "height"):
            assert result.height > 0
        else:
            assert result, f"{sampleAxis} 축이 빈 결과"
