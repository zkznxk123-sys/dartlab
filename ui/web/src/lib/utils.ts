import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

// shadcn/ui 표준 className 합성 헬퍼.
export function cn(...inputs: ClassValue[]): string {
	return twMerge(clsx(inputs));
}
