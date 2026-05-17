// 외부 본문 시각 구분 — `[EXTERNAL CONTENT START ...]\n{text}\n[EXTERNAL CONTENT END]` 블록.
// 회색 dim bg + 좌측 🌐 + 상단 배지 "외부 본문 · 1 차 출처 검증 필요". 내부는 markdown 재렌더 (단, 중첩 untrusted 방지 위해 raw text 표시).
import { Globe } from 'lucide-react';

interface Props {
	text: string;
}

export function UntrustedBlock({ text }: Props) {
	return (
		<div className="my-3 rounded-md border border-dashed border-border bg-muted/30 p-3">
			<div className="mb-2 flex items-center gap-1.5">
				<Globe className="size-3 text-muted-foreground" />
				<span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
					외부 본문 · 1 차 출처 검증 필요
				</span>
			</div>
			<div className="whitespace-pre-wrap break-words text-sm leading-relaxed text-muted-foreground">
				{text}
			</div>
		</div>
	);
}
