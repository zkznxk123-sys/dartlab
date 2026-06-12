// 오류 계약 — service/port 실패를 정상 데이터처럼 렌더하지 않기 위한 공통 형태.

export type RuntimeErrorCode = 'unavailable' | 'network' | 'notFound' | 'timeout' | 'forbidden' | 'internal';

export interface RuntimeErrorShape {
	code: RuntimeErrorCode;
	message: string;
	cause?: unknown;
}
