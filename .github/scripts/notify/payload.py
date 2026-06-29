"""발행 알림 본문 조립 — 토픽별 url/tag, body=description.

url 은 **app-path(base 없음)** — `/blog/{slug}`·`/cards?post={slug}`. BASE_PATH `/dartlab` 접두는 SW 가
한 곳에서 붙인다([07] §1·[08] §1). payload 에 base 박지 않음(SSOT 1곳). 라이브 라우트 정합:
blog = `/blog/[slug]`, card = `/cards?post=`(`/cards/[slug]` 부재, share.ts cardShareUrl 와 동형).
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from notify.sanitize import sanitize


@dataclass
class PublishEvent:
    topic: str  # 'blogPublish' | 'cardPublish'
    slug: str
    title: str
    summary: str


def buildPayload(ev: PublishEvent) -> dict:
    if ev.topic == "blogPublish":
        url = f"/blog/{quote(ev.slug)}"
        tag = f"blog:{ev.slug}"
        title = "[새 글] " + ev.title
    else:
        url = f"/cards?post={quote(ev.slug)}"
        tag = f"card:{ev.slug}"
        title = "[새 카드] " + ev.title
    return {
        "topic": ev.topic,
        "notification": {
            "title": sanitize(title)[:120],
            "body": sanitize(ev.summary)[:120],
            "url": url,
            "tag": tag,
        },
    }
