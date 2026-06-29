// 워커/파일별 1회 — migrations/ DDL 적용(테이블 생성). 행 리셋은 각 테스트 beforeEach 담당.
import { applyD1Migrations, env } from 'cloudflare:test';

await applyD1Migrations(env.PUSHHUB_DB, env.TEST_MIGRATIONS);
