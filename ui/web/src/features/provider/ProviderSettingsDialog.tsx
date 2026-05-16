// Provider 설정 모달 — backup 양식.
// - OAuth provider (auth=oauth): "로그인" 클릭 → /api/oauth/authorize → 브라우저 새 탭 + 상태 폴링
// - API key provider (auth=api_key): 입력 필드 + "저장" → POST /api/ai/profile/secrets
// - 카드 클릭으로 provider 전환 (available 이면)
import { useState, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, Check, ExternalLink, Loader2, LogIn, LogOut, Settings } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
	DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

interface ProviderInfo {
	available: boolean;
	model?: string;
	label?: string;
	desc?: string;
	selected?: boolean;
	auth?: 'oauth' | 'api_key' | string;
	envKey?: string;
	signupUrl?: string;
	secretConfigured?: boolean;
}
interface StatusResp {
	providers: Record<string, ProviderInfo>;
}

async function fetchStatus(): Promise<StatusResp> {
	const r = await fetch('/api/status');
	if (!r.ok) throw new Error(`HTTP ${r.status}`);
	return r.json();
}

async function selectProvider(provider: string): Promise<void> {
	const r = await fetch('/api/ai/profile', {
		method: 'PUT',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ provider }),
	});
	if (!r.ok) throw new Error(`HTTP ${r.status}`);
}

async function setApiKey(provider: string, apiKey: string): Promise<void> {
	const r = await fetch('/api/ai/profile/secrets', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ provider, apiKey }),
	});
	if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text().catch(() => '')}`);
}

async function startOauth(): Promise<{ authUrl: string }> {
	const r = await fetch('/api/oauth/authorize');
	if (!r.ok) throw new Error(`HTTP ${r.status}`);
	return r.json();
}

async function pollOauthStatus(): Promise<{ done: boolean; error?: string }> {
	const r = await fetch('/api/oauth/status');
	if (!r.ok) throw new Error(`HTTP ${r.status}`);
	return r.json();
}

async function oauthLogout(): Promise<void> {
	const r = await fetch('/api/oauth/logout', { method: 'POST' });
	if (!r.ok) throw new Error(`HTTP ${r.status}`);
}

interface Props {
	trigger?: ReactNode;
}

export function ProviderSettingsDialog({ trigger }: Props) {
	const [open, setOpen] = useState(false);
	const qc = useQueryClient();
	const { data, isLoading, refetch } = useQuery({
		queryKey: ['provider-status'],
		queryFn: fetchStatus,
		staleTime: 10_000,
		enabled: open,
	});

	const entries = Object.entries(data?.providers ?? {});

	return (
		<Dialog open={open} onOpenChange={setOpen}>
			<DialogTrigger asChild>
				{trigger ?? (
					<Button variant="ghost" size="icon" aria-label="AI Provider 설정">
						<Settings />
					</Button>
				)}
			</DialogTrigger>
			<DialogContent className="sm:max-w-lg">
				<DialogHeader>
					<DialogTitle>AI Provider</DialogTitle>
					<DialogDescription>분석에 사용할 AI 공급자를 선택하고 로그인하세요.</DialogDescription>
				</DialogHeader>
				<ScrollArea className="max-h-[60vh]">
					<div className="flex flex-col gap-2 pr-2">
						{isLoading ? (
							<div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
								<Loader2 className="size-4 animate-spin" />
								<span>확인 중…</span>
							</div>
						) : entries.length === 0 ? (
							<div className="py-8 text-center text-sm text-muted-foreground">
								가용 provider 없음
							</div>
						) : (
							entries.map(([key, p]) => (
								<ProviderCard
									key={key}
									providerKey={key}
									info={p}
									onChanged={() => {
										qc.invalidateQueries({ queryKey: ['provider-status'] });
										refetch();
									}}
								/>
							))
						)}
					</div>
				</ScrollArea>
			</DialogContent>
		</Dialog>
	);
}

function ProviderCard({
	providerKey,
	info,
	onChanged,
}: {
	providerKey: string;
	info: ProviderInfo;
	onChanged: () => void;
}) {
	const [keyInput, setKeyInput] = useState('');
	const [oauthBusy, setOauthBusy] = useState(false);

	const selectM = useMutation({
		mutationFn: () => selectProvider(providerKey),
		onSuccess: onChanged,
	});
	const apiKeyM = useMutation({
		mutationFn: () => setApiKey(providerKey, keyInput.trim()),
		onSuccess: () => {
			setKeyInput('');
			onChanged();
		},
	});
	const oauthLogoutM = useMutation({
		mutationFn: oauthLogout,
		onSuccess: onChanged,
	});

	async function handleOauthLogin() {
		setOauthBusy(true);
		try {
			const { authUrl } = await startOauth();
			window.open(authUrl, '_blank', 'noopener,noreferrer');
			// 폴링 — 최대 5 분
			for (let i = 0; i < 150; i++) {
				await new Promise((r) => setTimeout(r, 2000));
				try {
					const s = await pollOauthStatus();
					if (s.done) {
						if (s.error) throw new Error(s.error);
						break;
					}
				} catch {
					/* 다음 폴링까지 */
				}
			}
			onChanged();
		} finally {
			setOauthBusy(false);
		}
	}

	const statusBadge = info.selected
		? 'SELECTED'
		: info.available
			? 'AVAILABLE'
			: 'NEEDS SETUP';
	const badgeColor = info.selected
		? 'text-emerald-500'
		: info.available
			? 'text-muted-foreground'
			: 'text-muted-foreground';

	return (
		<div
			className={
				'rounded-md border p-3 transition-colors ' +
				(info.selected ? 'border-primary/40 bg-accent/40' : 'border-border')
			}
		>
			<div className="flex items-center gap-2">
				<span className="text-sm font-medium">{info.label || providerKey}</span>
				<span className={`ml-auto flex items-center gap-1 text-[10px] font-mono ${badgeColor}`}>
					{info.selected ? (
						<Check className="size-3" />
					) : !info.available ? (
						<AlertCircle className="size-3" />
					) : null}
					{statusBadge}
				</span>
			</div>
			{info.desc && (
				<div className="mt-0.5 text-xs text-muted-foreground">{info.desc}</div>
			)}
			{info.model && (
				<div className="mt-0.5 font-mono text-[11px] text-muted-foreground">{info.model}</div>
			)}

			{/* Actions */}
			<div className="mt-2 flex flex-wrap items-center gap-2">
						{/* OAuth provider */}
						{info.auth === 'oauth' &&
							(info.available ? (
								<>
									{!info.selected && (
										<Button
											size="sm"
											variant="outline"
											onClick={() => selectM.mutate()}
											disabled={selectM.isPending}
										>
											사용
										</Button>
									)}
									<Button
										size="sm"
										variant="ghost"
										onClick={() => oauthLogoutM.mutate()}
										disabled={oauthLogoutM.isPending}
									>
										<LogOut />
										로그아웃
									</Button>
								</>
							) : (
								<Button size="sm" onClick={handleOauthLogin} disabled={oauthBusy}>
									{oauthBusy ? (
										<>
											<Loader2 className="animate-spin" />
											브라우저 로그인 대기 중…
										</>
									) : (
										<>
											<LogIn />
											브라우저로 로그인
										</>
									)}
								</Button>
							))}

						{/* API key provider */}
						{info.auth === 'api_key' && (
							<>
								{info.available && !info.selected && (
									<Button
										size="sm"
										variant="outline"
										onClick={() => selectM.mutate()}
										disabled={selectM.isPending}
									>
										사용
									</Button>
								)}
								<div className="flex w-full items-center gap-1.5">
									<Input
										type="password"
										value={keyInput}
										onChange={(e) => setKeyInput(e.target.value)}
										placeholder={info.envKey || 'API Key'}
										className="h-8 flex-1 font-mono text-xs"
									/>
									<Button
										size="sm"
										onClick={() => apiKeyM.mutate()}
										disabled={apiKeyM.isPending || !keyInput.trim()}
									>
										{apiKeyM.isPending ? <Loader2 className="animate-spin" /> : '저장'}
									</Button>
								</div>
								{info.signupUrl && (
									<Tooltip>
										<TooltipTrigger asChild>
											<Button size="sm" variant="ghost" asChild>
												<a href={info.signupUrl} target="_blank" rel="noopener noreferrer">
													<ExternalLink />키 발급
												</a>
											</Button>
										</TooltipTrigger>
										<TooltipContent>{info.signupUrl}</TooltipContent>
									</Tooltip>
								)}
							</>
						)}
			</div>
		</div>
	);
}
