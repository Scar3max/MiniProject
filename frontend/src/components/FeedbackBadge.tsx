import React from "react";
import { CheckCircle2, AlertCircle, XCircle, Clock, HelpCircle, MinusCircle } from "lucide-react";
import { getBadgeConfig } from "../utils/badgeMapper";
import { TOKENS } from "../tokens";

export interface FeedbackBadgeProps {
  classification: string | null | undefined;
  score?: number | null;
  className?: string;
}

export const FeedbackBadge: React.FC<FeedbackBadgeProps> = ({
  classification,
  score,
  className = "",
}) => {
  const config = getBadgeConfig(classification);

  const renderIcon = () => {
    const iconProps = { size: 14, strokeWidth: 2, "aria-hidden": true };
    switch (config.iconName) {
      case "CheckCircle2":
        return <CheckCircle2 {...iconProps} />;
      case "AlertCircle":
        return <AlertCircle {...iconProps} />;
      case "XCircle":
        return <XCircle {...iconProps} />;
      case "Clock":
        return <Clock {...iconProps} />;
      case "HelpCircle":
        return <HelpCircle {...iconProps} />;
      default:
        return <MinusCircle {...iconProps} />;
    }
  };

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.375rem",
        padding: "0.25rem 0.625rem",
        fontSize: TOKENS.typography.sizes.xs,
        fontWeight: 500,
        borderRadius: TOKENS.radii.full,
        backgroundColor: config.bg,
        color: config.color,
        border: `1px solid ${config.borderColor}`,
      }}
      className={className}
      role="status"
      aria-label={`Feedback: ${config.label}${score !== undefined && score !== null ? `, Score: ${score}/10` : ""}`}
    >
      {renderIcon()}
      <span>{config.label}</span>
      {score !== undefined && score !== null && (
        <span style={{ opacity: 0.85, fontWeight: 600 }}>({score}/10)</span>
      )}
    </span>
  );
};
