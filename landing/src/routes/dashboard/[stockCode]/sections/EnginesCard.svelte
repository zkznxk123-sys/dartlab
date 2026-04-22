<script>
  // @ts-nocheck
  /** @type {{ data: any[] }} */
  let { data: engines } = $props();
</script>

<div id="engines">
  <div class="head">
    <div class="eyebrow"><span class="bar"></span>ENGINES · 이 대시보드를 만드는 5개 엔진</div>
    <h2>analysis · credit · macro · quant · industry</h2>
    <div class="sub">L2 엔진은 서로 import 하지 않습니다. 각자 독립된 데이터 파이프라인. Composition은 review 계층의 몫.</div>
  </div>

  <div class="grid">
    {#each engines as e}
      <div class="ecard" style:--ecolor={e.color}>
        <div class="halo"></div>
        <div class="top">
          <div class="glyph">{e.name[0]}</div>
          <div>
            <div class="ename">{e.name}</div>
            <div class="ekr">{e.nameKr}</div>
          </div>
        </div>
        <div class="tag">{e.tagline}</div>

        {#if e.metric}
          <div class="metric">
            <div class="ml">{e.metric.label}</div>
            <div class="mono mv">{e.metric.value}</div>
            <div class="ms">{e.metric.sub}</div>
          </div>
        {/if}

        <div class="section">
          <div class="sec-h">OUTPUT</div>
          <div class="chips">
            {#each e.outputs as o}
              <span class="chip">{o}</span>
            {/each}
          </div>
        </div>

        <div class="divider"></div>
        <div class="section">
          <div class="sec-h">POWERS</div>
          <div class="powers">{e.powers.join(' · ')}</div>
        </div>
      </div>
    {/each}
  </div>
</div>

<style>
  #engines { scroll-margin-top: 90px; }
  .head { margin-bottom: 18px; }
  .eyebrow {
    font-size: 11px; font-weight: 600; letter-spacing: 0.16em;
    color: var(--orange); text-transform: uppercase;
    display: flex; align-items: center; gap: 8px;
  }
  .bar { width: 18px; height: 1px; background: var(--grad-heat); }
  h2 { font-size: 28px; font-weight: 700; letter-spacing: -0.02em; margin: 6px 0 4px; color: var(--text); }
  .sub { color: var(--text-mid); font-size: 14px; max-width: 640px; }

  .grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }

  .ecard {
    padding: 18px;
    background: linear-gradient(180deg, color-mix(in srgb, var(--ecolor) 7%, transparent), var(--card) 60%);
    border: 1px solid var(--border);
    border-radius: var(--r-md);
    position: relative; overflow: hidden;
    transition: transform .2s, border-color .2s;
  }
  .ecard:hover { transform: translateY(-2px); border-color: color-mix(in srgb, var(--ecolor) 33%, transparent); }
  .halo {
    position: absolute; top: -24px; right: -24px; width: 80px; height: 80px; border-radius: 50%;
    background: radial-gradient(circle, color-mix(in srgb, var(--ecolor) 20%, transparent), transparent 60%);
    pointer-events: none;
  }
  .top { display: flex; align-items: center; gap: 8px; position: relative; }
  .glyph {
    width: 28px; height: 28px; border-radius: 7px; flex-shrink: 0;
    background: color-mix(in srgb, var(--ecolor) 13%, transparent);
    border: 1px solid color-mix(in srgb, var(--ecolor) 27%, transparent);
    display: grid; place-items: center; color: var(--ecolor);
    font-weight: 800; font-size: 13px;
  }
  .ename { font-size: 13px; font-weight: 700; letter-spacing: -0.01em; color: var(--text); }
  .ekr { font-size: 10px; color: var(--text-dim); }
  .tag { font-size: 12px; color: var(--text-mid); margin-top: 12px; line-height: 1.45; }

  .metric {
    margin-top: 12px; padding: 10px 12px;
    background: color-mix(in srgb, var(--ecolor) 6%, transparent);
    border: 1px solid color-mix(in srgb, var(--ecolor) 20%, transparent);
    border-radius: 8px;
  }
  .ml { font-size: 9px; letter-spacing: 0.12em; color: var(--ecolor); font-weight: 700; }
  .mv { font-size: 18px; font-weight: 700; margin-top: 2px; color: var(--text); }
  .ms { font-size: 10px; color: var(--text-dim); }

  .section { margin-top: 12px; }
  .sec-h { font-size: 9px; letter-spacing: 0.12em; color: var(--text-faint); font-weight: 700; margin-bottom: 6px; }
  .chips { display: flex; flex-wrap: wrap; gap: 4px; }
  .chip {
    font-size: 10px; padding: 3px 7px; border-radius: 4px;
    background: rgba(255,255,255,0.03);
    border: 1px solid var(--border);
    color: var(--text-mid);
  }
  .divider { height: 1px; background: var(--border); margin-top: 10px; }
  .powers { font-size: 11px; color: var(--ecolor); font-weight: 500; }

  @media (max-width: 1100px) { .grid { grid-template-columns: repeat(2, 1fr); } }
  @media (max-width: 600px) { .grid { grid-template-columns: 1fr; } }
</style>
