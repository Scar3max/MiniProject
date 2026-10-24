import React from "react";
import { FolderOpen } from "lucide-react";
import { TOKENS } from "../tokens";
import { Button } from "./Button";

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  className = "",
}) => {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        padding: "3rem 1.5rem",
        backgroundColor: TOKENS.colors.surfaceSubdued,
        borderRadius: TOKENS.radii.lg,
        border: `1px dashed ${TOKENS.colors.border}`,
      }}
      className={className}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          width: "3rem",
          height: "3rem",
          borderRadius: "50%",
          backgroundColor: TOKENS.colors.surface,
          color: TOKENS.colors.textMuted,
          marginBottom: "1rem",
          border: `1px solid ${TOKENS.colors.border}`,
        }}
      >
        {icon || <FolderOpen size={24} />}
      </div>
      <h3
        style={{
          fontSize: TOKENS.typography.sizes.lg,
          fontWeight: 600,
          color: TOKENS.colors.textPrimary,
          margin: "0 0 0.5rem 0",
        }}
      >
        {title}
      </h3>
      <p
        style={{
          fontSize: TOKENS.typography.sizes.sm,
          color: TOKENS.colors.textSecondary,
          maxWidth: "420px",
          margin: "0 0 1.25rem 0",
          lineHeight: 1.5,
        }}
      >
        {description}
      </p>
      {actionLabel && onAction && (
        <Button variant="primary" size="sm" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
};
