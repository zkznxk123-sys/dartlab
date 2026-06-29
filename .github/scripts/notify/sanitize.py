"""알림 sink 정화 — 제어/RTL/zero-width strip + 공백 정규화.

우리가 쓴 글이라 외부 untrusted 는 아니지만(=길이컷·제어문자 수준), 알림 본문에 보이지 않는 방향제어·
zero-width 가 섞이면 표시가 깨지거나 피싱처럼 보일 수 있어 발송 전 한 번 정화한다.
"""

from __future__ import annotations

import re
import unicodedata

# 제거 대상 코드포인트(소스 ASCII 유지 — 보이지 않는 문자를 리터럴로 박지 않는다):
#  - C0/C1 제어문자(일반 공백 \t\n\r 은 아래 공백 정규화가 흡수)
#  - bidi override/isolate (RTL 스푸핑): 200e 200f 202a-202e 2066-2069
#  - zero-width joiner/non-joiner/space + BOM: 200b-200d feff
_STRIP = (
    set(range(0x00, 0x09))
    | {0x0B, 0x0C}
    | set(range(0x0E, 0x20))
    | set(range(0x7F, 0xA0))
    | {0x200E, 0x200F, 0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069}
    | {0x200B, 0x200C, 0x200D, 0xFEFF}
)


def sanitize(text: str) -> str:
    if not text:
        return ""
    s = unicodedata.normalize("NFC", str(text))
    s = "".join(ch for ch in s if ord(ch) not in _STRIP)
    return re.sub(r"\s+", " ", s).strip()
