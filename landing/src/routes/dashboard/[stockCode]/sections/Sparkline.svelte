<script>
  // @ts-nocheck
  /** @type {{ data: number[], width?: number, height?: number, color?: string, fillOpacity?: number }} */
  let { data, width = 280, height = 64, color = '#fb923c', fillOpacity = 0.18 } = $props();

  const id = 'sg' + Math.random().toString(36).slice(2, 8);

  const min = $derived(Math.min(...data));
  const max = $derived(Math.max(...data));
  const range = $derived((max - min) || 1);
  const pad = 4;
  const w = $derived(width - pad * 2);
  const h = $derived(height - pad * 2);
  const step = $derived(w / (data.length - 1));

  const pts = $derived(
    data.map((v, i) => [pad + i * step, pad + h - ((v - min) / range) * h])
  );
  const line = $derived(
    pts.map((p, i) => (i === 0 ? `M ${p[0]} ${p[1]}` : `L ${p[0]} ${p[1]}`)).join(' ')
  );
  const area = $derived(
    line + ` L ${pts[pts.length - 1][0]} ${pad + h} L ${pad} ${pad + h} Z`
  );
  const last = $derived(pts[pts.length - 1]);
</script>

<svg width="100%" viewBox="0 0 {width} {height}" style="display:block">
  <defs>
    <linearGradient id={id} x1="0" x2="0" y1="0" y2="1">
      <stop offset="0%" stop-color={color} stop-opacity={fillOpacity} />
      <stop offset="100%" stop-color={color} stop-opacity="0" />
    </linearGradient>
  </defs>
  <path d={area} fill="url(#{id})" />
  <path d={line} fill="none" stroke={color} stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
  <circle cx={last[0]} cy={last[1]} r="3" fill={color} stroke="#0f1219" stroke-width="1.5" />
</svg>
