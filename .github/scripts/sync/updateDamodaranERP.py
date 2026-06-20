"""Damodaran ERP 월별 갱신 스크립트 (gather fetch 위임).

실행:
    uv run python -X utf8 .github/scripts/sync/updateDamodaranERP.py

동작:
    1. gather SSOT(``getDamodaranCountryErp``)로 ctryprem.html fetch+파싱 (외부 fetch=gather)
    2. 국가별 total ERP → ISO2 매핑 + countryRiskPremium 산출 (sink 해석)
    3. src/dartlab/reference/data/damodaranDefaults.json 병합 갱신
    4. 실패 시 기존 스냅샷 보존 (폴백 안전)

Damodaran 이 매년 1월/7월 갱신하므로 월 1회 적합. 외부 fetch·HTML 파싱은 본 스크립트가
재구현하지 않고 gather(Extract) SSOT 에 위임한다 — 별도빌드 금지.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from dartlab.gather.sources.damodaran import getDamodaranCountryErp

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_TARGET = _REPO_ROOT / "src" / "dartlab" / "reference" / "data" / "damodaranDefaults.json"


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
    return mapping.get(countryName.strip().lower())


def updateDefaults() -> bool:
    """gather fetch → ISO2 매핑 → damodaranDefaults.json 병합. 성공 시 True."""
    erp = getDamodaranCountryErp()
    if not erp:
        return False

    mature = erp.get("matureMarketERP") or 4.60
    countries_raw = erp.get("countries") or {}

    if not _TARGET.exists():
        print(f"[updateDamodaran] target missing: {_TARGET}", file=sys.stderr)
        return False

    try:
        with _TARGET.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[updateDamodaran] existing load 실패: {e}", file=sys.stderr)
        return False

    updated = 0
    for name, info in countries_raw.items():
        iso = _resolveIso2(name)
        if not iso:
            continue
        nums = info.get("rawNumbers") or []
        if len(nums) < 2:
            continue
        # heuristic: 가장 큰 퍼센트가 total ERP
        total = sorted(nums, reverse=True)[0]
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
    data["_meta"]["updatedBy"] = ".github/scripts/sync/updateDamodaranERP.py"

    with _TARGET.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"[updateDamodaran] {updated}개 국가 갱신 완료 (mature={mature}%)")
    return True


if __name__ == "__main__":
    ok = updateDefaults()
    sys.exit(0 if ok else 1)
