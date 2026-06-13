// 로컬 앱 runtime 컴포지션 루트 — createLocalRuntime 인스턴스는 여기 1곳에서만 만든다.
// surface 는 window.location/$app 을 직접 모른다(02 §1) — 셸이 NavigationPort 를 goto/base 로 구현해 주입한다.
// 컴포넌트는 setDartLabRuntime/useDartLabRuntime 컨텍스트로, 라우트 load 같은 비컴포넌트 글루만 getLocalRuntime() 직접 호출.
import { goto } from '$app/navigation';
import { base } from '$app/paths';
import type {
	AskContext,
	DartLabRoute,
	DartLabRuntime,
	NavigationPort,
	ViewerOpenOptions
} from '@dartlab/ui-contracts';
import { createLocalRuntime } from '@dartlab/ui-runtime';

function viewerQuery(options?: ViewerOpenOptions): string {
	const qs = new URLSearchParams({ period: options?.period ?? 'quarterly' });
	if (options?.vs?.length) qs.set('vs', options.vs.join(','));
	if (options?.sectionKey) qs.set('section', options.sectionKey);
	return qs.toString();
}

function routeHref(route: DartLabRoute): string {
	switch (route.kind) {
		case 'terminal':
			return `${base}/terminal/${route.code}`;
		case 'viewer':
			return `${base}/analysis/${route.code}/viewer?${viewerQuery(route.options)}`;
		case 'company':
			return `${base}/analysis/${route.code}`;
		case 'chat':
			return `${base}/chat`;
		case 'ask':
			return `${base}/ask${route.context?.code ? `?code=${route.context.code}` : ''}`;
	}
}

function localNavigation(): NavigationPort {
	return {
		async toTerminal(code) {
			await goto(`${base}/terminal/${code}`);
		},
		async toViewer(code, options) {
			await goto(`${base}/analysis/${code}/viewer?${viewerQuery(options)}`);
		},
		async toCompany(code) {
			await goto(`${base}/analysis/${code}`);
		},
		async toAsk(context?: AskContext) {
			await goto(`${base}/ask${context?.code ? `?code=${context.code}` : ''}`);
		},
		href: routeHref
	};
}

let instance: DartLabRuntime | null = null;

export function getLocalRuntime(): DartLabRuntime {
	instance ??= createLocalRuntime({
		env: {
			basePath: base,
			locale: 'ko',
			marketDefault: 'KR',
			buildVersion: 'local',
			readonly: false
		},
		apiBase: '', // same-origin /api (dev 는 vite proxy 가 127.0.0.1:8400 으로)
		navigation: localNavigation()
	});
	return instance;
}
