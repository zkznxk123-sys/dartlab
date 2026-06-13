export type BrowserAiAvailability = 'unsupported' | 'unavailable' | 'downloadable' | 'downloading' | 'available' | 'error';

export interface BrowserAiStatus {
	status: BrowserAiAvailability;
	raw?: string;
	reason?: string;
}

export interface BrowserAiDownloadProgress {
	loaded: number;
	total?: number;
	ratio?: number;
}

export interface BrowserLanguageModelSession {
	prompt(input: string | BrowserLanguageModelPrompt[]): Promise<string>;
	destroy?: () => void;
}

export interface BrowserLanguageModelPrompt {
	role: 'system' | 'user' | 'assistant';
	content: string;
	prefix?: boolean;
}

export interface BrowserLanguageModelApi {
	availability(options?: Record<string, unknown>): Promise<string>;
	create(options?: {
		initialPrompts?: BrowserLanguageModelPrompt[];
		signal?: AbortSignal;
		monitor?: (monitorTarget: EventTarget) => void;
	}): Promise<BrowserLanguageModelSession>;
}

export interface BrowserAiRunOpts {
	api?: BrowserLanguageModelApi | null;
	signal?: AbortSignal;
	onDownload?: (progress: BrowserAiDownloadProgress) => void;
}

export function getLanguageModelApi(): BrowserLanguageModelApi | null {
	const target = globalThis as unknown as { LanguageModel?: BrowserLanguageModelApi };
	return target.LanguageModel ?? null;
}

export async function checkBrowserAiAvailability(api: BrowserLanguageModelApi | null = getLanguageModelApi()): Promise<BrowserAiStatus> {
	if (!api) return { status: 'unsupported', reason: 'LanguageModel API not present' };
	try {
		const raw = await api.availability();
		if (raw === 'unavailable' || raw === 'downloadable' || raw === 'downloading' || raw === 'available') {
			return { status: raw, raw };
		}
		return { status: 'error', raw, reason: `Unknown availability: ${raw}` };
	} catch (error) {
		return { status: 'error', reason: error instanceof Error ? error.message : String(error) };
	}
}

export async function runBrowserAiPrompt(prompt: string, opts: BrowserAiRunOpts = {}): Promise<string> {
	const api = opts.api ?? getLanguageModelApi();
	if (!api) throw new Error('LanguageModel API is not available');

	const session = await api.create({
		signal: opts.signal,
		initialPrompts: [
			{
				role: 'system',
				content:
					'You analyze company disclosure evidence. Use only the provided evidence, cite evidence numbers, and answer in Korean when possible.'
			}
		],
		monitor(monitorTarget) {
			monitorTarget.addEventListener('downloadprogress', (event) => {
				const progress = event as Event & { loaded?: number; total?: number };
				const loaded = typeof progress.loaded === 'number' ? progress.loaded : 0;
				const total = typeof progress.total === 'number' ? progress.total : undefined;
				opts.onDownload?.({
					loaded,
					total,
					ratio: total && total > 0 ? loaded / total : undefined
				});
			});
		}
	});

	try {
		return await session.prompt(prompt);
	} finally {
		session.destroy?.();
	}
}
