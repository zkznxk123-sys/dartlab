import { AbsoluteFill } from "remotion";
import { colors } from "../lib/colors";
import type { HookProps } from "../lib/types";

const fontFamily =
  "'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Malgun Gothic', sans-serif";

export const ContextCard: React.FC<HookProps> = ({ company, context }) => {
  return (
    <AbsoluteFill style={{ backgroundColor: colors.bgDark, fontFamily }}>
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at top right, rgba(234,70,71,0.12) 0%, transparent 55%)",
        }}
      />

      <AbsoluteFill
        style={{
          padding: "120px 80px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            fontSize: 26,
            color: colors.textDim,
            fontWeight: 700,
            letterSpacing: "3px",
            marginBottom: 32,
            textTransform: "uppercase",
          }}
        >
          {company.name} — {company.sector}
        </div>

        <div
          style={{
            fontSize: 68,
            fontWeight: 900,
            color: colors.text,
            lineHeight: 1.2,
            letterSpacing: "-1.5px",
            marginBottom: 60,
            whiteSpace: "pre-line",
          }}
        >
          {context.question}
        </div>

        <div
          style={{
            padding: "36px 44px",
            borderLeft: `6px solid ${colors.primary}`,
            backgroundColor: colors.bgCard,
            borderRadius: "0 16px 16px 0",
          }}
        >
          <div
            style={{
              fontSize: 38,
              color: colors.textMuted,
              lineHeight: 1.45,
              fontWeight: 600,
              letterSpacing: "-0.5px",
            }}
          >
            {context.setup}
          </div>
        </div>
      </AbsoluteFill>

      <AbsoluteFill
        style={{
          padding: "50px 80px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "flex-end",
          pointerEvents: "none",
        }}
      >
        <div
          style={{
            fontSize: 22,
            color: colors.textDim,
            textAlign: "right",
            fontWeight: 700,
          }}
        >
          dartlab · 2 / 5
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
