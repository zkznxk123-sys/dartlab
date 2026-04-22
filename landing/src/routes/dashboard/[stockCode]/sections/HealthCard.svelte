<script>
  // @ts-nocheck
  /** @type {{ data: any }} */
  let { data: h } = $props();
  const zPct = $derived(Math.min(100, (h.altmanZ.value / 6) * 100));
</script>

<div class="card" id="health">
  <div class="card-title">HEALTH · 재무건전성</div>
  <h3>부도 위험과 회계 품질</h3>
  <div class="sub">Altman Z와 Beneish M 스코어로 재무 이상 징후 탐지.</div>

  <div class="grid">
    <div class="score safe">
      <div class="sh">
        <span class="slab">ALTMAN Z-SCORE</span>
        <span class="pill green">SAFE</span>
      </div>
      <div class="mono sv">{h.altmanZ.value}</div>
      <div class="z-track"></div>
      <div class="z-marker-wrap">
        <div class="z-marker" style:left="{zPct}%"></div>
      </div>
      <div class="z-labels mono">
        <span>Distress 1.81</span><span>Grey 2.99</span><span>Safe</span>
      </div>
    </div>

    <div class="score">
      <div class="sh">
        <span class="slab">BENEISH M-SCORE</span>
        <span class="pill green">CLEAN</span>
      </div>
      <div class="mono sv">{h.beneishM.value}</div>
      <div class="sflag">{h.beneishM.flag}</div>
      <div class="m-threshold-label">THRESHOLD · &gt; -1.78 = 높음</div>
      <div class="m-track">
        <div class="m-fill"></div>
        <div class="m-mark"></div>
      </div>
    </div>
  </div>

  <div class="flags">
    <div class="flags-head">경고 플래그 · {h.flags.length}건</div>
    <div class="flags-list">
      {#each h.flags as f}
        {@const color = f.level === 'warn' ? '#fbbf24' : f.level === 'alert' ? '#ef4444' : '#a6adbb'}
        <div class="flag"
          style:background={f.level === 'info' ? 'rgba(255,255,255,0.02)' : `${color}14`}
          style:border-color={f.level === 'info' ? 'var(--border)' : `${color}33`}>
          <div class="flag-dot" style:background={color}></div>
          <div class="flag-text" style:color={f.level === 'info' ? 'var(--text-mid)' : 'var(--text)'}>
            {f.text}
          </div>
        </div>
      {/each}
    </div>
  </div>
</div>

<style>
  .card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: var(--r-lg); padding: 24px; scroll-margin-top: 90px;
  }
  h3 { font-size: 20px; font-weight: 700; letter-spacing: -0.01em; margin: 6px 0 2px; color: var(--text); }
  .sub { color: var(--text-mid); font-size: 13px; margin-bottom: 20px; }

  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .score {
    padding: 18px; border: 1px solid var(--border); border-radius: var(--r-md);
  }
  .score.safe { background: rgba(52,211,153,0.04); }
  .sh { display: flex; justify-content: space-between; align-items: center; }
  .slab { font-size: 11px; color: var(--text-dim); letter-spacing: 0.1em; font-weight: 600; }
  .pill {
    display: inline-flex; align-items: center; padding: 3px 8px;
    border-radius: 999px; font-size: 10px; font-weight: 500;
    border: 1px solid;
  }
  .pill.green { color: #bbf7d0; background: rgba(52,211,153,0.08); border-color: rgba(52,211,153,0.25); }
  .sv { font-size: 36px; font-weight: 700; margin-top: 6px; letter-spacing: -0.02em; color: var(--text); }
  .sflag { font-size: 12px; color: var(--text-mid); margin-top: 4px; }

  .z-track {
    height: 10px; margin-top: 10px;
    background: linear-gradient(90deg, #ef4444 0%, #ef4444 30%, #fbbf24 30%, #fbbf24 50%, #34d399 50%, #34d399 100%);
    border-radius: 5px; opacity: 0.5;
  }
  .z-marker-wrap { position: relative; margin-top: -14px; }
  .z-marker {
    position: absolute; top: 0; width: 3px; height: 18px;
    background: #fff; transform: translateX(-50%);
    border-radius: 2px; box-shadow: 0 0 8px rgba(255,255,255,0.6);
  }
  .z-labels { display: flex; justify-content: space-between; font-size: 9px; color: var(--text-faint); margin-top: 6px; }

  .m-threshold-label { font-size: 10px; color: var(--text-faint); letter-spacing: 0.1em; margin: 14px 0 6px; }
  .m-track { height: 4px; background: rgba(255,255,255,0.06); border-radius: 2px; position: relative; }
  .m-fill { position: absolute; left: 0; top: 0; bottom: 0; width: 35%; background: var(--green); border-radius: 2px; }
  .m-mark { position: absolute; left: 35%; top: -2px; bottom: -2px; width: 2px; background: var(--yellow); }

  .flags { margin-top: 20px; }
  .flags-head { font-size: 11px; color: var(--text-dim); letter-spacing: 0.14em; font-weight: 600; margin-bottom: 10px; }
  .flags-list { display: flex; flex-direction: column; gap: 6px; }
  .flag {
    display: flex; align-items: center; gap: 12px;
    padding: 10px 14px; border: 1px solid; border-radius: 8px;
  }
  .flag-dot { width: 8px; height: 8px; border-radius: 2px; flex-shrink: 0; }
  .flag-text { font-size: 13px; }

  @media (max-width: 640px) { .grid { grid-template-columns: 1fr; } }
</style>
