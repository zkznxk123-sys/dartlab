"""/send 인증 헤더 — Bearer(send.py 부착) + 결정적 nonce. HMAC 서명층 없음([06] §2).

nonce = sha1(f"{topic}:{slug}") — (topic, slug) 결정적이라 같은 발행 재push 는 허브에서 409(멱등).
blog·card 는 토픽이 달라 nonce 도 달라 둘 다 발송. send.py 는 반환된 `raw` 바이트를 그대로 전송(재직렬화 금지).
"""

from __future__ import annotations

import hashlib
import json


def authHeaders(payload: dict, ts: int, topic: str, slug: str) -> tuple[bytes, dict]:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    nonce = hashlib.sha1(f"{topic}:{slug}".encode()).hexdigest()
    return raw, {"X-DL-Ts": str(ts), "X-DL-Nonce": nonce}
