// 스크롤이 하단에서 떨어졌을 때 우하단 floating 버튼.
// 부모가 scroll container 를 ref 로 넘겨주면 본 컴포넌트가 scroll 위치 관찰 + 클릭 시 하단으로.
import { useEffect, useState } from 'react';
import { ArrowDown } from 'lucide-react';

import { Button } from '@/components/ui/button';

interface Props {
	scrollContainer: HTMLElement | null;
	threshold?: number; // px from bottom 안에 있으면 hidden
}

export function ScrollToBottomButton({ scrollContainer, threshold = 80 }: Props) {
	const [visible, setVisible] = useState(false);

	useEffect(() => {
		const el = scrollContainer;
		if (!el) return;
		const check = () => {
			const dist = el.scrollHeight - el.scrollTop - el.clientHeight;
			setVisible(dist > threshold);
		};
		check();
		el.addEventListener('scroll', check, { passive: true });
		const ro = new ResizeObserver(check);
		ro.observe(el);
		return () => {
			el.removeEventListener('scroll', check);
			ro.disconnect();
		};
	}, [scrollContainer, threshold]);

	function scrollDown() {
		const el = scrollContainer;
		if (!el) return;
		el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
	}

	if (!visible) return null;
	return (
		<Button
			variant="outline"
			size="icon"
			onClick={scrollDown}
			className="absolute bottom-4 right-4 z-10 size-9 rounded-full shadow-md"
			aria-label="최신으로 스크롤"
		>
			<ArrowDown className="size-4" />
		</Button>
	);
}
