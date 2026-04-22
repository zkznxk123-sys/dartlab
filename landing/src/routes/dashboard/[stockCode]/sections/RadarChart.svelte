<script>
  // @ts-nocheck
  /** @type {{ data: { axes: string[], company: number[], sector: number[] }, size?: number }} */
  let { data, size = 360 } = $props();

  const cx = $derived(size / 2);
  const cy = $derived(size / 2);
  const r = $derived(size * 0.38);
  const n = $derived(data.axes.length);

  function pt(val, i, radius = r) {
    const angle = -Math.PI / 2 + (i * 2 * Math.PI) / n;
    const rr = (val / 5) * radius;
    return [cx + rr * Math.cos(angle), cy + rr * Math.sin(angle)];
  }

  function poly(vals) {
    return vals.map((v, i) => pt(v, i).join(',')).join(' ');
  }

  const rings = [1, 2, 3, 4, 5];
  const avg = $derived(
    (data.company.reduce((a, b) => a + b, 0) / data.company.length).toFixed(1)
  );
</script>

<svg viewBox="0 0 {size} {size}" width="100%" style="max-width:{size}px;display:block">
  <defs>
    <linearGradient id="radarFill" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0%" stop-color="#ea4647" stop-opacity="0.55" />
      <stop offset="100%" stop-color="#fb923c" stop-opacity="0.35" />
    </linearGradient>
    <radialGradient id="radarGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#ea4647" stop-opacity="0.18" />
      <stop offset="100%" stop-color="#ea4647" stop-opacity="0" />
    </radialGradient>
  </defs>

  <circle {cx} {cy} r={r * 1.2} fill="url(#radarGlow)" />

  {#each rings as ring}
    <polygon
      points={data.axes.map((_, idx) => pt(ring, idx).join(',')).join(' ')}
      fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="1"
    />
  {/each}

  {#each data.axes as _, i}
    {@const p = pt(5, i)}
    <line x1={cx} y1={cy} x2={p[0]} y2={p[1]} stroke="rgba(255,255,255,0.05)" stroke-width="1" />
  {/each}

  <polygon points={poly(data.sector)} fill="rgba(255,255,255,0.05)"
    stroke="rgba(255,255,255,0.25)" stroke-width="1" stroke-dasharray="3 3" />

  <polygon points={poly(data.company)} fill="url(#radarFill)" stroke="#ea4647" stroke-width="1.5" />

  {#each data.company as v, i}
    {@const p = pt(v, i)}
    <circle cx={p[0]} cy={p[1]} r="4" fill="#fb923c" stroke="#050811" stroke-width="2" />
  {/each}

  {#each data.axes as label, i}
    {@const p = pt(5.9, i)}
    {@const v = data.company[i]}
    {@const sv = data.sector[i]}
    {@const delta = (v - sv).toFixed(1)}
    {@const sign = v >= sv ? '+' : ''}
    {@const anchor = Math.abs(p[0] - cx) < 4 ? 'middle' : (p[0] > cx ? 'start' : 'end')}
    <g>
      <text x={p[0]} y={p[1] - 6} fill="#e8ecf5" font-size="12" font-weight="600"
        text-anchor={anchor} dominant-baseline="middle">{label}</text>
      <text x={p[0]} y={p[1] + 10} fill="#6b7280" font-size="10"
        text-anchor={anchor} dominant-baseline="middle" font-family="var(--font-mono)">
        {v.toFixed(1)} <tspan fill={v >= sv ? '#34d399' : '#ef4444'}>({sign}{delta})</tspan>
      </text>
    </g>
  {/each}
</svg>
