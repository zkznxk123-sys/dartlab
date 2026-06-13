import { useEffect, useRef, useState } from 'react';
import { mount, unmount } from 'svelte';

import { brand } from '@/lib/brand';
import { loadLocalTerminalRuntime } from './localTerminalData';

// 디자인 토큰 — @dartlab/ui-design (ui/web 은 워크스페이스 밖이라 파일경로로 소비, 01 §3.4)
import '../../../../packages/design/src/styles/v2-tokens.css';
import '../../../../packages/design/src/styles/tokens.css';

// 헤더 SNS 링크 — ui/web 자체 brand 에서 주입 (surface 가 brand 소유 안 함, 단계-4b).
const TERMINAL_LINKS = {
	repo: brand.repo,
	coffee: brand.coffee,
	youtube: brand.youtube,
	threads: brand.threads,
	instagram: brand.instagram,
};

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

		setStatus('loading');
		setMessage(`${code} 로컬 데이터 로딩 중`);
		target.replaceChildren();

		(async () => {
			const local = await loadLocalTerminalRuntime(code);
			if (cancelled) return;
			// 단계-4b: 터미널 surface 는 @dartlab/ui-surfaces 패키지 (옛 landing deep import 소멸).
			const { TerminalSurface, createEngine } = await import('@dartlab/ui-surfaces/terminal');
			if (cancelled) return;
			const eng = createEngine(local.raw);
			// runtime 은 prop 주입 — TerminalSurface 가 컨텍스트로 하위 패널에 배포 (전역 locator 철거, 4a-2).
			// hosts = null: 이 셸은 viewer 임베드 미지원 — 뷰어는 iframe(viewer port URL), 재무모달은 열화 안내 (4a-3)
			const hosts = { viewerStudio: null, financeDialog: null };
			instance = mount(TerminalSurface, {
				target,
				props: { eng, runtime: local.runtime, hosts, links: TERMINAL_LINKS, initial: code },
			}) as SvelteInstance;
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
