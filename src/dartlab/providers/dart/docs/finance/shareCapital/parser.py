"""주식의 총수 테이블 파서."""

from dartlab.core.tableParser import parseAmount

FIELD_MAP = {
    "발행할 주식의 총수": "authorizedShares",
    "현재까지 발행한 주식의 총수": "issuedShares",
    "현재까지 감소한 주식의 총수": "retiredShares",
    "발행주식의 총수": "outstandingShares",
    "자기주식수": "treasuryShares",
    "유통주식수": "floatingShares",
    "자기주식 보유비율": "treasuryRatio",
}


def parseShareCapitalTable(content: str, *, includePreferred: bool = False) -> dict | None:
    """주식의 총수 테이블 파싱.

    Ⅰ~Ⅶ 번호 체계에서 발행주식/자기주식/유통주식 추출.
    표는 (label, [빈셀], 보통주, 우선주, 합계, 비고) 순서.

    Args:
        content: section_content 마크다운 텍스트
        includePreferred: True면 우선주 필드도 추출 (preferred* 키 추가)

    Returns:
        dict with keys: authorizedShares, issuedShares, retiredShares,
            outstandingShares, treasuryShares, floatingShares, treasuryRatio
        includePreferred=True일 때 추가: preferredOutstanding, preferredTreasury,
            preferredFloating, preferredIssued
        또는 발행주식 총수를 추출할 수 없으면 None
    """
    lines = content.split("\n")
    result: dict = {}

    # 우선주는 outstandingShares/treasuryShares/floatingShares/issuedShares만 캡쳐
    _PREF_FIELDS = {
        "outstandingShares": "preferredOutstanding",
        "treasuryShares": "preferredTreasury",
        "floatingShares": "preferredFloating",
        "issuedShares": "preferredIssued",
    }

    for line in lines:
        s = line.strip()
        if not s.startswith("|"):
            continue

        cells = [c.strip() for c in s.split("|")]
        if cells and cells[0] == "":
            cells = cells[1:]
        if cells and cells[-1] == "":
            cells = cells[:-1]

        if len(cells) < 3:
            continue

        txt = " ".join(cells[:2])
        for keyword, field in FIELD_MAP.items():
            if keyword in txt:
                # 숫자 셀들을 등장 순서대로 수집 — [공통, 우선, 합계] 또는 [공통]
                nums: list[float] = []
                for ci in range(1, len(cells)):
                    v = parseAmount(cells[ci])
                    if v is not None:
                        nums.append(v)
                if not nums:
                    break
                result[field] = nums[0]  # 보통주 (하위호환)
                if includePreferred and field in _PREF_FIELDS:
                    # 우선주 식별: nums = [공통, 우선, 합계] 일 때만 우선주 인정.
                    # 합계 검증: |공통 + 우선 - 합계| / 합계 < 0.001
                    # 우선주 없는 종목은 보통 [공통, 공통] 또는 [공통, 합계=공통] → 우선주=0
                    pref = 0.0
                    if len(nums) >= 3:
                        c, p, t = nums[0], nums[1], nums[2]
                        if t > 0 and abs(c + p - t) / t < 0.001:
                            pref = p
                    result[_PREF_FIELDS[field]] = pref
                break

    if not result.get("outstandingShares"):
        return None
    return result
