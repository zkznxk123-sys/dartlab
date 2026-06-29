// VAPID 키쌍 생성 — worker.js 가 기대하는 정확한 포맷으로.
//   VAPID_PRIVATE_KEY = pkcs8 DER 의 base64url  (Worker secret. crypto.subtle.importKey('pkcs8', …, ECDSA P-256))
//   VAPID_PUBLIC_KEY  = uncompressed raw 65B(0x04‖x‖y) 의 base64url  (Worker var + GitHub VITE_VAPID_PUBLIC_KEY,
//                       브라우저 applicationServerKey · VAPID 헤더 k= 공용)
//
// 무의존(node 표준 webcrypto). 생성 후 round-trip 자체검증(재import 서명·검증 + raw 65B 확인)으로 포맷 보증.
//
// ⚠ 개인키는 비밀이다. 본인 터미널에서 직접 실행하라(`! ` 프리픽스/공유 세션에 붙여넣지 말 것 — 전사 노출):
//     node infra/workers/pushHub/scripts/genVapid.mjs
import { webcrypto as crypto } from 'node:crypto';

const b64url = (buf) =>
	Buffer.from(buf).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

const keys = await crypto.subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify']);
const pkcs8 = new Uint8Array(await crypto.subtle.exportKey('pkcs8', keys.privateKey));
const raw = new Uint8Array(await crypto.subtle.exportKey('raw', keys.publicKey)); // 65B uncompressed

// ── 자체검증: Worker 가 하는 그대로 재import 해 서명·검증 + 공개키 형식 확인 ──
if (raw.length !== 65 || raw[0] !== 0x04) {
	console.error(`FAIL: 공개키가 uncompressed 65B 가 아님 (len=${raw.length}, prefix=0x${raw[0]?.toString(16)})`);
	process.exit(1);
}
const reimported = await crypto.subtle.importKey('pkcs8', pkcs8, { name: 'ECDSA', namedCurve: 'P-256' }, false, ['sign']);
const pub = await crypto.subtle.importKey('raw', raw, { name: 'ECDSA', namedCurve: 'P-256' }, false, ['verify']);
const msg = new TextEncoder().encode('vapid-selfcheck');
const sig = await crypto.subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, reimported, msg);
const ok = await crypto.subtle.verify({ name: 'ECDSA', hash: 'SHA-256' }, pub, sig, msg);
if (!ok) {
	console.error('FAIL: round-trip 서명/검증 실패 — 포맷 불일치');
	process.exit(1);
}

console.log('✅ VAPID 키쌍 생성 + 자체검증 통과 (Worker 포맷 정합)\n');
console.log('# ── 비밀: Worker secret + GitHub Actions secret ──────────────────────────');
console.log('# (개인키 — 절대 커밋/공유 금지)');
console.log('VAPID_PRIVATE_KEY=' + b64url(pkcs8));
console.log('\n# ── 공개값: wrangler.toml [vars] + GitHub repo vars ──────────────────────');
console.log('VAPID_PUBLIC_KEY=' + b64url(raw));
console.log('\n다음: infra/workers/pushHub/DEPLOY_RUNBOOK.md 절차대로 등록하라.');
