<script>
  // @ts-nocheck
  /** @type {{ data: number[], width?: number, height?: number, color?: string }} */
  let { data, width = 280, height = 64, color = '#fb923c' } = $props();

  const min = $derived(Math.min(...data, 0));
  const max = $derived(Math.max(...data));
  const range = $derived((max - min) || 1);
  const pad = 4;
  const w = $derived(width - pad * 2);
  const h = $derived(height - pad * 2);
  const bw = $derived((w / data.length) * 0.7);
  const gap = $derived((w / data.length) * 0.3);
  const zeroY = $derived(pad + h - ((0 - min) / range) * h);
</script>

<svg width="100%" viewBox="0 0 {width} {height}" style="display:block">
  {#each data as v, i}
    {@const x = pad + i * (bw + gap)}
    {@const vy = pad + h - ((v - min) / range) * h}
    {@const top = v >= 0 ? vy : zeroY}
    {@const bh = Math.abs(zeroY - vy)}
    <rect
      x={x} y={top} width={bw} height={Math.max(bh, 1)}
      fill={v >= 0 ? color : '#ef4444'}
      opacity={i === data.length - 1 ? 1 : 0.55}
      rx="1"
    />
  {/each}
</svg>
