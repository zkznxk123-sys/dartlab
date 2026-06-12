import { Loader2, Send, Sparkles, X } from 'lucide-react';
import { useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { streamAsk } from '@/features/chat/streaming/streamAsk';
import { searchCompanies } from '@/features/dashboard/api/client';

import { formatEvidenceSkillAnswer, prioritizeEvidenceSkillHits } from './evidenceSkill';
import { searchViewerIndex, type ViewerSearchHit, type ViewerSearchIndex } from './searchIndex';
import {
	deriveViewerActions,
	executeViewerAction,
	type ViewerAction,
	type ViewerActionApi,
} from './viewerActions';

interface ProviderStatusResp {
	providers: Record<string, { selected?: boolean; label?: string; model?: string }>;
}

interface ChatTurn {
	id: string;
	q: string;
	local: string;
	ai: string;
	running: boolean;
	error?: string;
	hits: ViewerSearchHit[];
	actions: Array<{ action: ViewerAction; ok: boolean; reason?: string }>;
}

interface Props {
	code: string;
	corpName: string;
	index: ViewerSearchIndex | null;
	indexing: boolean;
	onEnsureIndex: () => Promise<ViewerSearchIndex | null>;
	actionApi: ViewerActionApi;
	onClose: () => void;
}

async function selectedProviderLabel(): Promise<string | null> {
	const r = await fetch('/api/status');
	if (!r.ok) return null;
	const data: ProviderStatusResp = await r.json();
	for (const provider of Object.values(data.providers ?? {})) {
		if (provider.selected) return [provider.label, provider.model].filter(Boolean).join(' · ');
	}
	return null;
}

function makePrompt(q: string, code: string, corpName: string, hits: ViewerSearchHit[], local: string): string {
	const evidence = hits.slice(0, 5).map((h, i) => {
		return `[근거 ${i + 1}] ${h.period} · ${h.chapter} > ${h.section}${h.block ? ` > ${h.block}` : ''}\n${h.snippet}`;
	});
	return [
		`회사: ${corpName || code} (${code})`,
		'아래 [로컬 근거 스킬]과 [공시뷰어 검색 근거]를 최우선 근거로 삼아 사용자 질문에만 답하라. 근거와 질문 주제가 맞지 않으면 부족하다고 말하고, 관련 없는 재무표나 다른 주제로 확장하지 마라. 숫자/날짜 주장은 기간과 근거 번호를 함께 명시하라.',
		`질문: ${q}`,
		`[로컬 근거 스킬]\n${local}`,
		evidence.length ? `[공시뷰어 검색 근거]\n${evidence.join('\n\n')}` : '[공시뷰어 검색 근거]\n검색 결과 없음',
	].join('\n\n');
}

function navigationSearchQueries(q: string): string[] {
	const withoutCommand = q
		.replace(/\b\d{6}\b/g, ' ')
		.replace(/회사|종목|화면/g, ' ')
		.replace(/변경|이동|열어|바꿔|보여줘|해줘|해|줘|가줘|가/g, ' ')
		.replace(/[(){}\[\],.!?]/g, ' ')
		.replace(/\s+/g, ' ')
		.trim();
	const stripped = withoutCommand.replace(/(?:으로|로)$/u, '').trim();
	return [...new Set([stripped, withoutCommand].filter((term) => term.length >= 2 && term !== q))];
}

async function detectTargetCompany(q: string, currentCode: string): Promise<string | null> {
	const code = q.match(/\b\d{6}\b/)?.[0];
	if (code && code !== currentCode) return code;
	const wantsNavigation = /(회사|종목|화면).*(변경|이동|열어|바꿔)|로\s*(가|이동|변경|열어)/.test(q);
	const searchTerms = wantsNavigation ? navigationSearchQueries(q) : [];
	const hits = await searchCompanies(searchTerms[0] ?? q, 3).catch(() => []);
	if (wantsNavigation && hits.length === 1 && hits[0].stockCode !== currentCode) return hits[0].stockCode;
	for (const hit of hits) {
		if (hit.stockCode === currentCode) continue;
		if (q.includes(hit.stockCode) || (!!hit.corpName && q.includes(hit.corpName))) return hit.stockCode;
	}
	for (const term of searchTerms.slice(1)) {
		const termHits = await searchCompanies(term, 3).catch(() => []);
		if (termHits.length === 1 && termHits[0].stockCode !== currentCode) return termHits[0].stockCode;
	}
	return null;
}

export function ViewerAskDrawer({
	code,
	corpName,
	index,
	indexing,
	onEnsureIndex,
	actionApi,
	onClose,
}: Props) {
	const [question, setQuestion] = useState('');
	const [turns, setTurns] = useState<ChatTurn[]>([]);
	const [busy, setBusy] = useState(false);
	const scrollRef = useRef<HTMLDivElement | null>(null);
	const { data: providerLabel } = useQuery({
		queryKey: ['viewer-ai-provider'],
		queryFn: selectedProviderLabel,
		staleTime: 30_000,
	});

	const canAsk = question.trim().length > 0 && !busy && !indexing;
	const currentIndex = useMemo(() => index, [index]);

	function scrollBottom() {
		requestAnimationFrame(() => {
			if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
		});
	}

	async function submit() {
		const q = question.trim();
		if (!q || busy) return;
		setQuestion('');
		setBusy(true);

		const targetCode = await detectTargetCompany(q, code);
		const usableIndex = targetCode ? currentIndex : currentIndex ?? (await onEnsureIndex());
		const hits = !targetCode && usableIndex ? prioritizeEvidenceSkillHits(q, searchViewerIndex(usableIndex, q, 6).hits) : [];
		const actions = targetCode
			? ([{ kind: 'navigateCompany', code: targetCode, carryQuestion: q }] as ViewerAction[])
			: usableIndex
				? deriveViewerActions({ question: q, hits, periods: usableIndex.periods })
				: [];
		const actionResults = actions.map((action) => ({ action, ...executeViewerAction(action, actionApi) }));
		const local = targetCode ? `${targetCode} 회사로 이동해 같은 질문을 이어갑니다.` : formatEvidenceSkillAnswer(q, hits);
		const id = Date.now().toString(36);
		const turn: ChatTurn = {
			id,
			q,
			local,
			ai: '',
			running: !targetCode,
			hits,
			actions: actionResults,
		};
		setTurns((prev) => [...prev, turn]);
		scrollBottom();

		if (targetCode) {
			setBusy(false);
			return;
		}

		const control = streamAsk(
			{
				question: makePrompt(q, code, corpName, hits, local),
				history: turns.slice(-4).flatMap((t) => [
					{ role: 'user' as const, text: t.q },
					{ role: 'assistant' as const, text: t.ai || t.local },
				]),
			},
			{
				onTextDelta: (delta) => {
					setTurns((prev) => prev.map((t) => (t.id === id ? { ...t, ai: t.ai + delta } : t)));
					scrollBottom();
				},
				onError: (err) => {
					setTurns((prev) => prev.map((t) => (t.id === id ? { ...t, running: false, error: err.message } : t)));
				},
				onDone: () => {
					setTurns((prev) => prev.map((t) => (t.id === id ? { ...t, running: false } : t)));
				},
			},
		);
		await control.promise;
		setBusy(false);
	}

	return (
		<aside className="flex h-full min-h-0 w-[390px] shrink-0 flex-col border-l bg-card">
			<header className="flex h-12 shrink-0 items-center gap-2 border-b px-3">
				<img src="/avatar.png" alt="" className="size-6 rounded-full" />
				<div className="min-w-0 flex-1">
					<div className="text-sm font-semibold">공시 Q&A</div>
					<div className="truncate text-[10px] text-muted-foreground">
						{providerLabel || 'provider 미선택'} · {corpName || code}
					</div>
				</div>
				<Button type="button" variant="ghost" size="icon" className="size-8" onClick={onClose} aria-label="닫기">
					<X className="size-4" />
				</Button>
			</header>

			<div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto p-3 tiny-scroll">
				{turns.length === 0 && (
					<div className="mx-auto mt-10 max-w-[280px] text-center">
						<img src="/avatar.png" alt="" className="mx-auto size-16 rounded-full" />
						<div className="mt-4 text-sm font-medium">공시를 읽고 화면도 움직입니다</div>
						<div className="mt-2 text-xs leading-relaxed text-muted-foreground">
							질문하면 전체 공시 색인을 검색하고, 근거 셀로 이동한 뒤 선택한 provider에 깊은 답변을 요청합니다.
						</div>
						{indexing && (
							<div className="mt-4 inline-flex items-center gap-2 text-xs text-muted-foreground">
								<Loader2 className="size-3 animate-spin" />
								색인 생성 중
							</div>
						)}
					</div>
				)}
				{turns.map((turn) => (
					<div key={turn.id} className="mb-4 space-y-2">
						<div className="ml-auto max-w-[92%] rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground">
							{turn.q}
						</div>
						<div className="rounded-lg border bg-background px-3 py-2 text-sm">
							<div className="whitespace-pre-wrap leading-relaxed">{turn.local}</div>
							{turn.ai && (
								<div className="mt-3 border-t pt-3">
									<div className="mb-1 text-[10px] font-medium text-muted-foreground">provider</div>
									<div className="whitespace-pre-wrap leading-relaxed">{turn.ai}</div>
								</div>
							)}
							{turn.running && (
								<div className="mt-2 inline-flex items-center gap-2 text-xs text-muted-foreground">
									<Sparkles className="size-3" />
									provider 답변 생성 중
								</div>
							)}
							{turn.error && <div className="mt-2 text-xs text-destructive">{turn.error}</div>}
							{turn.hits.length > 0 && (
								<div className="mt-3 flex flex-wrap gap-1.5">
									{turn.hits.map((hit, i) => (
										<button
											key={`${turn.id}-${hit.sectionKey}-${hit.rowIndex}-${hit.period}`}
											type="button"
											onClick={() => executeViewerAction({ kind: 'focusEvidence', hit }, actionApi)}
											className="rounded-full border px-2 py-1 text-[10px] text-muted-foreground hover:bg-accent hover:text-foreground"
											title={`${hit.chapter} > ${hit.section} > ${hit.block}`}
										>
											근거 {i + 1} · {hit.period}
										</button>
									))}
								</div>
							)}
							{turn.actions.length > 0 && (
								<div className="mt-2 flex flex-wrap gap-1">
									{turn.actions.map((item, i) => (
										<Badge
											key={`${turn.id}-a-${i}`}
											variant={item.ok ? 'secondary' : 'outline'}
											className={cn('text-[10px]', !item.ok && 'text-muted-foreground')}
										>
											{item.action.kind}
										</Badge>
									))}
								</div>
							)}
						</div>
					</div>
				))}
			</div>

			<div className="shrink-0 border-t p-3">
				<div className="flex items-end gap-2">
					<Textarea
						value={question}
						onChange={(e) => setQuestion(e.target.value)}
						onKeyDown={(e) => {
							if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
								e.preventDefault();
								void submit();
							}
						}}
						placeholder="공시에 대해 질문..."
						className="min-h-10 resize-none text-sm"
						rows={1}
					/>
					<Button type="button" size="icon" className="size-10 shrink-0" disabled={!canAsk} onClick={() => void submit()} aria-label="질문">
						{busy ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
					</Button>
				</div>
			</div>
		</aside>
	);
}
