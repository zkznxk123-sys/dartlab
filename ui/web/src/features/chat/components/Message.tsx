// 메시지 한 줄 — ChatGPT 최신 양식.
// 사용자 = 우측 정렬, 둥근 muted 박스, 폭 75%. 아바타 없음.
// AI    = 좌측 정렬, 전체 폭, 배경 없음. hover 시 MessageActions (복사 · 재생성).
// parts[] 는 groupParts 로 [text | loop] 시퀀스로 묶어 렌더.
import { RotateCcw } from 'lucide-react';

import type { Message } from '@/features/chat/store/chat';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { MarkdownText } from '../markdown/MarkdownText';
import { groupParts, WorkLoop } from '../workloop/WorkLoop';
import { MessageActions } from './MessageActions';

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

	return (
		<div className="group px-4 py-3 space-y-2">
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
			{groups.map((g, i) =>
				g.kind === 'text' ? (
					<MarkdownText key={i} text={g.part.text} />
				) : (
					<WorkLoop key={i} parts={g.parts} />
				),
			)}
			{showThinking && (
				<div className="space-y-2 py-1">
					<Skeleton className="h-3 w-4/5" />
					<Skeleton className="h-3 w-3/5" />
					<Skeleton className="h-3 w-2/3" />
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
