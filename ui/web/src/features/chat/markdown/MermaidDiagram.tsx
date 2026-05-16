// Mermaid 다이어그램 — 테마 변경 시마다 재 init + SVG 컨테이너 폭 100%.
import { useEffect, useId, useState } from 'react';

import { useTheme } from '@/shell/ThemeProvider';

let mermaidLib: typeof import('mermaid').default | null = null;

async function getMermaid() {
	if (!mermaidLib) {
		const mod = await import('mermaid');
		mermaidLib = mod.default;
	}
	return mermaidLib;
}

export function MermaidDiagram({ code }: { code: string }) {
	const id = useId().replace(/:/g, '_');
	const { theme } = useTheme();
	const isDark =
		theme === 'dark' ||
		(theme === 'system' &&
			typeof window !== 'undefined' &&
			window.matchMedia('(prefers-color-scheme: dark)').matches);
	const [svg, setSvg] = useState<string | null>(null);
	const [err, setErr] = useState<string | null>(null);

	useEffect(() => {
		let cancelled = false;
		setSvg(null);
		setErr(null);
		(async () => {
			try {
				const m = await getMermaid();
				// 매 렌더마다 재 init — 테마 변경 즉시 반영.
				m.initialize({
					startOnLoad: false,
					theme: isDark ? 'dark' : 'default',
					securityLevel: 'loose',
					fontFamily: 'inherit',
					fontSize: 16,
					flowchart: { htmlLabels: true, useMaxWidth: false, padding: 16, nodeSpacing: 50, rankSpacing: 60 },
					themeVariables: isDark
						? {
								primaryColor: '#1f2937',
								primaryTextColor: '#f3f4f6',
								primaryBorderColor: '#4b5563',
								lineColor: '#9ca3af',
								background: '#0a0a0a',
							}
						: {
								primaryColor: '#f3f4f6',
								primaryTextColor: '#111827',
								primaryBorderColor: '#9ca3af',
								lineColor: '#4b5563',
								background: '#ffffff',
							},
				});
				const out = await m.render(`mmd_${id}_${isDark ? 'd' : 'l'}`, code);
				// mermaid 가 박은 width/height/style 속성 제거 → CSS 가 컨테이너 폭 100% 강제.
				let cleaned = out.svg;
				cleaned = cleaned.replace(/<svg([^>]*?)\s+width="[^"]*"/, '<svg$1');
				cleaned = cleaned.replace(/<svg([^>]*?)\s+height="[^"]*"/, '<svg$1');
				cleaned = cleaned.replace(/<svg([^>]*?)\s+style="[^"]*"/, '<svg$1');
				if (!cancelled) setSvg(cleaned);
			} catch (e) {
				if (!cancelled) setErr((e as Error).message || 'mermaid render failed');
			}
		})();
		return () => {
			cancelled = true;
		};
	}, [code, id, isDark]);

	if (err) {
		return (
			<pre className="my-2 overflow-x-auto rounded-md border border-destructive/30 bg-destructive/5 p-3 text-xs font-mono text-destructive">
				{`mermaid 렌더 실패: ${err}\n\n${code}`}
			</pre>
		);
	}
	if (!svg) {
		return (
			<div className="my-2 rounded-md bg-muted/30 p-3 text-xs text-muted-foreground">
				다이어그램 렌더 중…
			</div>
		);
	}
	return (
		<div
			className="my-3 overflow-x-auto rounded-md border border-border bg-background p-4 [&_svg]:!h-auto [&_svg]:!max-w-full [&_svg]:!w-full [&_svg]:mx-auto [&_.nodeLabel]:!text-foreground [&_.edgeLabel]:!text-foreground [&_.edgeLabel]:!bg-background"
			dangerouslySetInnerHTML={{ __html: svg }}
		/>
	);
}
