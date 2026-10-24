import React from "react";
import { TOKENS } from "../tokens";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = "primary",
  size = "md",
  isLoading = false,
  disabled,
  className = "",
  style,
  ...props
}) => {
  const baseStyles: React.CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "0.5rem",
    fontWeight: 500,
    borderRadius: TOKENS.radii.md,
    cursor: disabled || isLoading ? "not-allowed" : "pointer",
    transition: "all 150ms ease-in-out",
    border: "1px solid transparent",
    textDecoration: "none",
    opacity: disabled || isLoading ? 0.6 : 1,
    fontFamily: "inherit",
  };

  const sizeStyles: Record<string, React.CSSProperties> = {
    sm: { padding: "0.375rem 0.75rem", fontSize: TOKENS.typography.sizes.sm },
    md: { padding: "0.5rem 1rem", fontSize: TOKENS.typography.sizes.base },
    lg: { padding: "0.75rem 1.5rem", fontSize: TOKENS.typography.sizes.lg },
  };

  // Primary: Dark Navy button with white text (18.52:1 AAA)
  // Secondary: Accent cyan (#46c4f6) with Dark Navy text (11.54:1 AAA)
  const variantStyles: Record<string, React.CSSProperties> = {
    primary: {
      backgroundColor: TOKENS.colors.textPrimary,
      color: TOKENS.colors.textInverse,
      borderColor: TOKENS.colors.textPrimary,
    },
    secondary: {
      backgroundColor: TOKENS.colors.accent,
      color: TOKENS.colors.textPrimary,
      borderColor: TOKENS.colors.accent,
    },
    outline: {
      backgroundColor: TOKENS.colors.surface,
      color: TOKENS.colors.textPrimary,
      borderColor: TOKENS.colors.border,
    },
    ghost: {
      backgroundColor: "transparent",
      color: TOKENS.colors.textSecondary,
      borderColor: "transparent",
    },
    danger: {
      backgroundColor: TOKENS.colors.dangerBg,
      color: TOKENS.colors.dangerText,
      borderColor: "#fca5a5",
    },
  };

  return (
    <button
      disabled={disabled || isLoading}
      style={{
        ...baseStyles,
        ...sizeStyles[size],
        ...variantStyles[variant],
        ...style,
      }}
      className={`focus:outline-none focus:ring-2 focus:ring-[#46c4f6] ${className}`}
      {...props}
    >
      {isLoading && (
        <span
          style={{
            width: "1rem",
            height: "1rem",
            border: "2px solid currentColor",
            borderRightColor: "transparent",
            borderRadius: "50%",
            display: "inline-block",
            animation: "spin 0.75s linear infinite",
          }}
        />
      )}
      {children}
    </button>
  );
};
