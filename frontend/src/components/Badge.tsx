import React from "react";
import { TOKENS } from "../tokens";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "neutral" | "info" | "success" | "warning" | "danger" | "accent";
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = "neutral",
  className = "",
  style,
  ...props
}) => {
  const variantMap: Record<string, { bg: string; color: string; border: string }> = {
    neutral: {
      bg: TOKENS.colors.neutralBg,
      color: TOKENS.colors.neutralText,
      border: TOKENS.colors.border,
    },
    info: {
      bg: TOKENS.colors.infoBg,
      color: TOKENS.colors.infoText,
      border: "#bae6fd",
    },
    success: {
      bg: TOKENS.colors.successBg,
      color: TOKENS.colors.successText,
      border: "#bbf7d0",
    },
    warning: {
      bg: TOKENS.colors.warningBg,
      color: TOKENS.colors.warningText,
      border: "#fde68a",
    },
    danger: {
      bg: TOKENS.colors.dangerBg,
      color: TOKENS.colors.dangerText,
      border: "#fecaca",
    },
    accent: {
      bg: TOKENS.colors.accentLight,
      color: "#0369a1",
      border: "#bae6fd",
    },
  };

  const current = variantMap[variant] || variantMap.neutral;

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.25rem",
        padding: "0.2rem 0.5rem",
        fontSize: TOKENS.typography.sizes.xs,
        fontWeight: 500,
        borderRadius: TOKENS.radii.full,
        backgroundColor: current.bg,
        color: current.color,
        border: `1px solid ${current.border}`,
        whiteSpace: "nowrap",
        ...style,
      }}
      className={className}
      {...props}
    >
      {children}
    </span>
  );
};
