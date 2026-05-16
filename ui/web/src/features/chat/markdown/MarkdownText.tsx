// react-markdown + remark-gfm — ChatGPT/Claude 양식 타이포.
// + ref ID 패턴을 EvidenceChip 으로 인라인 주입 (Track 2)
// + UntrustedBlock 외부 본문 시각 구분 (Track 3)
import { Fragment, type ReactNode } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { EvidenceChip } from '../refs/EvidenceChip';
import { MermaidDiagram } from './MermaidDiagram';
import { UntrustedBlock } from './UntrustedBlock';

// CJK 인접 bold 인식 보강.
// CommonMark 우측 flanking: 닫는 `**` 앞이 punctuation (`%`, `+` 등) 일 때 뒤가
// whitespace/punctuation 이어야 닫힘 인정. 한글 letter 는 모두 실패 → raw `**` 노출.
function fixCjkBold(text: string): string {
	let out = text.replace(/(\*\*[^*\n]+?\*\*)(?=[가-힣ぁ-んァ-ヴー一-龥])/g, '$1 ');
	out = out.replace(/([가-힣ぁ-んァ-ヴー一-龥])(\*\*[^\s*])/g, '$1 $2');
	return out;
}

// dartlab ref ID 양식 — kind:value 형태. kind 는 알려진 12 종.
const REF_KINDS = [
	'doc',
	'docRef',
	'table',
	'tableRef',
	'value',
	'valueRef',
	'date',
	'dateRef',
	'source',
	'sourceRef',
	'execution',
	'executionRef',
	'decision',
	'decisionRef',
	'skill',
	'skillRef',
	'view',
	'viewRef',
	'visualRef',
	'artifact',
	'artifactRef',
	'evidence',
	'evidenceRef',
] as const;
const REF_KIND_ALT = REF_KINDS.join('|');
// 매칭: kind:Va_l-u.e:more — value 안에 : / . / - / _ 허용. 공백/세미콜론/괄호/줄바꿈에서 종료.
const REF_ID_RE = new RegExp(`\\b(${REF_KIND_ALT}):[A-Za-z0-9_.\\-:]+`, 'g');

const SENTINEL_OPEN = '⦉CHIP:';
const SENTINEL_CLOSE = '⦊';
const SENTINEL_RE = /⦉CHIP:([^⦊]+)⦊/g;

// ref ID 추출 + sentinel 로 마킹. 백틱 안 / inline code 는 보호 (간단: ` 로 감싸진 구간 skip).
function injectRefSentinels(text: string): { text: string; refOrder: string[] } {
	const refOrder: string[] = [];
	const seen = new Set<string>();

	// 백틱 코드 fence 와 인라인 코드 (`...`) 는 protect — placeholder 치환 후 복원.
	const protectedRanges: string[] = [];
	const protectKey = (i: number) => `␀PROT${i}␀`;
	let working = text;

	// fenced code blocks ```...```
	working = working.replace(/```[\s\S]*?```/g, (m) => {
		const i = protectedRanges.length;
		protectedRanges.push(m);
		return protectKey(i);
	});
	// inline code `...`
	working = working.replace(/`[^`\n]*`/g, (m) => {
		const i = protectedRanges.length;
		protectedRanges.push(m);
		return protectKey(i);
	});

	working = working.replace(REF_ID_RE, (m, _kind, _offset) => {
		// false positive 방지: URL (http://) 또는 file path (C:\) 회피
		// REF_KIND_ALT 가 http / file 포함 안 하므로 보통 안전. 한 번 더 check.
		if (m.length > 200) return m; // 비정상 긴 매치는 skip
		if (!seen.has(m)) {
			seen.add(m);
			refOrder.push(m);
		}
		return `${SENTINEL_OPEN}${m}${SENTINEL_CLOSE}`;
	});

	// 복원
	working = working.replace(/␀PROT(\d+)␀/g, (_, i) => protectedRanges[Number(i)] ?? '');

	return { text: working, refOrder };
}

// 외부 본문 마커 추출 — [EXTERNAL CONTENT START ...] ... [EXTERNAL CONTENT END]
// 추출 후 sentinel placeholder 로 치환, render 시 다시 UntrustedBlock 으로.
const EXTERNAL_RE = /\[EXTERNAL CONTENT START[^\]]*\]([\s\S]*?)\[EXTERNAL CONTENT END\]/g;
const EXT_SENTINEL_OPEN = '⦉EXT:';
const EXT_SENTINEL_CLOSE = '⦊';
const EXT_SENTINEL_RE = /⦉EXT:(\d+)⦊/g;

function injectExternalSentinels(text: string): { text: string; blocks: string[] } {
	const blocks: string[] = [];
	const out = text.replace(EXTERNAL_RE, (_, inner: string) => {
		const i = blocks.length;
		blocks.push(inner.trim());
		// 마커는 별도 줄 단위 placeholder — markdown 이 paragraph 단위로 처리하도록 앞뒤 \n.
		return `\n\n${EXT_SENTINEL_OPEN}${i}${EXT_SENTINEL_CLOSE}\n\n`;
	});
	return { text: out, blocks };
}

// 문자열 안 sentinel 을 React 노드로 split.
function splitWithSentinels(
	s: string,
	refIndex: Map<string, number>,
	extBlocks: string[],
): ReactNode {
	if (!s.includes(SENTINEL_OPEN) && !s.includes(EXT_SENTINEL_OPEN)) return s;

	const parts: ReactNode[] = [];
	let cursor = 0;
	const combined = new RegExp(`${SENTINEL_RE.source}|${EXT_SENTINEL_RE.source}`, 'g');
	let m: RegExpExecArray | null;
	while ((m = combined.exec(s)) !== null) {
		if (m.index > cursor) parts.push(s.slice(cursor, m.index));
		if (m[1]) {
			// ref chip
			const refId = m[1];
			parts.push(
				<EvidenceChip
					key={`${refId}-${m.index}`}
					refId={refId}
					index={refIndex.get(refId) ?? 0}
				/>,
			);
		} else if (m[2] !== undefined) {
			// external block
			const idx = Number(m[2]);
			parts.push(
				<UntrustedBlock key={`ext-${m.index}`} text={extBlocks[idx] ?? ''} />,
			);
		}
		cursor = combined.lastIndex;
	}
	if (cursor < s.length) parts.push(s.slice(cursor));
	return <>{parts}</>;
}

// react-markdown children walker — string 노드만 split, 다른 React 요소는 그대로.
function walkChildren(
	children: ReactNode,
	refIndex: Map<string, number>,
	extBlocks: string[],
): ReactNode {
	if (typeof children === 'string') return splitWithSentinels(children, refIndex, extBlocks);
	if (Array.isArray(children)) {
		return children.map((c, i) =>
			typeof c === 'string' ? (
				<Fragment key={i}>{splitWithSentinels(c, refIndex, extBlocks)}</Fragment>
			) : (
				c
			),
		);
	}
	return children;
}

export function MarkdownText({ text }: { text: string }) {
	// 1) external 본문 sentinel
	const { text: t1, blocks: extBlocks } = injectExternalSentinels(text);
	// 2) ref ID sentinel
	const { text: t2, refOrder } = injectRefSentinels(t1);
	// 3) CJK bold 보정
	const cleaned = fixCjkBold(t2);
	const refIndex = new Map(refOrder.map((id, i) => [id, i + 1]));

	const wrap = (children: ReactNode) => walkChildren(children, refIndex, extBlocks);

	return (
		<div className="text-sm leading-[1.7] text-foreground">
			<ReactMarkdown
				remarkPlugins={[remarkGfm]}
				components={{
					p({ children }) {
						return <p className="my-3 first:mt-0 last:mb-0">{wrap(children)}</p>;
					},
					strong({ children }) {
						return <strong className="font-semibold text-foreground">{wrap(children)}</strong>;
					},
					em({ children }) {
						return <em className="italic">{wrap(children)}</em>;
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
						return <li className="pl-1.5">{wrap(children)}</li>;
					},
					h1({ children }) {
						return <h1 className="mt-5 mb-3 text-xl font-bold tracking-tight">{wrap(children)}</h1>;
					},
					h2({ children }) {
						return (
							<h2 className="mt-5 mb-2 text-lg font-semibold tracking-tight">{wrap(children)}</h2>
						);
					},
					h3({ children }) {
						return (
							<h3 className="mt-4 mb-1.5 text-base font-semibold tracking-tight">{wrap(children)}</h3>
						);
					},
					h4({ children }) {
						return (
							<h4 className="mt-3 mb-1 text-sm font-semibold tracking-tight">{wrap(children)}</h4>
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
								{wrap(children)}
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
								{wrap(children)}
							</th>
						);
					},
					td({ children }) {
						return (
							<td className="border-t border-border px-3 py-1.5">{wrap(children)}</td>
						);
					},
				}}
			>
				{cleaned}
			</ReactMarkdown>
		</div>
	);
}
