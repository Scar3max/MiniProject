import React from "react";
import { TOKENS } from "../tokens";

export interface SpinnerProps {
  size?: "sm" | "md" | "lg";
  label?: string;
  className?: string;
}

export const Spinner: React.FC<SpinnerProps> = ({ size = "md", label, className = "" }) => {
  const sizeMap = {
    sm: "1rem",
    md: "2rem",
    lg: "3rem",
  };

  const borderMap = {
    sm: "2px",
    md: "3px",
    lg: "4px",
  };

  return (
    <div
      style={{
        display: "inline-flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "0.75rem",
      }}
      className={className}
      role="status"
    >
      <div
        style={{
          width: sizeMap[size],
          height: sizeMap[size],
          border: `${borderMap[size]} solid ${TOKENS.colors.border}`,
          borderTopColor: TOKENS.colors.accent,
          borderRadius: "50%",
          animation: "spin 0.8s linear infinite",
        }}
      />
      {label && (
        <span
          style={{
            fontSize: TOKENS.typography.sizes.sm,
            color: TOKENS.colors.textSecondary,
          }}
        >
          {label}
        </span>
      )}
    </div>
  );
};
