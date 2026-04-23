<script>
  // @ts-nocheck
  /** @type {{ data: { thesis: any, blog: any, githubStars?: number, version?: string } }} */
  let { data } = $props();
  const thesis = $derived(data.thesis);
  const blog = $derived(data.blog);
</script>

<div class="thesis card" id="thesis">
  <div class="grid">
    <div>
      <div class="card-title">AI THESIS · 종합 서술</div>
      <h3>한 단락으로 이 회사</h3>
      <p class="summary">{thesis.summary}</p>

      <div class="sw-grid">
        <div>
          <div class="sw-eyebrow green">+ 강점</div>
          <div class="sw-pills">
            {#each thesis.strengths as s}<span class="pill green">{s}</span>{/each}
          </div>
        </div>
        <div>
          <div class="sw-eyebrow red">− 약점</div>
          <div class="sw-pills">
            {#each thesis.weaknesses as s}<span class="pill red">{s}</span>{/each}
          </div>
        </div>
      </div>
    </div>

    <a href="#" class="blog-card">
      <div class="halo"></div>
      <div class="eyebrow">DARTLAB BLOG · 심층분석</div>
      <h4 class="blog-title">{blog.title}</h4>
      <p class="blog-excerpt">{blog.excerpt}</p>
      <div class="spacer"></div>
      <div class="blog-foot">
        <div class="mono blog-meta">
          <span>{blog.date}</span><span>·</span><span>{blog.readTime}</span>
        </div>
        <span class="read-more">읽기 →</span>
      </div>
    </a>
  </div>
</div>

<section class="bottom container">
  <div class="cta-box">
    <div class="glow-a"></div>
    <div class="glow-b"></div>
    <div class="cta-body">
      <div class="os-eyebrow">OPEN SOURCE · APACHE 2.0</div>
      <h2 class="cta-title">
        이 대시보드는 무료 공개입니다.<br/>
        계속 만들 수 있게 <span class="grad">도와주세요</span>.
      </h2>
      <p class="cta-desc">
        dartlab은 1인 개발 프로젝트입니다. 전 상장사 데이터 수집·보관·분석 비용을 후원으로 충당합니다. GitHub Star만 눌러주셔도 큰 힘이 됩니다.
      </p>
      <div class="cta-row">
        <a href="https://www.buymeacoffee.com/" class="btn btn-primary">
          <span>☕</span> Buy Me A Coffee
        </a>
        <a href="https://github.com/eddmpython/dartlab" class="btn">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 .25a8 8 0 0 0-2.53 15.59c.4.07.55-.17.55-.38v-1.37c-2.23.48-2.7-1.07-2.7-1.07-.36-.93-.89-1.17-.89-1.17-.73-.5.05-.49.05-.49.8.06 1.23.83 1.23.83.72 1.23 1.88.87 2.34.67.07-.52.28-.88.51-1.08-1.78-.2-3.65-.89-3.65-3.96 0-.88.31-1.6.83-2.16-.08-.2-.36-1.02.08-2.12 0 0 .67-.22 2.2.82A7.67 7.67 0 0 1 8 4.36c.68 0 1.37.09 2.01.27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.28.82 2.16 0 3.08-1.87 3.76-3.66 3.95.29.25.54.74.54 1.48v2.2c0 .21.15.46.55.38A8 8 0 0 0 8 .25z"/>
          </svg>
          GitHub Star
          <span class="mono stars">{data.githubStars ?? 9}</span>
        </a>
        <a href="https://pypi.org/project/dartlab/" class="btn btn-ghost">pip install dartlab →</a>
      </div>
    </div>
  </div>

  <footer class="footer">
    <div class="fl">
      <span class="mono">dartlab {data.version ?? 'v0.2.4'}</span>
      <span>·</span><span>Apache License 2.0</span>
      <span>·</span><span>© 2026 eddmpython</span>
    </div>
    <div class="fr">
      <a href="#">Docs</a><a href="#">PyPI</a><a href="#">GitHub</a><a href="#">Blog</a>
    </div>
  </footer>
</section>

<style>
  .card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: var(--r-lg); padding: 24px; scroll-margin-top: 90px;
  }
  .grid { display: grid; grid-template-columns: 1.3fr 1fr; gap: 28px; }
  h3 { font-size: 20px; font-weight: 700; letter-spacing: -0.01em; margin: 6px 0 2px; color: var(--text); }
  .summary { font-size: 15px; line-height: 1.65; color: var(--text); margin-top: 14px; text-wrap: pretty; }
  .sw-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 18px; }
  .sw-eyebrow { font-size: 10px; letter-spacing: 0.14em; font-weight: 700; margin-bottom: 8px; }
  .sw-eyebrow.green { color: var(--green); }
  .sw-eyebrow.red { color: var(--red); }
  .sw-pills { display: flex; flex-wrap: wrap; gap: 6px; }
  .pill {
    display: inline-flex; align-items: center; padding: 5px 10px;
    border-radius: 999px; font-size: 12px; font-weight: 500; border: 1px solid;
  }
  .pill.red { color: #fecaca; background: rgba(234, 70, 71, 0.1); border-color: rgba(234, 70, 71, 0.3); }
  .pill.green { color: #bbf7d0; background: rgba(52, 211, 153, 0.08); border-color: rgba(52, 211, 153, 0.25); }

  .blog-card {
    display: flex; flex-direction: column; padding: 22px;
    background: linear-gradient(180deg, rgba(234,70,71,0.1), rgba(15,18,25,0.6));
    border: 1px solid var(--border-accent); border-radius: var(--r-md);
    position: relative; overflow: hidden; text-decoration: none; color: inherit;
    transition: transform .2s;
  }
  .blog-card:hover { transform: translateY(-2px); }
  .halo {
    position: absolute; top: -30px; right: -30px; width: 160px; height: 160px;
    background: radial-gradient(circle, rgba(234,70,71,0.25), transparent 60%);
    pointer-events: none;
  }
  .eyebrow { font-size: 10px; letter-spacing: 0.14em; font-weight: 700; color: var(--orange); }
  .blog-title { font-size: 22px; font-weight: 700; letter-spacing: -0.02em; margin: 14px 0 10px; line-height: 1.25; color: var(--text); position: relative; z-index: 1; }
  .blog-excerpt { font-size: 13px; color: var(--text-mid); line-height: 1.55; margin: 0; text-wrap: pretty; }
  .spacer { flex: 1; }
  .blog-foot { display: flex; align-items: center; justify-content: space-between; margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border); }
  .blog-meta { display: flex; gap: 10px; font-size: 11px; color: var(--text-dim); }
  .read-more { font-size: 13px; font-weight: 600; color: var(--orange); }

  .bottom { padding: 56px 0 40px; }
  .cta-box {
    position: relative; overflow: hidden;
    border-radius: var(--r-xl); padding: 48px 40px;
    background: linear-gradient(135deg, #1a0b0b 0%, #0f1219 60%);
    border: 1px solid var(--border-accent);
  }
  .glow-a { position: absolute; top: -80px; left: -60px; width: 400px; height: 400px; background: radial-gradient(circle, rgba(234,70,71,0.18), transparent 70%); pointer-events: none; }
  .glow-b { position: absolute; bottom: -120px; right: -80px; width: 420px; height: 420px; background: radial-gradient(circle, rgba(251,146,60,0.12), transparent 70%); pointer-events: none; }
  .cta-body { position: relative; max-width: 720px; }
  .os-eyebrow { font-size: 11px; letter-spacing: 0.2em; color: var(--orange); font-weight: 700; }
  .cta-title { font-size: 40px; font-weight: 800; letter-spacing: -0.025em; margin: 10px 0 14px; line-height: 1.15; text-wrap: pretty; color: var(--text); }
  .grad { background: var(--grad-heat); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
  .cta-desc { font-size: 15px; color: var(--text-mid); max-width: 560px; line-height: 1.6; }
  .cta-row { display: flex; gap: 10px; margin-top: 24px; flex-wrap: wrap; }

  .btn {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 12px 20px; border-radius: 10px;
    font-size: 14px; font-weight: 500;
    border: 1px solid var(--border); background: rgba(255,255,255,0.03);
    color: var(--text); text-decoration: none; cursor: pointer;
    transition: all .15s;
  }
  .btn:hover { background: rgba(255,255,255,0.06); border-color: var(--border-hi); }
  .btn-primary { background: var(--grad-heat); color: #fff; border-color: transparent; font-weight: 600; }
  .btn-ghost { background: transparent; border-color: transparent; color: var(--text-mid); }
  .btn-ghost:hover { background: rgba(255,255,255,0.05); }
  .stars { font-size: 11px; color: var(--text-dim); margin-left: 4px; }

  .footer {
    display: flex; justify-content: space-between; align-items: center;
    margin-top: 40px; padding-top: 24px; border-top: 1px solid var(--border);
    font-size: 12px; color: var(--text-dim);
  }
  .fl { display: flex; gap: 20px; align-items: center; }
  .fr { display: flex; gap: 16px; }
  .fr a { color: var(--text-dim); text-decoration: none; }

  @media (max-width: 820px) { .grid { grid-template-columns: 1fr; } }
  @media (max-width: 600px) { .footer { flex-direction: column; gap: 10px; align-items: flex-start; } }
</style>
