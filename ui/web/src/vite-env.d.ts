/// <reference types="vite/client" />

declare const __DARTLAB_VERSION__: string;

declare module '*.svelte' {
	const component: unknown;
	export default component;
}
