import { loadHfChangesMap } from './changesRuntime';

type ChangesMessage = {
	type: 'changes';
	year?: number;
};

self.onmessage = (event: MessageEvent<ChangesMessage>) => {
	const msg = event.data;
	if (msg.type !== 'changes') return;
	void loadHfChangesMap({ year: msg.year })
		.then((result) => {
			postMessage({ type: 'changes', ...result });
		})
		.catch((err) => {
			postMessage({ type: 'changes-error', error: err instanceof Error ? err.message : String(err) });
		});
};
