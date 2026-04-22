<script>
  // @ts-nocheck
  import RadarChart from './RadarChart.svelte';

  /** @type {{ data: any }} */
  let { data: c } = $props();

  const delta = $derived(((c.price - c.fairValue) / c.fairValue) * 100);
  const overvalued = $derived(delta > 0);
  const avg = $derived(
    (c.radar.company.reduce((a, b) => a + b, 0) / c.radar.company.length).toFixed(1)
  );
  const verdictColor = $derived(
    c.verdict.call === 'BUY' ? 'var(--green)' : c.verdict.call === 'SELL' ? 'var(--red)' : 'var(--yellow)'
  );
  const verdictLabel = $derived(({ BUY: '매수', HOLD: '보유', SELL: '매도' })[c.verdict.call]);

  // price-fair bar scaling
  const barMin = $derived(Math.min(c.fairRange[0], c.fairValue, c.price) * 0.9);
  const barMax = $derived(Math.max(c.fairRange[1], c.fairValue, c.price) * 1.05);
  const span = $derived(barMax - barMin);
  const pct = (v) => ((v - barMin) / span) * 100;
</script>

<section class="hero container reveal">
  <div class="hero-grid">
    <!-- LEFT: radar -->
    <div class="radar-wrap">
      <div class="head">
        <div>
          <div class="card-title">5축 Snowflake 스코어</div>
          <div class="sub">업종 중앙값 대비 · 5점 만점</div>
        </div>
        <div class="avg">
          <div class="mono avg-val">{avg}</div>
          <div class="avg-label">AVG</div>
        </div>
      </div>

      <div class="radar-slot">
        <RadarChart data={c.radar} size={380} />
      </div>

      <div class="legend">
        <span class="leg"><span class="sw sw-heat"></span> {c.name}</span>
        <span class="leg"><span class="sw sw-dash"></span> 업종 중앙값</span>
      </div>
    </div>

    <!-- RIGHT: identity + verdict + blog -->
    <div class="right">
      <div>
        <div class="meta">
          <span class="mono">{c.market}</span><span>·</span>
          <span class="mono">{c.code}</span><span>·</span>
          <span>{c.sector}</span>
        </div>
        <h1 class="name">{c.name}</h1>
        <div class="pills">
          <span class="pill">{c.subsector}</span>
          <span class="pill">생애주기 · {c.lifecycle}</span>
          <span class="pill">{c.type}</span>
          <span class="pill">CEO · {c.ceo}</span>
        </div>
      </div>

      <div class="verdict">
        <div class="verdict-head">
          <div class="vh-left">
            <span class="vh-label">AI VERDICT</span>
            <span class="vh-pill" style="background:{verdictColor}1a;color:{verdictColor};border-color:{verdictColor}66">
              {verdictLabel} · {c.verdict.call}
            </span>
          </div>
          <div class="vh-right">
            <span class="vh-label">CONFIDENCE</span>
            <span class="conf-track"><span class="conf-fill" style="width:{c.verdict.confidence}%"></span></span>
            <span class="mono conf-val">{c.verdict.confidence}%</span>
          </div>
        </div>
        <p class="verdict-text">{c.verdict.oneLiner}</p>

        <!-- price vs fair -->
        <div class="pf-head">
          <div>
            <div class="pf-label">현재가</div>
            <div class="mono pf-val">₩{c.price.toLocaleString()}</div>
            <div class="mono pf-change {c.priceChange < 0 ? 'red' : 'green'}">
              {c.priceChange > 0 ? '+' : ''}{c.priceChange}%
            </div>
          </div>
          <div style="text-align:right">
            <div class="pf-label">BLENDED 적정가</div>
            <div class="mono pf-val dim">₩{c.fairValue.toLocaleString()}</div>
            <div class="mono pf-change {overvalued ? 'red' : 'green'}">
              {overvalued ? '▲' : '▼'} {delta.toFixed(1)}% {overvalued ? '고평가' : '저평가'}
            </div>
          </div>
        </div>

        <div class="pf-bar">
          <div class="pf-track"></div>
          <div class="pf-range" style="left:{pct(c.fairRange[0])}%;width:{pct(c.fairRange[1]) - pct(c.fairRange[0])}%"></div>
          <div class="pf-fair" style="left:calc({pct(c.fairValue)}% - 1px)"></div>
          <div class="pf-fair-label" style="left:{pct(c.fairValue)}%">적정</div>
          <div class="pf-price-wrap" style="left:calc({pct(c.price)}% - 9px)">
            <div class="pf-price"></div>
          </div>
        </div>
      </div>

      <!-- blog CTA -->
      <a href="#" class="blog-cta">
        <div class="blog-icon">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M3 3H9C10.1 3 11 3.9 11 5V16C11 15.45 10.55 15 10 15H3V3Z" stroke="#fb923c" stroke-width="1.5"/>
            <path d="M15 3H11V15H14C14.55 15 15 15.45 15 16V3Z" stroke="#fb923c" stroke-width="1.5"/>
          </svg>
        </div>
        <div class="blog-body">
          <div class="blog-eyebrow">블로그 심층분석</div>
          <div class="blog-title">{c.blog.title}</div>
          <div class="blog-meta">
            <span>{c.blog.date}</span><span>·</span><span>{c.blog.readTime} 읽기</span>
          </div>
        </div>
        <div class="blog-arrow">→</div>
      </a>
    </div>
  </div>
</section>

<style>
  .hero { padding-top: 40px; padding-bottom: 20px; }
  .hero-grid {
    display: grid; grid-template-columns: 45fr 55fr; gap: 28px; align-items: stretch;
  }
  .radar-wrap {
    background: linear-gradient(180deg, rgba(234,70,71,0.04), rgba(15,18,25,0.6));
    border: 1px solid var(--border);
    border-radius: var(--r-xl);
    padding: 28px 24px 20px;
    position: relative; overflow: hidden;
  }
  .head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
  .sub { font-size: 13px; color: var(--text-mid); margin-top: 6px; }
  .avg { text-align: right; }
  .avg-val {
    font-size: 30px; font-weight: 700; letter-spacing: -0.02em;
    background: var(--grad-heat);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  .avg-label { font-size: 10px; color: var(--text-dim); letter-spacing: 0.08em; }
  .radar-slot { display: grid; place-items: center; padding: 8px 0 16px; }
  .legend {
    display: flex; gap: 18px; justify-content: center;
    padding-top: 14px; border-top: 1px solid var(--border); margin-top: 8px;
  }
  .leg { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-mid); }
  .sw { width: 18px; height: 3px; border-radius: 2px; }
  .sw-heat { background: linear-gradient(135deg,#ea4647,#fb923c); }
  .sw-dash { border-top: 2px dashed rgba(255,255,255,0.5); height: 0; }

  .right { display: flex; flex-direction: column; gap: 20px; }
  .meta { display: flex; align-items: center; gap: 10px; color: var(--text-dim); font-size: 12px; }
  .name { margin: 8px 0 12px; font-size: 56px; font-weight: 800; letter-spacing: -0.035em; line-height: 1; color: var(--text); }
  .pills { display: flex; gap: 6px; flex-wrap: wrap; }

  .verdict {
    background: var(--card); border: 1px solid var(--border);
    border-radius: var(--r-lg); padding: 20px;
    position: relative; overflow: hidden;
  }
  .verdict-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
  .vh-left, .vh-right { display: flex; align-items: center; gap: 10px; }
  .vh-label { font-size: 10px; letter-spacing: 0.14em; color: var(--text-dim); font-weight: 600; }
  .vh-pill { padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 13px; border: 1px solid; letter-spacing: 0.04em; }
  .conf-track { width: 100px; height: 6px; border-radius: 3px; background: rgba(255,255,255,0.06); position: relative; overflow: hidden; display: inline-block; }
  .conf-fill { position: absolute; inset: 0; background: var(--grad-heat); border-radius: 3px; }
  .conf-val { font-size: 12px; color: var(--text); }
  .verdict-text { margin: 12px 0 18px; font-size: 14px; line-height: 1.55; color: var(--text); text-wrap: pretty; }

  .pf-head { display: flex; justify-content: space-between; margin-bottom: 10px; }
  .pf-label { font-size: 11px; color: var(--text-dim); letter-spacing: 0.08em; }
  .pf-val { font-size: 22px; font-weight: 700; color: var(--text); }
  .pf-val.dim { color: var(--text-mid); }
  .pf-change { font-size: 11px; }
  .pf-change.red { color: var(--red); }
  .pf-change.green { color: var(--green); }

  .pf-bar { position: relative; height: 42px; margin-top: 4px; }
  .pf-track { position: absolute; left: 0; right: 0; top: 18px; height: 6px; background: rgba(255,255,255,0.04); border-radius: 3px; }
  .pf-range {
    position: absolute; top: 18px; height: 6px; border-radius: 3px;
    background: linear-gradient(90deg, rgba(52,211,153,0.4), rgba(52,211,153,0.15));
    border: 1px solid rgba(52,211,153,0.35);
  }
  .pf-fair { position: absolute; top: 10px; width: 2px; height: 22px; background: rgba(255,255,255,0.5); }
  .pf-fair-label { position: absolute; top: 34px; transform: translateX(-50%); font-size: 9px; color: var(--text-dim); white-space: nowrap; }
  .pf-price-wrap { position: absolute; top: 6px; width: 18px; height: 30px; pointer-events: none; }
  .pf-price {
    width: 18px; height: 18px; border-radius: 50%;
    background: var(--grad-heat); border: 2px solid var(--card);
    box-shadow: 0 0 0 1px rgba(234,70,71,0.4), 0 4px 12px rgba(234,70,71,0.4);
  }

  .blog-cta {
    display: flex; align-items: center; gap: 16px;
    padding: 16px 18px; border: 1px solid var(--border); border-radius: var(--r-lg);
    background: linear-gradient(90deg, rgba(234,70,71,0.08), transparent);
    text-decoration: none; color: inherit; transition: border-color .2s;
  }
  .blog-cta:hover { border-color: var(--border-accent); }
  .blog-icon {
    width: 44px; height: 44px; border-radius: 10px; flex-shrink: 0;
    background: var(--grad-heat-soft);
    border: 1px solid var(--border-accent);
    display: grid; place-items: center;
  }
  .blog-body { flex: 1; min-width: 0; }
  .blog-eyebrow { font-size: 10px; letter-spacing: 0.14em; font-weight: 600; color: var(--orange); margin-bottom: 4px; }
  .blog-title { font-size: 15px; font-weight: 600; letter-spacing: -0.01em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--text); }
  .blog-meta { display: flex; gap: 10px; margin-top: 2px; font-size: 11px; color: var(--text-dim); }
  .blog-arrow { font-size: 22px; color: var(--orange); }

  @media (max-width: 900px) { .hero-grid { grid-template-columns: 1fr; } }
</style>
