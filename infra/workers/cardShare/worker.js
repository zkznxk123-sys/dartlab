// 캐러셀 공유/OG 동적 엔드포인트 Cloudflare Worker (무료 티어).
//
// 정공법 = SSOT(hfMedia)에서 라이브로 읽어 파생뷰(OG)만 낸다. 정적 사이트(GitHub Pages)에 캐러셀마다
// HTML 을 굽지 않는다 — 그건 라이브 데이터를 정적 빌드에 복사·박제(drift + 캐러셀마다 재배포)라 우회.
// 이 워커는 /cards 가 브라우저에서 hfMedia 를 라이브로 읽는 것과 *동일 원리*를, 크롤러용으로 서버사이드에서
// 한다. hfProxy·news 워커가 "정적 사이트가 못 하는 라이브 HF 브리지"를 하는 것과 같은 패턴.
//
// 라우트: GET /c/<slug>
//   1) hfMedia carousels/index.json 라이브 read(엣지 캐시 10분 — index 는 재게시로 갱신되는 가변 파일).
//   2) slug 로 캐러셀 찾기 → og:title/description/image(첫 슬라이드 이미지) 생성.
//   3) 크롤러(스레드·인스타·카톡·X)는 <meta og:*> 만 읽고, 사람은 meta-refresh + JS 로 실제 캐러셀
//      (LANDING_BASE/cards?post=<slug>)로 즉시 이동.
//
// 새 캐러셀을 데이터로만 올려도(carousels/index.json 재게시) 그 공유 링크가 즉시 작동 — 워커·landing
// 재배포 0. og:image 는 이미 hfMedia 에 있는 첫 슬라이드를 가리키므로 추가 자산 생성도 없다.
//
// 무료 티어: 순수 fetch, nodejs_compat 불필요. 배포·도메인은 README.md.

const MEDIA_BASE = 'https://huggingface.co/datasets/eddmpython/dartlab-media/resolve/main';

// HTML 속성에 안전하게 박기 — &, <, >, ", ' 이스케이프(메타 content 주입 방지).
function esc(s) {
	return String(s == null ? '' : s)
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&#39;');
}

// sym(6자리 코드 또는 티커) → canonical media key (landing media.ts mediaKey 와 동일 규칙).
function mediaKey(sym) {
	return /^\d{6}$/.test(sym) ? sym : String(sym || '').toUpperCase();
}

// 캐러셀 첫 슬라이드 이미지 → 절대 og:image URL. 이슈(image 에 '/' 포함)는 hfMedia 상대경로 직접,
// 회사(semantic 파일명)는 companies/index.json 으로 해석. 못 풀면 null(브랜드 폴백).
async function resolveOgImage(post, companiesIndex) {
	const slide = (post.slides || []).find((s) => s && s.image);
	const image = slide && slide.image;
	if (!image) return null;
	if (image.includes('/')) return `${MEDIA_BASE}/${image.replace(/^\/+/, '')}`; // 이슈: issues/<slug>/cover.<hash>.webp
	const key = mediaKey(post.code || '');
	const company = companiesIndex && companiesIndex.companies && companiesIndex.companies[key];
	const asset = company && (company.assets || []).find((a) => a.name === image || a.name.startsWith(image + '.'));
	return asset ? `${MEDIA_BASE}/companies/${key}/${asset.name}` : null;
}

// 캡션 산문 첫 문단 → og:description(≤180자). 없으면 첫 슬라이드 line.
function ogDescription(post) {
	const cap = String(post.caption || '').split(/\n\s*\n/)[0].replace(/\s+/g, ' ').trim();
	if (cap) return cap.slice(0, 180);
	const slide = (post.slides || []).find((s) => s && (s.line || s.context));
	return String((slide && (slide.line || slide.context)) || post.name || '').replace(/\s+/g, ' ').trim().slice(0, 180);
}

// 엣지 캐시 헬퍼 — index 같은 가변 파일을 워커 엣지에 10분 보관(매 요청 HF 직타 방지).
async function cachedJson(url, ttl, ctx) {
	const key = new Request(url);
	const hit = await caches.default.match(key);
	if (hit) return hit.json();
	const r = await fetch(url, { headers: { 'User-Agent': 'dartlab-card-share/1.0' } });
	if (!r.ok) return null;
	const body = await r.text();
	const resp = new Response(body, { headers: { 'Content-Type': 'application/json', 'Cache-Control': `public, max-age=${ttl}` } });
	if (ctx) ctx.waitUntil(caches.default.put(key, resp.clone()));
	try { return JSON.parse(body); } catch { return null; }
}

export default {
	async fetch(req, env, ctx) {
		const LANDING_BASE = (env.LANDING_BASE || 'https://eddmpython.github.io/dartlab').replace(/\/+$/, '');
		const url = new URL(req.url);
		if (req.method !== 'GET' && req.method !== 'HEAD') return new Response('method not allowed', { status: 405 });

		const m = url.pathname.match(/^\/c\/([^/]+)\/?$/);
		if (!m) return Response.redirect(`${LANDING_BASE}/cards`, 302);
		const slug = decodeURIComponent(m[1]).replace(/[^0-9a-zA-Z가-힣\-_.]/g, '').slice(0, 80);
		const target = `${LANDING_BASE}/cards?post=${encodeURIComponent(slug)}`;

		// SSOT 라이브 read — carousels/index.json(가변, 10분 엣지) + companies/index.json(회사 이미지 해석용).
		const index = await cachedJson(`${MEDIA_BASE}/carousels/index.json`, 600, ctx);
		const post = index && Array.isArray(index.posts) && index.posts.find((p) => p.slug === slug);
		if (!post) return Response.redirect(target, 302); // 없는 슬러그 → 그냥 피드/딥링크로

		const companies = post.code ? await cachedJson(`${MEDIA_BASE}/companies/index.json`, 600, ctx) : null;
		const ogImage = await resolveOgImage(post, companies);
		const title = String(post.title || post.name || 'DartLab 카드').trim();
		const desc = ogDescription(post);
		const shareUrl = `${url.origin}/c/${encodeURIComponent(slug)}`;

		// 크롤러용 OG/twitter 메타 + 사람용 즉시 리다이렉트. body 는 폴백 링크만(JS 꺼져도 이동 가능).
		const html = `<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)} · DartLab</title>
<meta name="description" content="${esc(desc)}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="DartLab">
<meta property="og:title" content="${esc(title)}">
<meta property="og:description" content="${esc(desc)}">
<meta property="og:url" content="${esc(shareUrl)}">
${ogImage ? `<meta property="og:image" content="${esc(ogImage)}">
<meta property="og:image:alt" content="${esc(title)}">` : ''}
<meta name="twitter:card" content="${ogImage ? 'summary_large_image' : 'summary'}">
<meta name="twitter:title" content="${esc(title)}">
<meta name="twitter:description" content="${esc(desc)}">
${ogImage ? `<meta name="twitter:image" content="${esc(ogImage)}">` : ''}
<link rel="canonical" href="${esc(target)}">
<meta http-equiv="refresh" content="0; url=${esc(target)}">
<script>location.replace(${JSON.stringify(target)});</script>
</head>
<body style="background:#030509;color:#f1f5f9;font-family:system-ui,sans-serif;text-align:center;padding:18vh 8vw">
<p>카드를 여는 중…</p>
<p><a href="${esc(target)}" style="color:#fb923c">${esc(title)} 보러 가기 →</a></p>
</body>
</html>`;
		return new Response(req.method === 'HEAD' ? null : html, {
			headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'public, max-age=600' }
		});
	}
};
