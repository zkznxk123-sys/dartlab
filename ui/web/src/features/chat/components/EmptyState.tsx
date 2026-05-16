// 대화 시작 전 빈 상태 — 헤드라인 + 추천 칩 + Composer 가운데 정렬.
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Composer } from './Composer';

const suggestions = [
	'삼성전자 005930 최근 5년 매출과 영업이익 추이',
	'코스피에서 ROE 높고 부채비율 낮은 종목 찾아줘',
	'테슬라 최근 분기 실적 정리',
	'한국 매크로 지표 — 환율 · 금리 · CPI',
];

interface EmptyStateProps {
	input: string;
	setInput: (v: string) => void;
	onSend: () => void;
	onStop: () => void;
	onNewConversation?: () => void;
	busy: boolean;
}

export function EmptyState({ input, setInput, onSend, onStop, onNewConversation, busy }: EmptyStateProps) {
	return (
		<div className="flex flex-1 flex-col items-center justify-center px-4 py-6">
			<div className="w-full max-w-2xl space-y-6">
				<div className="flex flex-col items-center space-y-3 text-center">
					<Avatar className="size-12">
						<AvatarImage src="/avatar.png" alt="DartLab" />
						<AvatarFallback>DL</AvatarFallback>
					</Avatar>
					<h2 className="text-2xl font-semibold tracking-tight">무엇을 도와드릴까요?</h2>
					<p className="text-sm text-muted-foreground">
						종목코드 · 회사명 · 거시 지표 무엇이든 물어보세요.
					</p>
				</div>
				<Composer
					value={input}
					onChange={setInput}
					onSend={onSend}
					onStop={onStop}
					onNewConversation={onNewConversation}
					busy={busy}
					autoFocus
				/>
				<div className="flex flex-wrap justify-center gap-2 pt-2">
					{suggestions.map((s) => (
						<Button
							key={s}
							variant="outline"
							size="sm"
							className="text-xs font-normal text-muted-foreground"
							onClick={() => setInput(s)}
						>
							{s}
						</Button>
					))}
				</div>
			</div>
		</div>
	);
}
