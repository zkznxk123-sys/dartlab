export type ChartItem = {
  label: string;
  value: number;
  unit: string;
  highlight: boolean;
};

export type HookProps = {
  pattern: string;
  company: { code: string; name: string; sector: string };
  hook: { line: string; sub: string };
  context: { question: string; setup: string };
  chart: {
    title: string;
    items: ChartItem[];
    caption: string;
  };
  insight: { headline: string; body: string };
  cta: { blogSlug: string; youtubeId: string; tagline: string };
  /** optional background image (Flux-generated), staticFile path */
  bgImage?: string;
};
