<script>
  // @ts-nocheck
  /** @type {{ data: { value: any, price: number } }} */
  let { data } = $props();
  const value = $derived(data.value);
  const price = $derived(data.price);

  const maxFair = $derived(Math.max(...value.methods.map((m) => m.fair), price));
  const scale = (v) => (v / (maxFair * 1.15)) * 100;
  const mosColor = $derived(value.mos < 0 ? 'var(--red)' : 'var(--green)');

  const scenarios = $derived([
    { key: 'bull', label: 'Bull', icon: '▲', color: 'var(--green)', ...value.scenarios.bull },
    { key: 'base', label: 'Base', icon: '●', color: 'var(--orange)', ...value.scenarios.base },
    { key: 'bear', label: 'Bear', icon: '▼', color: 'var(--red)', ...value.scenarios.bear }
  ]);
</script>

<div class="card" id="value">
  <div class="grid">
    <div>
      <div class="card-title">VALUE · 적정가 추정</div>
      <h3>네 가지 방법으로 본 적정가</h3>
      <div class="sub">DCF · DDM · RIM · 상대가치, 가중 평균으로 블렌딩.</div>

      <div class="methods">
        {#each value.methods as m}
          <div class="method">
            <div class="row">
              <div class="lhs">
                <span class="m-name">{m.name}</span>
                <span class="mono m-w">w={m.weight}%</span>
              </div>
              <span class="mono m-val">₩{m.fair.toLocaleString()}</span>
            </div>
            <div class="track"><div class="fill" style:width="{scale(m.fair)}%"></div></div>
          </div>
        {/each}

        <div class="current">
          <div class="row">
            <span class="m-name strong">현재가</span>
            <span class="mono m-val strong">₩{price.toLocaleString()}</span>
          </div>
          <div class="track"><div class="fill white" style:width="{scale(price)}%"></div></div>
        </div>
      </div>
    </div>

    <div class="right">
      <div class="mos">
        <div class="mos-label">MARGIN OF SAFETY</div>
        <div class="mos-val mono" style:color={mosColor}>
          {value.mos > 0 ? '+' : ''}{value.mos}%
        </div>
        <div class="mos-sub">
          현재가가 블렌딩 적정가 대비 {Math.abs(value.mos)}% {value.mos < 0 ? '고평가' : '저평가'}
        </div>
      </div>

      <div>
        <div class="sc-head">시나리오 목표가</div>
        <div class="scenarios">
          {#each scenarios as s}
            <div class="sc">
              <span class="sc-icon" style:color={s.color}>{s.icon}</span>
              <span class="sc-label">{s.label}</span>
              <span class="mono sc-target">₩{s.target.toLocaleString()}</span>
              <div class="sc-prob">
                <div class="sc-track"><div class="sc-fill" style:width="{s.prob}%" style:background={s.color}></div></div>
                <span class="mono sc-pct">{s.prob}%</span>
              </div>
            </div>
          {/each}
        </div>
      </div>
    </div>
  </div>
</div>

<style>
  .card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: var(--r-lg); padding: 24px; scroll-margin-top: 90px;
  }
  .grid { display: grid; grid-template-columns: 1.2fr 1fr; gap: 28px; }
  h3 { font-size: 20px; font-weight: 700; letter-spacing: -0.01em; margin: 6px 0 2px; color: var(--text); }
  .sub { color: var(--text-mid); font-size: 13px; margin-bottom: 18px; }

  .methods { display: flex; flex-direction: column; gap: 10px; margin-top: 18px; }
  .row { display: flex; justify-content: space-between; margin-bottom: 4px; }
  .lhs { display: flex; align-items: center; gap: 8px; }
  .m-name { font-size: 12px; font-weight: 600; color: var(--text); }
  .m-name.strong { font-size: 12px; color: var(--text); }
  .m-w { font-size: 10px; color: var(--text-faint); }
  .m-val { font-size: 13px; color: var(--text); }
  .m-val.strong { font-size: 13px; font-weight: 700; }
  .track { position: relative; height: 6px; background: rgba(255,255,255,0.04); border-radius: 3px; }
  .fill {
    position: absolute; inset: 0;
    background: linear-gradient(90deg, rgba(234,70,71,0.6), rgba(251,146,60,0.6));
    border-radius: 3px;
  }
  .fill.white { background: rgba(255,255,255,0.5); }
  .current { margin-top: 6px; padding-top: 12px; border-top: 1px solid var(--border); }

  .right { display: flex; flex-direction: column; gap: 20px; }
  .mos {
    background: rgba(234,70,71,0.06); border: 1px solid rgba(234,70,71,0.2);
    border-radius: var(--r-md); padding: 18px;
  }
  .mos-label { font-size: 10px; letter-spacing: 0.14em; color: var(--text-dim); font-weight: 600; }
  .mos-val { font-size: 44px; font-weight: 700; letter-spacing: -0.03em; margin-top: 6px; line-height: 1; }
  .mos-sub { font-size: 12px; color: var(--text-mid); margin-top: 6px; }

  .sc-head { font-size: 11px; letter-spacing: 0.14em; color: var(--text-dim); font-weight: 600; margin-bottom: 10px; }
  .scenarios { display: flex; flex-direction: column; gap: 6px; }
  .sc {
    display: grid; grid-template-columns: auto 1fr auto auto;
    align-items: center; gap: 10px; padding: 10px 12px;
    background: rgba(255,255,255,0.02); border-radius: 8px; border: 1px solid var(--border);
  }
  .sc-icon { font-size: 11px; }
  .sc-label { font-size: 12px; font-weight: 600; color: var(--text); }
  .sc-target { font-size: 13px; color: var(--text); }
  .sc-prob { display: flex; align-items: center; gap: 6px; }
  .sc-track { width: 40px; height: 4px; background: rgba(255,255,255,0.06); border-radius: 2px; }
  .sc-fill { height: 100%; border-radius: 2px; }
  .sc-pct { font-size: 10px; color: var(--text-dim); width: 26px; text-align: right; }

  @media (max-width: 820px) { .grid { grid-template-columns: 1fr; } }
</style>
