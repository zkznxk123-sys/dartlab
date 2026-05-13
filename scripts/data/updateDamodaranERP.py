"""Damodaran ERP 월별 갱신 스크립트.

실행:
    uv run python -X utf8 scripts/data/updateDamodaranERP.py

동작:
    1. pages.stern.nyu.edu/~adamodar/ 의 ctryprem.html 파싱
    2. 국가별 Moody's rating + adj default spread + total ERP 추출
    3. src/dartlab/reference/data/damodaranDefaults.json 업데이트
    4. 실패 시 기존 스냅샷 보존 (폴백 안전)

Damodaran 이 매년 1월/7월 갱신하므로 월 1회 cron 적합.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_TARGET = _REPO_ROOT / "src" / "dartlab" / "core" / "data" / "damodaranDefaults.json"
_URL = "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html"


def _fetchHtml() -> str | None:
    """Damodaran ctryprem.html 원문 다운로드."""
    try:
        req = urllib.request.Request(_URL, headers={"User-Agent": "dartlab/1.0 (research)"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            # encoding 자동 감지 fallback
            for enc in ("utf-8", "windows-1252", "latin-1"):
                try:
                    return raw.decode(enc)
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", errors="replace")
    except (OSError, ValueError) as e:
        print(f"[updateDamodaran] fetch 실패: {e}", file=sys.stderr)
        return None


def _extractMatureMarketERP(html: str) -> float | None:
    """Mature market equity risk premium (US base) 추출.

    Damodaran 페이지 상단에 'mature market' 수치가 나오는 패턴 매칭.
    """
    # 예: "mature market equity risk premium...4.60%"
    m = re.search(r"mature\s+market[^.]*?(\d+\.\d+)\s*%", html, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


def _extractCountries(html: str) -> dict[str, dict]:
    """국가 테이블 파싱.

    테이블 형태가 변할 수 있으므로 관대한 regex 매칭.
    표준 컬럼: Country | Rating | Adj Default Spread | Total ERP | Country Risk Premium
    """
    # 간단한 tr/td 파싱 (BeautifulSoup 의존 회피)
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.DOTALL | re.IGNORECASE)
    out: dict[str, dict] = {}
    for row in rows:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.DOTALL | re.IGNORECASE)
        if len(cells) < 4:
            continue
        clean = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        name = clean[0]
        if not name or len(name) > 50:
            continue
        # 숫자 추출 시도
        nums: list[float] = []
        for c in clean[1:]:
            m = re.search(r"(\d+\.\d+)\s*%?", c)
            if m:
                try:
                    nums.append(float(m.group(1)))
                except ValueError:
                    pass
        if len(nums) < 2:
            continue
        # 컬럼 순서는 변할 수 있음 — 최빈 패턴: rating text, default spread, total ERP, CRP
        out[name] = {
            "rawNumbers": nums,
        }
    return out


def _resolveIso2(countryName: str) -> str | None:
    """국가명 → ISO2 (필요한 주요 국가만)."""
    mapping = {
        "korea": "KR",
        "south korea": "KR",
        "republic of korea": "KR",
        "united states": "US",
        "usa": "US",
        "japan": "JP",
        "china": "CN",
        "germany": "DE",
        "united kingdom": "GB",
        "uk": "GB",
        "taiwan": "TW",
        "hong kong": "HK",
        "india": "IN",
        "brazil": "BR",
        "france": "FR",
        "canada": "CA",
        "australia": "AU",
        "singapore": "SG",
    }
    key = countryName.strip().lower()
    return mapping.get(key)


def updateDefaults() -> bool:
    """ctryprem.html 파싱 → damodaranDefaults.json 업데이트. 성공 시 True."""
    html = _fetchHtml()
    if not html:
        return False

    mature = _extractMatureMarketERP(html) or 4.60
    countries_raw = _extractCountries(html)

    if not _TARGET.exists():
        print(f"[updateDamodaran] target missing: {_TARGET}", file=sys.stderr)
        return False

    # 기존 파일 로드 (다른 필드 보존)
    try:
        with _TARGET.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[updateDamodaran] existing load 실패: {e}", file=sys.stderr)
        return False

    # 매핑 가능한 국가만 업데이트 (나머지는 기존 스냅샷 유지)
    updated = 0
    for name, info in countries_raw.items():
        iso = _resolveIso2(name)
        if not iso:
            continue
        nums = info.get("rawNumbers") or []
        if len(nums) < 2:
            continue
        # heuristic: 가장 큰 퍼센트가 total ERP, 그 다음이 Rf 또는 CRP
        nums_sorted = sorted(nums, reverse=True)
        total = nums_sorted[0]
        if total <= mature or total > 15.0:
            continue
        crp = max(0.0, total - mature)
        if iso in data.get("countries", {}):
            data["countries"][iso]["totalERP"] = round(total, 2)
            data["countries"][iso]["countryRiskPremium"] = round(crp, 2)
            updated += 1

    data.setdefault("_meta", {})
    data["_meta"]["matureMarketERP"] = mature
    data["_meta"]["asOfDate"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data["_meta"]["updatedBy"] = "scripts/data/updateDamodaranERP.py"

    with _TARGET.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"[updateDamodaran] {updated}개 국가 갱신 완료 (mature={mature}%)")
    return True


if __name__ == "__main__":
    ok = updateDefaults()
    sys.exit(0 if ok else 1)
