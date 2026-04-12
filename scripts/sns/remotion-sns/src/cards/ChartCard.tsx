import { AbsoluteFill } from "remotion";
import { colors } from "../lib/colors";
import type { HookProps } from "../lib/types";

const fontFamily =
  "'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Malgun Gothic', sans-serif";

const formatNumber = (v: number): string => {
  if (v >= 10000) return (v / 10000).toFixed(1).replace(/\.0$/, "") + "만";
  if (v >= 1000) return v.toLocaleString();
  return v.toString();
};

export const ChartCard: React.FC<HookProps> = ({ chart }) => {
  const maxValue = Math.max(...chart.items.map((i) => i.value));

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bgDark, fontFamily }}>
      <AbsoluteFill
        style={{
          padding: "100px 80px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
        }}
      >
        <div>
          <div
            style={{
              fontSize: 28,
              color: colors.textDim,
              fontWeight: 700,
              letterSpacing: "2px",
              textTransform: "uppercase",
              marginBottom: 20,
            }}
          >
            숫자로 보면
          </div>
          <div
            style={{
              fontSize: 54,
              fontWeight: 900,
              color: colors.text,
              letterSpacing: "-1.2px",
              lineHeight: 1.2,
            }}
          >
            {chart.title}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 40 }}>
          {chart.items.map((item) => {
            const widthPct = (item.value / maxValue) * 100;
            const barColor = item.highlight ? colors.primary : colors.border;
            const labelColor = item.highlight ? colors.primaryLight : colors.textMuted;

            return (
              <div key={item.label}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "baseline",
                    marginBottom: 14,
                  }}
                >
                  <div
                    style={{
                      fontSize: 36,
                      color: labelColor,
                      fontWeight: 800,
                      letterSpacing: "-0.5px",
                    }}
                  >
                    {item.label}
                  </div>
                  <div
                    style={{
                      fontSize: 68,
                      color: item.highlight ? colors.text : colors.textMuted,
                      fontWeight: 900,
                      letterSpacing: "-2px",
                    }}
                  >
                    {formatNumber(item.value)}
                    <span
                      style={{
                        fontSize: 30,
                        color: colors.textDim,
                        marginLeft: 10,
                        fontWeight: 700,
                      }}
                    >
                      {item.unit}
                    </span>
                  </div>
                </div>
                <div
                  style={{
                    height: 28,
                    backgroundColor: colors.bgCard,
                    borderRadius: 14,
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${widthPct}%`,
                      height: "100%",
                      backgroundColor: barColor,
                      borderRadius: 14,
                      boxShadow: item.highlight
                        ? `0 0 30px ${colors.primary}80`
                        : "none",
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>

        <div
          style={{
            textAlign: "center",
            padding: "28px 40px",
            backgroundColor: colors.bgCard,
            borderRadius: 20,
            border: `2px solid ${colors.primary}`,
          }}
        >
          <div
            style={{
              fontSize: 44,
              color: colors.warning,
              fontWeight: 900,
              letterSpacing: "-1px",
            }}
          >
            {chart.caption}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
