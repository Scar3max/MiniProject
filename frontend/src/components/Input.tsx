import React from "react";
import { TOKENS } from "../tokens";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, id, className = "", style, ...props }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "0.375rem", width: "100%" }}>
        {label && (
          <label
            htmlFor={inputId}
            style={{
              fontSize: TOKENS.typography.sizes.sm,
              fontWeight: 500,
              color: TOKENS.colors.textPrimary,
            }}
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          style={{
            width: "100%",
            padding: "0.5rem 0.75rem",
            fontSize: TOKENS.typography.sizes.base,
            backgroundColor: TOKENS.colors.surface,
            border: `1px solid ${error ? TOKENS.colors.dangerText : TOKENS.colors.border}`,
            borderRadius: TOKENS.radii.md,
            color: TOKENS.colors.textPrimary,
            fontFamily: "inherit",
            transition: "border-color 150ms ease-in-out",
            ...style,
          }}
          className={`focus:outline-none focus:border-[#46c4f6] focus:ring-1 focus:ring-[#46c4f6] ${className}`}
          {...props}
        />
        {error && (
          <span style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.dangerText }}>
            {error}
          </span>
        )}
        {!error && helperText && (
          <span style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textMuted }}>
            {helperText}
          </span>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";
