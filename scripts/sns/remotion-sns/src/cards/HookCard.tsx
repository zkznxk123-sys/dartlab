import { AbsoluteFill, Img, staticFile } from "remotion";
import { colors } from "../lib/colors";
import type { HookProps } from "../lib/types";

const fontFamily =
  "'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Malgun Gothic', sans-serif";

export const HookCard: React.FC<HookProps> = ({ pattern, company, hook, bgImage }) => {
  return (
    <AbsoluteFill style={{ backgroundColor: colors.bgDark, fontFamily }}>
      {bgImage && (
        <AbsoluteFill>
          <Img
            src={staticFile(bgImage)}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              opacity: 0.28,
              filter: "blur(2px)",
            }}
          />
        </AbsoluteFill>
      )}

      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(5,8,17,0.4) 0%, rgba(5,8,17,0.85) 55%, rgba(5,8,17,0.98) 100%)",
        }}
      />

      <AbsoluteFill
        style={{
          padding: "90px 80px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <div
            style={{
              padding: "10px 20px",
              borderRadius: 999,
              backgroundColor: colors.primary,
              color: "#fff",
              fontSize: 28,
              fontWeight: 800,
              letterSpacing: "-0.5px",
            }}
          >
            {company.name}
          </div>
          <div
            style={{
              padding: "10px 18px",
              borderRadius: 999,
              border: `2px solid ${colors.border}`,
              color: colors.textMuted,
              fontSize: 24,
              fontFamily: "Menlo, Consolas, monospace",
              fontWeight: 600,
            }}
          >
            {company.code}
          </div>
        </div>

        <div>
          <div
            style={{
              fontSize: 28,
              color: colors.warning,
              fontWeight: 700,
              marginBottom: 28,
              letterSpacing: "-0.3px",
            }}
          >
            {hook.sub}
          </div>
          <div
            style={{
              fontSize: 104,
              fontWeight: 900,
              color: colors.text,
              lineHeight: 1.08,
              letterSpacing: "-3px",
              whiteSpace: "pre-line",
            }}
          >
            {hook.line}
          </div>
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div
            style={{
              fontSize: 22,
              color: colors.textDim,
              fontWeight: 600,
              letterSpacing: "1px",
              textTransform: "uppercase",
            }}
          >
            {pattern}
          </div>
          <div
            style={{
              fontSize: 26,
              color: colors.textMuted,
              fontWeight: 700,
            }}
          >
            스와이프 →
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
