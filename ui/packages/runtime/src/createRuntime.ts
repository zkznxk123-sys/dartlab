// kind 디스패처 — 앱 shell 진입점 1곳에서만 호출. surface 는 kind 를 모른다 (02 §1-5).
import type { DartLabRuntime, RuntimeEnvironment, RuntimeKind } from '@dartlab/ui-contracts';
import { createPublicRuntime } from './adapters/public/createPublicRuntime';
import { createLocalRuntime } from './adapters/local/createLocalRuntime';
import { createFakeRuntime } from './adapters/test/createFakeRuntime';

export interface CreateRuntimeOptions {
	kind: RuntimeKind;
	env: Omit<RuntimeEnvironment, 'kind'>;
}

export function createRuntime(options: CreateRuntimeOptions): DartLabRuntime {
	switch (options.kind) {
		case 'public':
			return createPublicRuntime({ env: options.env });
		case 'local':
			return createLocalRuntime({ env: options.env });
		case 'test':
			return createFakeRuntime({ env: { ...options.env, kind: 'test' } });
	}
}
