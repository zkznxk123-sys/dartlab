// 공시 Q&A 질문 수집 Cloudflare Worker — opt-in 사용자 질문을 HF raw 샤드에 적재.
//
// 정적사이트(GitHub Pages)는 런타임 쓰기가 불가해 수신단이 필요하다. 이 Worker 가 유일한 백엔드.
// 설계: PII 0(질문 본문 + 예측 intent 만, 회사코드/식별자 미수집). 질문당 *별도 파일* 로 적재해
// read-modify-write 레이스 0. HF 토큰은 Worker secret 에만(클라이언트 노출 0).
// 재학습 루프: raw → reviewRawQueries.py 가 미라우팅 군집을 운영자 review Issue 로 → curatedQuestions 승격 → 파이프라인 재빌드.
//
// 배포: 같은 폴더 README.md 참조 (wrangler + HF_TOKEN secret, 1회).

import { uploadFile } from '@huggingface/hub';

const REPO = { type: 'dataset', name: 'eddmpython/dartlab-data' };
const MAX_LEN = 200;
const MIN_LEN = 2;

export default {
	async fetch(req, env) {
		const cors = {
			'Access-Control-Allow-Origin': env.ALLOW_ORIGIN || '*', // 배포 시 실제 사이트 origin 으로 좁히길 권장
			'Access-Control-Allow-Methods': 'POST, OPTIONS',
			'Access-Control-Allow-Headers': 'Content-Type'
		};
		if (req.method === 'OPTIONS') return new Response(null, { headers: cors });
		if (req.method !== 'POST') return new Response('method not allowed', { status: 405, headers: cors });

		let body;
		try {
			body = await req.json();
		} catch {
			return new Response('bad json', { status: 400, headers: cors });
		}
		const q = String(body?.q ?? '').trim();
		if (q.length < MIN_LEN || q.length > MAX_LEN) return new Response('invalid length', { status: 422, headers: cors });
		// 한글/영문/숫자 비율이 너무 낮으면(=노이즈·스팸) 거절 (1차 청소; 본청소는 reviewRawQueries.py)
		const meaningful = (q.match(/[가-힣A-Za-z0-9]/g) || []).length;
		if (meaningful < q.length * 0.5) return new Response('noise', { status: 422, headers: cors });

		const intent = String(body?.intent ?? '').slice(0, 40);
		const rec = JSON.stringify({ q, intent, ts: new Date().toISOString() });
		const date = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
		const path = `dart/queries/raw/${date}/${crypto.randomUUID()}.json`; // 질문당 1파일 = append 레이스 0

		try {
			await uploadFile({
				repo: REPO,
				accessToken: env.HF_TOKEN,
				file: { path, content: new Blob([rec], { type: 'application/json' }) },
				commitTitle: 'collect: anonymous viewer question'
			});
		} catch {
			return new Response('upstream error', { status: 502, headers: cors });
		}
		return new Response('ok', { headers: cors });
	}
};
