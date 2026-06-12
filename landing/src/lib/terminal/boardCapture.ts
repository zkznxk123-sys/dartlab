// 터미널 보드 전체 PNG 캡처 — 3열 스크롤 영역을 아래 끝까지 펼쳐 한 장으로.
// html-to-image 는 클론에 computedStyle 을 인라인 복사하므로 잘린 스크롤 컨테이너는 잘린
// 높이 그대로 클론된다 — 실 DOM 에 .dlCapture 토글로 임시 펼침이 유일 정공법 (캡처 후 복원).
// klinecharts 캔버스(순수 2D)는 html-to-image 가 toDataURL 치환으로 보이는 그대로 박는다.
// 하단 출처 띠는 charts/snapshot.ts 와 동일 합성 — 공공누리 출처표시 의무 보존.
import { toPng } from 'html-to-image';

const EXPAND_CLASS = 'dlCapture';
const BG = '#0b0e14';
const MAX_EDGE = 16000; // Safari 캔버스 면적 한계 방어 — 초과 시 pixelRatio 강등

export async function downloadBoardSnapshot(
	board: HTMLElement,
	opts: { fileTag: string; srcLine: string }
): Promise<void> {
	const root = board.closest('.dlTerm') as HTMLElement | null;
	root?.classList.add(EXPAND_CLASS);
	try {
		await new Promise(requestAnimationFrame); // 펼침 리플로 1프레임 대기
		const w = board.scrollWidth;
		const h = board.scrollHeight;
		let ratio = Math.min(window.devicePixelRatio || 1, 2);
		if (Math.max(w, h) * ratio > MAX_EDGE) ratio = Math.max(1, MAX_EDGE / Math.max(w, h));
		const url = await toPng(board, {
			width: w,
			height: h,
			pixelRatio: ratio,
			backgroundColor: BG,
			cacheBust: true
		});
		const img = new Image();
		await new Promise<void>((resolve, reject) => {
			img.onload = () => resolve();
			img.onerror = () => reject(new Error('board snapshot image load'));
			img.src = url;
		});
		const pad = Math.round(26 * ratio);
		const cv = document.createElement('canvas');
		cv.width = img.width;
		cv.height = img.height + pad;
		const ctx = cv.getContext('2d');
		if (!ctx) return;
		ctx.fillStyle = BG;
		ctx.fillRect(0, 0, cv.width, cv.height);
		ctx.drawImage(img, 0, 0);
		ctx.fillStyle = '#7b828f';
		ctx.font = `${Math.round(11 * ratio)}px ui-monospace, monospace`;
		ctx.textBaseline = 'middle';
		ctx.fillText(opts.srcLine, Math.round(8 * ratio), img.height + pad / 2);
		const blob: Blob | null = await new Promise((resolve) => cv.toBlob(resolve, 'image/png'));
		if (!blob) return;
		const a = document.createElement('a');
		a.href = URL.createObjectURL(blob);
		a.download = `dartlab_${opts.fileTag}.png`;
		a.click();
		setTimeout(() => URL.revokeObjectURL(a.href), 4000);
	} finally {
		root?.classList.remove(EXPAND_CLASS);
	}
}
