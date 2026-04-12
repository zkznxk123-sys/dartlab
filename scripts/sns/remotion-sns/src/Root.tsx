import { Composition } from "remotion";
import { HookCard } from "./cards/HookCard";
import { ContextCard } from "./cards/ContextCard";
import { ChartCard } from "./cards/ChartCard";
import { InsightCard } from "./cards/InsightCard";
import { CtaCard } from "./cards/CtaCard";
import type { HookProps } from "./lib/types";

const DEFAULT_PROPS: HookProps = {
  pattern: "inequality",
  company: {
    code: "018880",
    name: "한온시스템",
    sector: "자동차부품",
  },
  hook: {
    line: "순이익의 7배를 배당으로",
    sub: "사모펀드가 10년간 쥐어짠 것",
  },
  context: {
    question: "어떤 회사가 버는 것의 7배를 주주에게 돌려주는가?",
    setup: "순이익 267억원. 배당금 1,850억원. 어딘가 이상하다.",
  },
  chart: {
    title: "2022년 한온시스템",
    items: [
      { label: "순이익", value: 267, unit: "억원", highlight: false },
      { label: "배당금", value: 1850, unit: "억원", highlight: true },
    ],
    caption: "배당 / 순이익 = 692%",
  },
  insight: {
    headline: "배당을 메우려고 빚을 냈다.",
    body: "2014년 사모펀드 인수 후 총차입금이 4천억에서 4.5조로 11배 급증. 이자비용이 이익을 먹기 시작했고, 2024년 첫 영업적자를 찍었다.",
  },
  cta: {
    blogSlug: "hanon-systems",
    youtubeId: "",
    tagline: "왜 이익을 넘는 배당이 나왔는가",
  },
};

const WIDTH = 1080;
const HEIGHT = 1350;

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="HookCard"
        component={HookCard}
        durationInFrames={30}
        fps={30}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={DEFAULT_PROPS}
      />
      <Composition
        id="ContextCard"
        component={ContextCard}
        durationInFrames={30}
        fps={30}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={DEFAULT_PROPS}
      />
      <Composition
        id="ChartCard"
        component={ChartCard}
        durationInFrames={30}
        fps={30}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={DEFAULT_PROPS}
      />
      <Composition
        id="InsightCard"
        component={InsightCard}
        durationInFrames={30}
        fps={30}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={DEFAULT_PROPS}
      />
      <Composition
        id="CtaCard"
        component={CtaCard}
        durationInFrames={30}
        fps={30}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={DEFAULT_PROPS}
      />
    </>
  );
};
