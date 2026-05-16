// react-markdown + remark-gfm — ChatGPT/Claude 양식 타이포.
// @tailwindcss/typography 미사용 — 컴포넌트별 명시 스타일링.
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { MermaidDiagram } from './MermaidDiagram';

// evidenceRef 마커 정리 — AI 가 본문에 박은 `evidenceRef:call_xxx` 양식 raw 인용을 화면에서 제거.
// 후속에서 ref 시스템으로 별도 chip 표시 (v2).
function cleanEvidenceRefs(text: string): string {
	return (
		text
			// 백틱 감싸진 `evidenceRef:xxx` 통째 제거
			.replace(/`evidenceRef:[^`]*`/g, '')
			// 백틱 없는 evidenceRef:xxx 도 제거 (라인 끝까지 또는 공백까지)
			.replace(/evidenceRef:[A-Za-z0-9_\-]+/g, '')
			// "출처:" 만 남으면 그 줄 자체 삭제
			.replace(/^\s*출처:\s*[,，·\s]*$/gm, '')
			// 빈 줄 3 개 이상 → 2 개로
			.replace(/\n{3,}/g, '\n\n')
	);
}

// CJK 인접 bold 인식 보강 — commonmark 는 `**bold**가` 처럼 한국어 조사가 붙으면
// 닫는 `**` 를 word-boundary 로 인식 못 해 raw 별표가 본문에 노출됨.
// 닫는 `**` 뒤에 한글이 바로 붙으면 zero-width space 를 끼워서 boundary 보장.
function fixCjkBold(text: string): string {
	return text.replace(/\*\*([^\s*][\s\S]*?[^\s*]|\S)\*\*(?=[가-힣ぁ-んァ-ヴー一-龥])/g, '**$1**​');
}

export function MarkdownText({ text }: { text: string }) {
	const cleaned = fixCjkBold(cleanEvidenceRefs(text));
	return (
		<div className="text-[15px] leading-[1.75] text-foreground">
			<ReactMarkdown
				remarkPlugins={[remarkGfm]}
				components={{
					p({ children }) {
						return <p className="my-3 first:mt-0 last:mb-0">{children}</p>;
					},
					strong({ children }) {
						return <strong className="font-semibold text-foreground">{children}</strong>;
					},
					em({ children }) {
						return <em className="italic">{children}</em>;
					},
					ul({ children }) {
						return (
							<ul className="my-3 ml-6 list-disc space-y-1.5 marker:text-muted-foreground/70">
								{children}
							</ul>
						);
					},
					ol({ children }) {
						return (
							<ol className="my-3 ml-6 list-decimal space-y-1.5 marker:text-muted-foreground/70">
								{children}
							</ol>
						);
					},
					li({ children }) {
						return <li className="pl-1.5">{children}</li>;
					},
					h1({ children }) {
						return <h1 className="mt-5 mb-3 text-xl font-bold tracking-tight">{children}</h1>;
					},
					h2({ children }) {
						return (
							<h2 className="mt-5 mb-2 text-lg font-semibold tracking-tight">{children}</h2>
						);
					},
					h3({ children }) {
						return (
							<h3 className="mt-4 mb-1.5 text-base font-semibold tracking-tight">{children}</h3>
						);
					},
					h4({ children }) {
						return (
							<h4 className="mt-3 mb-1 text-sm font-semibold tracking-tight">{children}</h4>
						);
					},
					blockquote({ children }) {
						return (
							<blockquote className="my-2 border-l-2 border-border pl-3 text-muted-foreground italic">
								{children}
							</blockquote>
						);
					},
					hr() {
						return <hr className="my-3 border-border" />;
					},
					a({ children, ...rest }) {
						return (
							<a
								{...rest}
								target="_blank"
								rel="noopener noreferrer"
								className="text-foreground underline decoration-muted-foreground underline-offset-2 hover:decoration-foreground"
							>
								{children}
							</a>
						);
					},
					code(props) {
						const { children, className, ...rest } = props;
						const lang = /language-([\w-]+)/.exec(className ?? '')?.[1];
						if (lang === 'mermaid') {
							return <MermaidDiagram code={String(children).trim()} />;
						}
						if (lang) {
							return (
								<pre className="my-2 overflow-x-auto rounded-md bg-muted/50 p-3 text-[13px] leading-6 font-mono">
									<code className={className} {...rest}>
										{children}
									</code>
								</pre>
							);
						}
						return (
							<code
								className="rounded bg-muted/60 px-1.5 py-0.5 text-[0.9em] font-mono"
								{...rest}
							>
								{children}
							</code>
						);
					},
					pre({ children }) {
						return <>{children}</>;
					},
					table({ children }) {
						return (
							<div className="my-3 overflow-x-auto rounded-md border border-border">
								<table className="w-full text-xs">{children}</table>
							</div>
						);
					},
					thead({ children }) {
						return <thead className="bg-muted/40">{children}</thead>;
					},
					th({ children }) {
						return (
							<th className="border-b border-border px-3 py-1.5 text-left font-medium">
								{children}
							</th>
						);
					},
					td({ children }) {
						return <td className="border-t border-border px-3 py-1.5">{children}</td>;
					},
				}}
			>
				{cleaned}
			</ReactMarkdown>
		</div>
	);
}
