// docs 라우트는 /skills 로 흡수됐다. 본 navigation 배열은 빈 배열로 유지하고,
// 호출처 (CommandPalette, search 페이지) 가 자동으로 빈 결과를 반환하게 한다.
// flattenNav 와 findPrevNext 는 호출 시그니처 호환성 위해 보존.

export interface NavItem {
	title: string;
	href: string;
	external?: boolean;
	items?: NavItem[];
}

export const navigation: NavItem[] = [];

export function flattenNav(items: NavItem[]): NavItem[] {
	const result: NavItem[] = [];
	for (const item of items) {
		if (item.items && item.items.length > 0) {
			result.push(...flattenNav(item.items));
		} else {
			result.push(item);
		}
	}
	return result;
}

export function findPrevNext(
	path: string,
	items: NavItem[] = navigation
): { prev?: NavItem; next?: NavItem } {
	const flat = flattenNav(items);
	const idx = flat.findIndex((item) => path.endsWith(item.href));
	return {
		prev: idx > 0 ? flat[idx - 1] : undefined,
		next: idx < flat.length - 1 ? flat[idx + 1] : undefined
	};
}
