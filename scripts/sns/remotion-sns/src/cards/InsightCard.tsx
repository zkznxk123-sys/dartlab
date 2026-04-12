import { AbsoluteFill } from "remotion";
import { colors } from "../lib/colors";
import type { HookProps } from "../lib/types";

const fontFamily =
  "'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Malgun Gothic', sans-serif";

export const InsightCard: React.FC<HookProps> = ({ company, insight }) => {
  return (
    <AbsoluteFill style={{ backgroundColor: colors.bgDark, fontFamily }}>
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at bottom left, rgba(251,146,60,0.1) 0%, transparent 60%)",
        }}
      />

      <AbsoluteFill
        style={{
          padding: "120px 80px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          gap: 56,
        }}
      >
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 14,
            fontSize: 26,
            color: colors.accent,
            fontWeight: 800,
            letterSpacing: "2px",
            textTransform: "uppercase",
          }}
        >
          <span
            style={{
              display: "inline-block",
              width: 12,
              height: 12,
              borderRadius: 999,
              backgroundColor: colors.accent,
            }}
          />
          그래서 무슨 일이?
        </div>

        <div
          style={{
            fontSize: 82,
            fontWeight: 900,
            color: colors.text,
            lineHeight: 1.15,
            letterSpacing: "-2px",
            whiteSpace: "pre-line",
          }}
        >
          {insight.headline}
        </div>

        <div
          style={{
            fontSize: 38,
            color: colors.textMuted,
            lineHeight: 1.55,
            fontWeight: 500,
            letterSpacing: "-0.3px",
          }}
        >
          {insight.body}
        </div>
      </AbsoluteFill>

      <AbsoluteFill
        style={{
          padding: "50px 80px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-end",
          pointerEvents: "none",
        }}
      >
        <div style={{ fontSize: 22, color: colors.textDim, fontWeight: 700 }}>
          {company.name} ({company.code})
        </div>
        <div
          style={{
            fontSize: 22,
            color: colors.textDim,
            fontWeight: 700,
          }}
        >
          dartlab · 4 / 5
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
