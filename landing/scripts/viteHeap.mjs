// vite CLI를 워크스페이스 호이스팅과 무관하게 기동하는 heap 래퍼.
// 옛 build 스크립트의 `./node_modules/vite/bin/vite.js` 고정 경로는 루트 워크스페이스
// 전환(호이스팅) 후 존재하지 않는다 — exports 맵을 우회해 require.resolve로 실위치를 찾는다.
// 사용: node --max-old-space-size=8192 scripts/viteHeap.mjs build
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { dirname, join } from 'node:path';

const require = createRequire(import.meta.url);
const vitePkg = require.resolve('vite/package.json');
await import(pathToFileURL(join(dirname(vitePkg), 'bin', 'vite.js')).href);
