<script lang="ts">
	// panel 셀(raw DART XML) 렌더 — ui/web CellContent 이식. content-sniffing: html table / narrative.
	import DOMPurify from 'dompurify';
	import {
		normalizeDartXml,
		SANITIZE_CONFIG,
		splitHtmlAndText,
		absorbCaptionUnitFromText,
		stripInlineTags,
		parseMarkdownSubTables,
		refineSubTable,
		type MarkdownSubTable
	} from '$lib/viewer/cell';

	let { value }: { value: string } = $props();

	type Seg =
		| { kind: 'mdtables'; blocks: MarkdownSubTable[] }
		| { kind: 'htmltable'; html: string; caption: string; unit: string }
		| { kind: 'text'; text: string };

	function clean(html: string): string {
		return DOMPurify.sanitize(html, SANITIZE_CONFIG) as unknown as string;
	}

	function build(v: string): Seg[] {
		if (!v || !v.trim()) return [];
		// 옛 markdown table (raw XML 엔 드묾)
		if (v.includes('|') && /\n\s*\|/.test(v) && !/<\s*[a-zA-Z]/.test(v)) {
			const blocks = parseMarkdownSubTables(v).map(refineSubTable).filter((b) => b.rows.length > 0 || b.caption || b.unit);
			if (blocks.length > 0) return [{ kind: 'mdtables', blocks }];
		}
		const html = normalizeDartXml(v);
		if (/<\s*table[\s>]/i.test(html)) {
			const out: Seg[] = [];
			let pendingCaption = '';
			let pendingUnit = '';
			for (const [kind, body] of splitHtmlAndText(html)) {
				if (kind === 'text') {
					const { caption, unit, remaining } = absorbCaptionUnitFromText(stripInlineTags(body));
					if (caption) pendingCaption = pendingCaption ? `${pendingCaption} · ${caption}` : caption;
					if (unit) pendingUnit = pendingUnit || unit;
					if (remaining) out.push({ kind: 'text', text: remaining.replace(/&cr;/g, ' ') });
				} else {
					out.push({ kind: 'htmltable', html: clean(body), caption: pendingCaption, unit: pendingUnit });
					pendingCaption = '';
					pendingUnit = '';
				}
			}
			if (pendingCaption || pendingUnit) out.push({ kind: 'htmltable', html: '', caption: pendingCaption, unit: pendingUnit });
			return out;
		}
		if (!/<[a-zA-Z]/.test(html)) return [{ kind: 'text', text: html.replace(/&cr;/g, ' ') }];
		return [{ kind: 'htmltable', html: clean(html), caption: '', unit: '' }];
	}

	const segments = $derived(build(value));
</script>

{#if segments.length}
	<div class="space-y-3">
		{#each segments as seg, i (i)}
			{#if seg.kind === 'text'}
				<div class="whitespace-pre-wrap break-words text-sm leading-relaxed text-muted-foreground">{seg.text}</div>
			{:else if seg.kind === 'htmltable'}
				<div class="space-y-1">
					{#if seg.caption || seg.unit}
						<div class="flex items-baseline justify-between gap-2 text-[11px]">
							<div class="font-medium">{seg.caption}</div>
							{#if seg.unit}<div class="text-muted-foreground">{seg.unit}</div>{/if}
						</div>
					{/if}
					{#if seg.html}
						<!-- eslint-disable-next-line svelte/no-at-html-tags -->
						<div class="dartlab-html overflow-x-auto text-xs [&_td]:border [&_td]:border-border/40 [&_td]:px-1.5 [&_td]:py-0.5 [&_th]:border [&_th]:border-border/40 [&_th]:px-1.5 [&_th]:py-0.5">{@html seg.html}</div>
					{/if}
				</div>
			{:else}
				<div class="space-y-3">
					{#each seg.blocks as b, bi (bi)}
						<div class="space-y-1">
							{#if b.caption || b.unit}
								<div class="flex items-baseline justify-between gap-2 text-[11px]">
									<div class="font-medium">{b.caption}</div>
									{#if b.unit}<div class="text-muted-foreground">{b.unit}</div>{/if}
								</div>
							{/if}
							{#if b.rows.length}
								<table class="w-full border-collapse text-xs">
									<tbody>
										{#each b.rows as r, ri (ri)}
											<tr>
												{#each r as c, ci (ci)}
													<td class="border border-border/40 px-1.5 py-0.5 align-top">{c.replace(/&cr;/g, ' ')}</td>
												{/each}
											</tr>
										{/each}
									</tbody>
								</table>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		{/each}
	</div>
{/if}
