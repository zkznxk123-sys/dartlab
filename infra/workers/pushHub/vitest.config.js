// vitest-pool-workers 0.16.x config — cloudflareTest 플러그인 방식(0.16 에서 defineWorkersConfig/./config 폐지).
// wrangler.toml 에서 [[d1_databases]] PUSHHUB_DB·[vars] 자동 발견. secret(PUSHHUB_SEND_TOKEN)·migrations 는
// miniflare.bindings 로 주입. 스키마는 migrations/ + setupFiles 의 applyD1Migrations 로 적용(멀티라인 exec 금지).
import { cloudflareTest, readD1Migrations } from '@cloudflare/vitest-pool-workers';
import { defineConfig } from 'vitest/config';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const dir = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig(async () => {
	const migrations = await readD1Migrations(path.join(dir, 'migrations'));
	return {
		plugins: [
			cloudflareTest({
				wrangler: { configPath: './wrangler.toml' },
				miniflare: {
					bindings: {
						PUSHHUB_SEND_TOKEN: 'test-send-token', // 테스트 전용 토큰(send.test 와 일치)
						TEST_MIGRATIONS: migrations // setupFiles 가 applyD1Migrations 로 적용
					}
				}
			})
		],
		test: {
			setupFiles: ['./test/applyMigrations.js']
		}
	};
});
