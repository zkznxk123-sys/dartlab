"""발행 러너 회귀 — detect/payload/nonce. 실제 frontmatter(description)·_issues(target.*) 형태로 검증.

git 의존(detect 의 `_git`)은 monkeypatch 로 끊고, 파일은 tmp_path 에 실제로 깔아 정규식·frontmatter·이벤트
구성을 검사한다(원격/실git 불요). slug 가 라이브 +page.ts normalizePath 와 동형인지, nonce 가 (topic,slug)
결정적인지가 핵심 회귀.
"""

from __future__ import annotations

import json

from notify import send as send_mod
from notify.authHeaders import authHeaders
from notify.payload import PublishEvent, buildPayload
from notify.send import detect


def _blog(tmp_path, body: str):
    d = tmp_path / "blog" / "05-company-reports" / "01-000660-skhynix"
    d.mkdir(parents=True)
    (d / "index.md").write_text(body, "utf-8")
    return "blog/05-company-reports/01-000660-skhynix/index.md"


def test_blog_detect(tmp_path, monkeypatch):
    f = _blog(tmp_path, '---\ntitle: "SK하이닉스"\ndescription: "요약 한 줄"\n---\n본문')
    monkeypatch.setattr(send_mod, "_git", lambda root, *a: f + "\n")
    evs = detect("aaa", "bbb", tmp_path)
    assert len(evs) == 1
    e = evs[0]
    assert e.topic == "blogPublish"
    assert e.slug == "000660-skhynix"  # \d+- 뒤 그룹 = 라이브 slug 동형
    assert e.title == "SK하이닉스"
    assert e.summary == "요약 한 줄"


def test_blog_with_carousel_emits_both(tmp_path, monkeypatch):
    f = _blog(tmp_path, '---\ntitle: "SK"\ndescription: "요약"\ncarousel:\n  title: "카드 제목"\n---\n')
    monkeypatch.setattr(send_mod, "_git", lambda root, *a: f + "\n")
    evs = detect("aaa", "bbb", tmp_path)
    assert [e.topic for e in evs] == ["blogPublish", "cardPublish"]


def test_company_blog_without_carousel_skips_card(tmp_path, monkeypatch):
    f = _blog(tmp_path, '---\ntitle: "회사글"\ndescription: "캐러셀 없음"\n---\n')
    monkeypatch.setattr(send_mod, "_git", lambda root, *a: f + "\n")
    evs = detect("aaa", "bbb", tmp_path)
    assert [e.topic for e in evs] == ["blogPublish"]  # KeyError 없이 card skip


def test_issue_card_detect(tmp_path, monkeypatch):
    d = tmp_path / "blog" / "_issues" / "my-issue"
    d.mkdir(parents=True)
    plan = {"target": {"slug": "my-issue", "title": "이슈 제목"}, "planning": {"cardThesis": "한 줄 논지"}}
    (d / "cards.plan.json").write_text(json.dumps(plan, ensure_ascii=False), "utf-8")
    monkeypatch.setattr(send_mod, "_git", lambda root, *a: "blog/_issues/my-issue/cards.plan.json\n")
    evs = detect("aaa", "bbb", tmp_path)
    assert len(evs) == 1
    e = evs[0]
    assert e.topic == "cardPublish"
    assert e.slug == "my-issue"
    assert e.title == "이슈 제목"  # target 하위
    assert e.summary == "한 줄 논지"  # planning.cardThesis


def test_non_publish_path_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr(send_mod, "_git", lambda root, *a: "blog/PIPELINE.md\nsrc/dartlab/x.py\n")
    assert detect("aaa", "bbb", tmp_path) == []


def test_payload_urls_and_titles():
    b = buildPayload(PublishEvent("blogPublish", "my-slug", "제목", "요약"))
    assert b["notification"]["url"] == "/blog/my-slug"
    assert b["notification"]["tag"] == "blog:my-slug"
    assert b["notification"]["title"].startswith("[새 글]")
    assert b["notification"]["body"] == "요약"
    c = buildPayload(PublishEvent("cardPublish", "my-slug", "제목", "요약"))
    assert c["notification"]["url"] == "/cards?post=my-slug"
    assert c["notification"]["title"].startswith("[새 카드]")


def test_nonce_deterministic_by_topic_slug():
    p = {"x": 1}
    _, h1 = authHeaders(p, 1, "blogPublish", "s")
    _, h2 = authHeaders(p, 999, "blogPublish", "s")
    assert h1["X-DL-Nonce"] == h2["X-DL-Nonce"]  # ts 무관, 같은 (topic,slug) = 같은 nonce
    _, h3 = authHeaders(p, 1, "cardPublish", "s")
    assert h1["X-DL-Nonce"] != h3["X-DL-Nonce"]  # 다른 topic = 다른 nonce


def test_raw_bytes_sent_verbatim():
    p = {"topic": "blogPublish", "notification": {"title": "가", "body": "나", "url": "/blog/x", "tag": "blog:x"}}
    raw, _ = authHeaders(p, 1, "blogPublish", "x")
    assert json.loads(raw.decode("utf-8")) == p  # 재직렬화 없이 그대로
