// 입력창 — auto-grow Textarea + 키보드 단축키 + Send/Stop 토글.
// Enter = 전송, Shift+Enter = 줄바꿈, ESC = 중단, Ctrl/Cmd+K = 새 대화.
import { useEffect, useRef, type KeyboardEvent } from 'react';
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
	const ref = useRef<HTMLTextAreaElement | null>(null);

	// auto-grow: scrollHeight 만큼 height. 최대 8 줄 (대략 192px).
	useEffect(() => {
		const el = ref.current;
		if (!el) return;
		el.style.height = '0px';
		const next = Math.min(el.scrollHeight, 192);
		el.style.height = `${next}px`;
	}, [value]);

	function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
		// ESC = 중단 (스트리밍 중일 때만)
		if (e.key === 'Escape' && busy) {
			e.preventDefault();
			onStop();
			return;
		}
		// Ctrl/Cmd+K = 새 대화
		if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
			e.preventDefault();
			onNewConversation?.();
			return;
		}
		// Enter (no shift) = 전송. nativeEvent.isComposing 는 IME (한글) 조합 중 false 보장.
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
				ref={ref}
				value={value}
				onChange={(e) => onChange(e.target.value)}
				onKeyDown={onKeyDown}
				placeholder={placeholder}
				rows={1}
				className="tiny-scroll min-h-[40px] max-h-[192px] flex-1 resize-none py-2.5"
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
