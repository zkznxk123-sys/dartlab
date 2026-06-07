// 브라우저 온디바이스 내레이션 (실험) — WebLLM(@mlc-ai/web-llm) Qwen3-0.6B.
//
// ★결정론 신호가 SSOT: 모델은 *이미 계산된* 분석 결과 텍스트를 한국어로 다듬기만 한다. 숫자·계정명·기간
// 재도출/변경/새 사실 생성 금지(시스템 프롬프트 + 결정론 표시가 진실원본). Chrome Prompt API(Gemini Nano)는
// 한국어 미지원이라 채택 안 함 → WebLLM 으로. WebGPU 없으면 비활성(결정론 내레이션만). 모델은 HF CDN 자동
// 다운로드 + 브라우저 캐시(사용자 관리 0, 외부 전송 0). import 는 호출 시 dynamic — 초기 번들 비포함.

import type { InitProgressReport, MLCEngineInterface } from '@mlc-ai/web-llm';

const MODEL_ID = 'Qwen3-0.6B-q4f16_1-MLC';

export interface WebLlmProgress {
	text: string;
	progress: number; // 0..1
}

export function webgpuAvailable(): boolean {
	return typeof navigator !== 'undefined' && 'gpu' in navigator;
}

let enginePromise: Promise<MLCEngineInterface> | null = null;

async function ensureEngine(onProgress?: (p: WebLlmProgress) => void): Promise<MLCEngineInterface> {
	if (!webgpuAvailable()) throw new Error('WebGPU 미지원 브라우저');
	if (!enginePromise) {
		enginePromise = (async () => {
			const webllm = await import('@mlc-ai/web-llm');
			const worker = new Worker(new URL('./webllmWorker.ts', import.meta.url), { type: 'module' });
			return webllm.CreateWebWorkerMLCEngine(worker, MODEL_ID, {
				initProgressCallback: (r: InitProgressReport) => onProgress?.({ text: r.text, progress: r.progress })
			});
		})().catch((e) => {
			enginePromise = null; // 실패 시 재시도 허용
			throw e;
		});
	}
	return enginePromise;
}

// 결정론 분석 결과 텍스트를 받아 한국어로 다듬기만. 숫자/사실 불변(시스템 프롬프트로 강제).
export async function narrateSignals(deterministicText: string, opts: { onProgress?: (p: WebLlmProgress) => void } = {}): Promise<string> {
	const engine = await ensureEngine(opts.onProgress);
	const reply = await engine.chat.completions.create({
		messages: [
			{
				role: 'system',
				content:
					'너는 재무공시 분석 문장 편집기다. 아래 [결정론 분석 결과]를 한국어로 자연스럽게 2~3문장으로 다듬어라. ' +
					'숫자·계정명·기간·비율은 절대 바꾸지 말고 그대로 쓴다. 새 사실·추측·해석을 추가하지 않는다. 결과 문장만 출력한다.'
			},
			{ role: 'user', content: `[결정론 분석 결과]\n${deterministicText}` }
		],
		temperature: 0.2,
		max_tokens: 220
	});
	return reply.choices[0]?.message?.content?.trim() ?? '';
}
