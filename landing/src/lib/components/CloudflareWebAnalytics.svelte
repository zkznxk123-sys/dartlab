<script lang="ts">
	import { onMount } from 'svelte';

	function extractCloudflareBeaconToken(rawValue: unknown): string {
		const value = String(rawValue ?? '').trim();
		if (value.length === 0 || value === 'disabled') return value;

		const beaconAttribute = value.match(/data-cf-beacon\s*=\s*(["'])(.*?)\1/i)?.[2];
		const candidate = beaconAttribute ?? value;
		try {
			const parsed = JSON.parse(candidate) as { token?: unknown };
			if (typeof parsed.token === 'string') return parsed.token.trim();
		} catch {
			const tokenMatch =
				candidate.match(/["']token["']\s*:\s*["']([^"']+)["']/i) ??
				value.match(/["']token["']\s*:\s*["']([^"']+)["']/i);
			if (tokenMatch?.[1]) return tokenMatch[1].trim();
		}

		return value;
	}

	const webAnalyticsToken = extractCloudflareBeaconToken(
		import.meta.env.VITE_CLOUDFLARE_WEB_ANALYTICS_TOKEN
	);
	const shouldLoadWebAnalytics =
		import.meta.env.PROD && webAnalyticsToken.length > 0 && webAnalyticsToken !== 'disabled';

	onMount(() => {
		if (!shouldLoadWebAnalytics) return;
		if (document.querySelector('script[data-dartlab-cloudflare-web-analytics]')) return;

		for (const href of [
			'https://static.cloudflareinsights.com',
			'https://cloudflareinsights.com'
		]) {
			if (document.querySelector(`link[rel="preconnect"][href="${href}"]`)) continue;
			const link = document.createElement('link');
			link.rel = 'preconnect';
			link.href = href;
			document.head.append(link);
		}

		const script = document.createElement('script');
		script.defer = true;
		script.src = 'https://static.cloudflareinsights.com/beacon.min.js';
		script.dataset.cfBeacon = JSON.stringify({ token: webAnalyticsToken });
		script.dataset.dartlabCloudflareWebAnalytics = 'true';
		document.head.append(script);
	});
</script>
