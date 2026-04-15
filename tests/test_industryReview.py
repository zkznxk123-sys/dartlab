"""Industry 엔진 → review 블록 통합 테스트."""

from __future__ import annotations

import pytest

from dartlab.review.builders import chainPositionBlock
from dartlab.review.catalog import getBlockMeta


pytestmark = pytest.mark.unit


def test_catalog_registers_chain_position():
    meta = getBlockMeta("chainPosition")
    assert meta is not None
    assert meta.label == "산업 밸류체인 내 위치"
    assert meta.section == "비교분석"


def test_chain_position_block_handles_none():
    assert chainPositionBlock(None) == []


def test_chain_position_block_handles_empty_dict():
    assert chainPositionBlock({}) == []


def test_chain_position_block_full_payload():
    data = {
        "industry": "semiconductor",
        "industryName": "반도체",
        "stage": "fab",
        "stageName": "전공정(FAB)",
        "role": "제조",
        "stream": "midstream",
        "confidence": 0.92,
        "source": "docs",
        "peers": [
            {"stockCode": "000660", "corpName": "SK하이닉스", "confidence": 0.95},
            {"stockCode": "042700", "corpName": "한미반도체", "confidence": 0.8},
        ],
    }
    blocks = chainPositionBlock(data)
    # Heading + Text + Table (peers 있음)
    assert len(blocks) == 3
    kinds = [type(b).__name__ for b in blocks]
    assert kinds == ["HeadingBlock", "TextBlock", "TableBlock"]


def test_chain_position_block_no_peers():
    data = {
        "industry": "steel",
        "industryName": "철강",
        "stage": "mill",
        "stageName": "제강",
        "role": "제조",
        "stream": "midstream",
        "confidence": 0.7,
        "source": "product",
        "peers": [],
    }
    blocks = chainPositionBlock(data)
    # peers 없으면 Table 생략
    assert len(blocks) == 2


def test_chain_position_block_low_confidence_label():
    data = {
        "industry": "x",
        "industryName": "기타",
        "stage": "y",
        "stageName": "미분류",
        "role": "",
        "stream": "",
        "confidence": 0.4,
        "source": "kindlist",
        "peers": [],
    }
    blocks = chainPositionBlock(data)
    # 저신뢰 문구 포함
    texts = [getattr(b, "text", "") for b in blocks]
    assert any("저신뢰" in t for t in texts)
