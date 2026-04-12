import { AbsoluteFill } from "remotion";
import { colors } from "../lib/colors";
import type { HookProps } from "../lib/types";

const fontFamily =
  "'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Malgun Gothic', sans-serif";

type LinkRow = { icon: string; label: string; url: string };

export const CtaCard: React.FC<HookProps> = ({ company, cta }) => {
  const rows: LinkRow[] = [
    {
      icon: "📊",
      label: "전문 분석 — 블로그",
      url: `eddmpython.github.io/dartlab/blog/${cta.blogSlug}`,
    },
    ...(cta.youtubeId
      ? [{ icon: "🎬", label: "영상으로 보기 — YouTube", url: `youtu.be/${cta.youtubeId}` }]
      : []),
    {
      icon: "💻",
      label: "코드로 직접 분석 — GitHub",
      url: "github.com/eddmpython/dartlab",
    },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bgDark, fontFamily }}>
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at center, rgba(234,70,71,0.15) 0%, transparent 65%)",
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
        <div>
          <div
            style={{
              fontSize: 28,
              color: colors.textDim,
              fontWeight: 800,
              letterSpacing: "3px",
              textTransform: "uppercase",
              marginBottom: 24,
            }}
          >
            더 깊이 보기
          </div>
          <div
            style={{
              fontSize: 76,
              fontWeight: 900,
              color: colors.text,
              lineHeight: 1.1,
              letterSpacing: "-2px",
              marginBottom: 20,
            }}
          >
            {company.name}
            <br />
            <span
              style={{
                background: `linear-gradient(90deg, ${colors.primary}, ${colors.accent})`,
                WebkitBackgroundClip: "text",
                backgroundClip: "text",
                color: "transparent",
              }}
            >
              {cta.tagline}
            </span>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {rows.map((row) => (
            <div
              key={row.label}
              style={{
                padding: "32px 36px",
                backgroundColor: colors.bgCard,
                borderRadius: 18,
                border: `2px solid ${colors.border}`,
                display: "flex",
                alignItems: "center",
                gap: 24,
              }}
            >
              <div style={{ fontSize: 48, lineHeight: 1 }}>{row.icon}</div>
              <div style={{ flex: 1 }}>
                <div
                  style={{
                    fontSize: 28,
                    color: colors.text,
                    fontWeight: 800,
                    letterSpacing: "-0.3px",
                    marginBottom: 6,
                  }}
                >
                  {row.label}
                </div>
                <div
                  style={{
                    fontSize: 24,
                    color: colors.textDim,
                    fontFamily: "Menlo, Consolas, monospace",
                    fontWeight: 600,
                  }}
                >
                  {row.url}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div
          style={{
            textAlign: "center",
            fontSize: 32,
            color: colors.text,
            fontWeight: 900,
            letterSpacing: "-0.3px",
          }}
        >
          <span style={{ color: colors.primary }}>dartlab</span> —
          종목코드 하나, 기업의 전체 이야기
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
