// 로컬 report 포트 — 정기보고서 파생 시계열 10종. 로컬 서버는 해당 엔드포인트 미보유라 전부 null
// (= 데이터셋 미존재 정직 표기). 공개 어댑터는 HF parquet 으로 구현 — 로컬은 후속 단계에서 /api 엔드포인트 신설 시 배선.
import type { ReportPort } from '@dartlab/ui-contracts';

export function localReportPort(): ReportPort {
	const none = async () => null;
	return {
		workforce: none,
		investments: none,
		shareholderReturn: none,
		ownership: none,
		execBoard: none,
		debtProfile: none,
		capitalChanges: none,
		auditTrail: none,
		topExecPay: none,
		auditFees: none
	};
}
