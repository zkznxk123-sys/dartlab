// 입력창 — auto-grow Textarea + 키보드 단축키.
// 높이 조절은 CSS field-sizing-content (Textarea base) 에 위임. 별도 JS 없음 → empty 시 scrollbar 안 보임.
// Enter = 전송, Shift+Enter = 줄바꿈, ESC = 중단, Ctrl/Cmd+K = 새 대화.
import type { KeyboardEvent } from 'react';
import { ArrowUp, Square } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

interface ComposerProps {
	value: string;
	onChange: (v: string) => void;
	onSend: () => void;
	onStop: () => void;
	onNewConversation?: () => void;
	busy: boolean;
	autoFocus?: boolean;
	placeholder?: string;
}

export function Composer({
	value,
	onChange,
	onSend,
	onStop,
	onNewConversation,
	busy,
	autoFocus,
	placeholder = '질문을 입력하세요…  (Enter 전송 · Shift+Enter 줄바꿈)',
}: ComposerProps) {
	function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
		if (e.key === 'Escape' && busy) {
			e.preventDefault();
			onStop();
			return;
		}
		if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
			e.preventDefault();
			onNewConversation?.();
			return;
		}
		if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
			e.preventDefault();
			if (!busy && value.trim()) onSend();
		}
	}

	return (
		<form
			className="flex w-full items-end gap-2"
			onSubmit={(e) => {
				e.preventDefault();
				if (!busy && value.trim()) onSend();
			}}
		>
			<Textarea
				value={value}
				onChange={(e) => onChange(e.target.value)}
				onKeyDown={onKeyDown}
				placeholder={placeholder}
				rows={1}
				className="min-h-[40px] max-h-[192px] flex-1 resize-none py-2.5 overflow-y-auto [scrollbar-width:thin]"
				autoFocus={autoFocus}
			/>
			{busy ? (
				<Button type="button" variant="outline" size="icon" onClick={onStop} aria-label="중단 (ESC)">
					<Square />
				</Button>
			) : (
				<Button type="submit" size="icon" disabled={!value.trim()} aria-label="전송 (Enter)">
					<ArrowUp />
				</Button>
			)}
		</form>
	);
}
