import { useEffect, useRef, useState } from 'react';
import { mount, unmount } from 'svelte';

import { loadLocalTerminalRuntime } from './localTerminalData';

// 디자인 토큰 — @dartlab/ui-design (ui/web 은 워크스페이스 밖이라 파일경로로 소비, 01 §3.4)
import '../../../../packages/design/src/styles/v2-tokens.css';
import '../../../../packages/design/src/styles/tokens.css';

interface LandingTerminalSurfaceProps {
	code: string;
}

type SvelteInstance = Record<string, unknown>;

export function LandingTerminalSurface({ code }: LandingTerminalSurfaceProps) {
	const targetRef = useRef<HTMLDivElement | null>(null);
	const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
	const [message, setMessage] = useState('로컬 터미널 준비 중');

	useEffect(() => {
		const target = targetRef.current;
		if (!target) return;
		let cancelled = false;
		let instance: SvelteInstance | null = null;
		const previous = window.__DARTLAB_LOCAL_TERMINAL__;

		setStatus('loading');
		setMessage(`${code} 로컬 데이터 로딩 중`);
		target.replaceChildren();

		(async () => {
			const runtime = await loadLocalTerminalRuntime(code);
			if (cancelled) return;
			window.__DARTLAB_LOCAL_TERMINAL__ = runtime.adapter;
			const [{ default: Terminal }, { createEngine }] = await Promise.all([
				import('../../../../../landing/src/lib/terminal/Terminal.svelte'),
				import('../../../../../landing/src/lib/terminal/data/engine'),
			]);
			if (cancelled) return;
			const eng = createEngine(runtime.raw);
			instance = mount(Terminal, { target, props: { eng, initial: code } }) as SvelteInstance;
			setStatus('ready');
		})().catch((err: unknown) => {
			if (cancelled) return;
			const text = err instanceof Error ? err.message : String(err);
			setStatus('error');
			setMessage(`터미널 로드 실패: ${text}`);
		});

		return () => {
			cancelled = true;
			if (instance) void unmount(instance);
			if (previous) window.__DARTLAB_LOCAL_TERMINAL__ = previous;
			else delete window.__DARTLAB_LOCAL_TERMINAL__;
			target.replaceChildren();
		};
	}, [code]);

	return (
		<div className="relative h-svh w-svw overflow-hidden bg-[#05070b] text-[#e8eaef]">
			<div ref={targetRef} className="h-full w-full" />
			{status !== 'ready' && (
				<div className="absolute inset-0 grid place-items-center bg-[#05070b]">
					<div className="w-[min(420px,calc(100vw-32px))] border border-white/10 bg-[#0f0f10] p-5 font-mono text-xs shadow-2xl">
						<div className="mb-3 text-[10px] font-bold uppercase tracking-[0.18em] text-[#fb923c]">DartLab Terminal</div>
						<div className="text-[#a3a8b3]">{message}</div>
					</div>
				</div>
			)}
		</div>
	);
}
