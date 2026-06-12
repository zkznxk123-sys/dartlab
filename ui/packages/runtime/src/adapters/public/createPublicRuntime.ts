// public adapter skeleton — 구현은 단계-4a (terminal 데이터 계층 포트화)에서 채운다.
// 책임 경계(02 §9.1): static/HF/hfProxy 접근·base path·deterministic+onDevice AI·localOnly descriptor.
// silent fallback 금지 — 미구현 호출은 명시적 오류로 실패한다 (조용히 빈 데이터를 주지 않는다).
import type { DartLabRuntime, RuntimeEnvironment } from '@dartlab/ui-contracts';

export interface PublicRuntimeOptions {
	env: Omit<RuntimeEnvironment, 'kind'>;
}

function notImplemented(port: string): never {
	throw new Error(`[public adapter] ${port} 는 단계-4a에서 구현된다 — 이 호출이 보이면 배선 순서 위반이다.`);
}

export function createPublicRuntime(options: PublicRuntimeOptions): DartLabRuntime {
	const env: RuntimeEnvironment = { ...options.env, kind: 'public' };
	return {
		env,
		get company() {
			return notImplemented('company');
		},
		get price() {
			return notImplemented('price');
		},
		get filing() {
			return notImplemented('filing');
		},
		get finance() {
			return notImplemented('finance');
		},
		get viewer() {
			return notImplemented('viewer');
		},
		get macro() {
			return notImplemented('macro');
		},
		get report() {
			return notImplemented('report');
		},
		get scan() {
			return notImplemented('scan');
		},
		get map() {
			return notImplemented('map');
		},
		get search() {
			return notImplemented('search');
		},
		get ai() {
			return notImplemented('ai');
		},
		get services() {
			return notImplemented('services');
		},
		get navigation() {
			return notImplemented('navigation');
		},
		get storage() {
			return notImplemented('storage');
		},
		telemetry: { event() {} },
		featureFlags: { isEnabled: () => false }
	};
}
