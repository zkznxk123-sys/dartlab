// HF 데이터셋 resolve base URL 의 단일 SSOT.
//
// 여러 로더(hfRange·dartlabData·duckdb·scan worker 등)가 각자 복제하던 base URL + VITE_DARTLAB_HF_RESOLVE
// override 로직을 여기로 통합한다. 데이터 호출 경로를 한곳에서 관리(SSOT) — 데이터 워크벤치 Phase 0.
//
// 전환(가역, 한 줄): 빌드 env 에 VITE_DARTLAB_HF_RESOLVE 지정 시 전체 로더가 그 base 로 전환.
//   예) Cloudflare hfProxy 워커: VITE_DARTLAB_HF_RESOLVE=https://dartlab-hf-proxy.<sub>.workers.dev/hf
//       (infra/workers/hfProxy — 콜드 HF CDN 403 흡수 + range 보존). 비우면 HF 직결로 즉시 롤백.
const DEFAULT_HF_RESOLVE = 'https://huggingface.co/datasets/eddmpython/dartlab-data/resolve/main';

export const HF_RESOLVE = (import.meta.env.VITE_DARTLAB_HF_RESOLVE ?? DEFAULT_HF_RESOLVE).replace(/\/+$/, '');

/** 데이터셋 상대 경로 → 절대 resolve URL. (선행 슬래시 정규화) */
export const hfUrl = (path: string): string => `${HF_RESOLVE}/${String(path).replace(/^\/+/, '')}`;
