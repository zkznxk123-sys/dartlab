import { base } from '$app/paths';
import { INITIAL_PUBLIC_PAYLOAD } from './model';
import type { SiteSignalsPublicPayload } from './types';

export async function loadSiteSignals(): Promise<SiteSignalsPublicPayload> {
	try {
		const response = await fetch(`${base}/site-signals/rolling.json`);
		if (!response.ok) return INITIAL_PUBLIC_PAYLOAD;
		const payload = (await response.json()) as Partial<SiteSignalsPublicPayload>;
		if (payload.version !== 1) return INITIAL_PUBLIC_PAYLOAD;
		return {
			...INITIAL_PUBLIC_PAYLOAD,
			...payload,
			windows: payload.windows?.length ? payload.windows : INITIAL_PUBLIC_PAYLOAD.windows,
			summaries: payload.summaries ?? INITIAL_PUBLIC_PAYLOAD.summaries
		};
	} catch {
		return INITIAL_PUBLIC_PAYLOAD;
	}
}
