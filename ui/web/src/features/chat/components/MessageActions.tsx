// AI 메시지 hover 시 우하단 액션 — Copy / Regenerate.
// 메시지 본문 텍스트만 추출해서 클립보드. parts[] 중 text 부분만 join.
import { useState } from 'react';
import { Check, Copy, RotateCcw } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import type { Message } from '@/features/chat/store/chat';

function messageToText(m: Message): string {
	return m.parts
		.map((p) => (p.type === 'text' ? p.text : ''))
		.join('')
		.trim();
}

interface Props {
	message: Message;
	onRegenerate?: () => void;
	canRegenerate?: boolean;
}

export function MessageActions({ message, onRegenerate, canRegenerate }: Props) {
	const [copied, setCopied] = useState(false);

	async function copy() {
		const text = messageToText(message);
		if (!text) return;
		try {
			await navigator.clipboard.writeText(text);
			setCopied(true);
			setTimeout(() => setCopied(false), 1500);
		} catch {
			/* clipboard 미지원 */
		}
	}

	return (
		<div className="mt-1 flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
			<Tooltip>
				<TooltipTrigger asChild>
					<Button variant="ghost" size="icon" className="size-7" onClick={copy} aria-label="복사">
						{copied ? <Check className="size-3.5 text-[#ea4647]" /> : <Copy className="size-3.5" />}
					</Button>
				</TooltipTrigger>
				<TooltipContent>{copied ? '복사됨' : '복사'}</TooltipContent>
			</Tooltip>
			{canRegenerate && onRegenerate && (
				<Tooltip>
					<TooltipTrigger asChild>
						<Button
							variant="ghost"
							size="icon"
							className="size-7"
							onClick={onRegenerate}
							aria-label="재생성"
						>
							<RotateCcw className="size-3.5" />
						</Button>
					</TooltipTrigger>
					<TooltipContent>재생성</TooltipContent>
				</Tooltip>
			)}
		</div>
	);
}
