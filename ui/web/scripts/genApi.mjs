// OpenAPI 코드젠 — Python (FastAPI) 가 SSOT, TS 클라이언트 자동 생성.
//
// 흐름:
//   1. uv run python -X utf8 -c "..."  →  FastAPI app.openapi() dump → openapi.json
//   2. openapi-typescript openapi.json  →  src/lib/api/gen.ts
//
// 호출: `npm run gen:api`  (in ui/web)
//
// 사용:
//   import type { paths, components } from '@/lib/api/gen';
//   type Company = components['schemas']['CompanyResponse'];
//
// 참고:
//   - SSE 엔드포인트 (sse_starlette.EventSourceResponse) 는 OpenAPI 가 잘 표현 못함.
//     SSE 클라이언트는 별도 손 작성 (@/lib/api/sse.ts) + zod 이벤트 스키마.
//   - 라우터에 `response_model=` 박혀있지 않으면 응답 스키마가 unknown 으로 떨어짐.
//     점진적으로 response_model 추가 — 한 번에 X.

import { execSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname ?? path.dirname(new URL(import.meta.url).pathname), '..');
const REPO = path.resolve(ROOT, '..', '..');
const OPENAPI_JSON = path.resolve(ROOT, 'openapi.json');
const OUT_TS = path.resolve(ROOT, 'src', 'lib', 'api', 'gen.ts');

console.log('[gen:api] dump openapi.json from dartlab.server.app');
const dumpCmd = `python -X utf8 -c "from dartlab.server import app; import json; open(r'${OPENAPI_JSON}', 'w', encoding='utf-8').write(json.dumps(app.openapi(), ensure_ascii=False, indent=2))"`;
execSync(`uv run ${dumpCmd}`, { cwd: REPO, stdio: 'inherit' });

if (!existsSync(OPENAPI_JSON)) {
	console.error('[gen:api] openapi.json 생성 실패 — dartlab.server.app 진입점 확인 필요');
	process.exit(1);
}

console.log(`[gen:api] openapi-typescript → ${path.relative(ROOT, OUT_TS)}`);
execSync(`npx openapi-typescript "${OPENAPI_JSON}" -o "${OUT_TS}"`, { cwd: ROOT, stdio: 'inherit' });

console.log('[gen:api] done. tsc --noEmit 로 검증 권장.');
