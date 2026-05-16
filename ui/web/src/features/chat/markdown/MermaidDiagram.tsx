// Mermaid 다이어그램 — 본문 폭 친화 양식.
// 사이즈는 보수적 (fontSize 13, padding 8, spacing 작게) → 노드 폭 자연스럽게 200~280px 수준.
// 장기 해법: viz skill 에 채팅 폭 가이드 추가해서 AI 가 처음부터 적정 크기 / 노드 수 그릴 것.
// 현재 폴백: 노드 5 개 초과 LR/RL → TB 자동 회전.
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

function autoRotateDirection(code: string): string {
	const headerRe = /^(\s*(?:flowchart|graph)\s+)(LR|RL)\b/m;
	const m = headerRe.exec(code);
	if (!m) return code;
	const nodes = code.match(/\b[A-Za-z_]\w*\s*[([{]/g) ?? [];
	if (nodes.length <= 5) return code;
	return code.replace(headerRe, '$1TB');
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
				m.initialize({
					startOnLoad: false,
					theme: isDark ? 'dark' : 'default',
					securityLevel: 'loose',
					fontFamily: 'inherit',
					fontSize: 13,
					flowchart: {
						htmlLabels: true,
						useMaxWidth: false,
						padding: 8,
						nodeSpacing: 30,
						rankSpacing: 40,
						curve: 'basis',
					},
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
				const out = await m.render(`mmd_${id}_${isDark ? 'd' : 'l'}`, autoRotateDirection(code));
				// mermaid 가 박는 인라인 max-width style 만 제거. width/height 속성은 그대로 (자연 크기).
				const cleaned = out.svg.replace(/<svg([^>]*?)\s+style="[^"]*"/, '<svg$1');
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
		<div className="tiny-scroll my-3 max-h-[60vh] overflow-auto rounded-md border border-border bg-background p-3">
			<div
				className="flex justify-center [&_.edgeLabel]:!bg-background [&_.edgeLabel]:!text-foreground [&_.nodeLabel]:!text-foreground"
				dangerouslySetInnerHTML={{ __html: svg }}
			/>
		</div>
	);
}
