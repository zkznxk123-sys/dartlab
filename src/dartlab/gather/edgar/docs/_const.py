"""gather EDGAR docs 공유 상수 — fetch/fetchHtmlParse/fetchUniverse 순환 회피용 base.

default-arg·module-level 로 쓰이는 단순 상수만 둔다(regex/dict 류는 fetch 에 잔존,
function-body 사용이라 bottom re-export 로 충분).
"""

HEADERS = {"User-Agent": "DartLab eddmpython@gmail.com"}
BASE_URL = "https://www.sec.gov"
DATA_URL = "https://data.sec.gov"
SINCE_YEAR = 2009
REQUEST_INTERVAL = 0.2
