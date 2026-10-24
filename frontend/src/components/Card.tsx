import React from "react";
import { TOKENS } from "../tokens";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  subdued?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  subdued = false,
  className = "",
  style,
  ...props
}) => {
  return (
    <div
      style={{
        backgroundColor: subdued ? TOKENS.colors.surfaceSubdued : TOKENS.colors.surface,
        border: `1px solid ${TOKENS.colors.border}`,
        borderRadius: TOKENS.radii.lg,
        padding: "1.5rem",
        boxShadow: TOKENS.shadows.sm,
        ...style,
      }}
      className={`page-card ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};
