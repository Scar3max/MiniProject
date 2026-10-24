import React from "react";
import { TOKENS } from "../tokens";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: SelectOption[];
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, options, id, className = "", style, ...props }, ref) => {
    const selectId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "0.375rem", width: "100%" }}>
        {label && (
          <label
            htmlFor={selectId}
            style={{
              fontSize: TOKENS.typography.sizes.sm,
              fontWeight: 500,
              color: TOKENS.colors.textPrimary,
            }}
          >
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={selectId}
          style={{
            width: "100%",
            padding: "0.5rem 0.75rem",
            fontSize: TOKENS.typography.sizes.base,
            backgroundColor: TOKENS.colors.surface,
            border: `1px solid ${error ? TOKENS.colors.dangerText : TOKENS.colors.border}`,
            borderRadius: TOKENS.radii.md,
            color: TOKENS.colors.textPrimary,
            fontFamily: "inherit",
            ...style,
          }}
          className={`focus:outline-none focus:border-[#46c4f6] focus:ring-1 focus:ring-[#46c4f6] ${className}`}
          {...props}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {error && (
          <span style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.dangerText }}>
            {error}
          </span>
        )}
      </div>
    );
  }
);

Select.displayName = "Select";
