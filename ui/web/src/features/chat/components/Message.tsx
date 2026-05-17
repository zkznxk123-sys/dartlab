// 메시지 한 줄 — ChatGPT 최신 양식.
// 사용자 = 우측 정렬, 둥근 muted 박스, 폭 75%. 아바타 없음.
// AI    = 좌측 정렬, 전체 폭, 배경 없음. hover 시 MessageActions (복사 · 재생성).
// parts[] 는 groupParts 로 [text | loop] 시퀀스로 묶어 렌더.
import { Loader2, RotateCcw } from 'lucide-react';

import type { Message, ToolPart } from '@/features/chat/store/chat';
import { Button } from '@/components/ui/button';
import { MarkdownText } from '../markdown/MarkdownText';
import { DcrPopover, type DcrBadgeData } from '../refs/DcrPopover';
import { IndustryChip, type IndustryBadgeData } from '../refs/IndustryChip';
import { groupParts, WorkLoop } from '../workloop/WorkLoop';
import { MessageActions } from './MessageActions';

interface CompanyShowData {
	dcrBadge?: DcrBadgeData;
	industryBadge?: IndustryBadgeData;
}

function latestToolResultData(message: Message): CompanyShowData | null {
	for (let i = message.parts.length - 1; i >= 0; i--) {
		const p = message.parts[i];
		if (!p || p.type !== 'tool') continue;
		const t = p as ToolPart;
		if (t.status !== 'done') continue;
		const r = t.result as { data?: CompanyShowData } | undefined;
		if (r?.data?.dcrBadge || r?.data?.industryBadge) return r.data;
	}
	return null;
}

interface Props {
	message: Message;
	onRegenerate?: () => void;
	canRegenerate?: boolean;
}

export function ChatMessage({ message, onRegenerate, canRegenerate }: Props) {
	const isUser = message.role === 'user';
	const hasParts = message.parts.length > 0;
	const groups = hasParts ? groupParts(message.parts) : [];
	const showThinking = message.loading && !hasParts;

	if (isUser) {
		const text = message.parts
			.map((p) => (p.type === 'text' ? p.text : ''))
			.join('')
			.trim();
		return (
			<div className="flex justify-end px-4 py-2">
				<div className="max-w-[75%] rounded-2xl bg-muted/60 px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap break-words">
					{text}
				</div>
			</div>
		);
	}

	// 마지막 그룹이 loop 면 "답변 작성 전" — 그 loop 는 stillWorking, 별도 spinner 노출.
	const lastGroup = groups[groups.length - 1];
	const showComposingSpinner = !!message.loading && (!lastGroup || lastGroup.kind === 'loop');
	const badgeData = latestToolResultData(message);
	const dcrBadge = badgeData?.dcrBadge ?? null;
	const industryBadge = badgeData?.industryBadge ?? null;

	return (
		<div className="group px-4 py-3 space-y-2">
			{(dcrBadge || industryBadge) && (
				<div className="flex flex-wrap items-center gap-2 pb-0.5">
					{dcrBadge && <DcrPopover badge={dcrBadge} />}
					{industryBadge && <IndustryChip badge={industryBadge} />}
				</div>
			)}
			{message.error && (
				<div className="flex items-center gap-2 text-sm text-destructive">
					<span>⚠ {message.error}</span>
					{onRegenerate && canRegenerate && (
						<Button
							size="sm"
							variant="ghost"
							onClick={onRegenerate}
							className="h-6 gap-1 px-2 text-xs"
						>
							<RotateCcw className="size-3" />
							재시도
						</Button>
					)}
				</div>
			)}
			{groups.map((g, i) => {
				if (g.kind === 'text') return <MarkdownText key={i} text={g.part.text} />;
				const hasTextAfter = groups.slice(i + 1).some((x) => x.kind === 'text');
				const stillWorking = !!message.loading && !hasTextAfter;
				return <WorkLoop key={i} parts={g.parts} stillWorking={stillWorking} />;
			})}
			{showThinking && (
				<div className="flex items-center gap-2 py-1 text-sm text-muted-foreground">
					<Loader2 className="size-3.5 animate-spin" />
					<span>분석 준비 중</span>
				</div>
			)}
			{!showThinking && showComposingSpinner && (
				<div className="flex items-center gap-2 py-1 text-sm text-muted-foreground">
					<Loader2 className="size-3.5 animate-spin" />
					<span>답변 작성 중</span>
				</div>
			)}
			{!message.loading && (hasParts || message.error) && (
				<MessageActions
					message={message}
					onRegenerate={onRegenerate}
					canRegenerate={canRegenerate}
				/>
			)}
		</div>
	);
}
