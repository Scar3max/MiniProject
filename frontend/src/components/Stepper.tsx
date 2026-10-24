import React from "react";
import { Check } from "lucide-react";
import { TOKENS } from "../tokens";

export interface StepItem {
  title: string;
  description?: string;
}

export interface StepperProps {
  steps: StepItem[];
  currentStep: number;
}

export const Stepper: React.FC<StepperProps> = ({ steps, currentStep }) => {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        width: "100%",
        marginBottom: "2rem",
      }}
    >
      {steps.map((step, idx) => {
        const isCompleted = idx < currentStep;
        const isCurrent = idx === currentStep;

        return (
          <React.Fragment key={step.title}>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                position: "relative",
              }}
            >
              <div
                style={{
                  width: "2rem",
                  height: "2rem",
                  borderRadius: "50%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: TOKENS.typography.sizes.sm,
                  fontWeight: 600,
                  backgroundColor: isCompleted
                    ? TOKENS.colors.textPrimary
                    : isCurrent
                    ? TOKENS.colors.accent
                    : TOKENS.colors.surfaceSubdued,
                  color: isCompleted
                    ? TOKENS.colors.textInverse
                    : isCurrent
                    ? TOKENS.colors.textPrimary
                    : TOKENS.colors.textMuted,
                  border: `2px solid ${
                    isCompleted
                      ? TOKENS.colors.textPrimary
                      : isCurrent
                      ? TOKENS.colors.accent
                      : TOKENS.colors.border
                  }`,
                  transition: "all 150ms ease",
                }}
              >
                {isCompleted ? <Check size={14} strokeWidth={2.5} /> : idx + 1}
              </div>
              <span
                style={{
                  marginTop: "0.5rem",
                  fontSize: TOKENS.typography.sizes.xs,
                  fontWeight: isCurrent ? 600 : 500,
                  color: isCurrent ? TOKENS.colors.textPrimary : TOKENS.colors.textMuted,
                  whiteSpace: "nowrap",
                }}
              >
                {step.title}
              </span>
            </div>
            {idx < steps.length - 1 && (
              <div
                style={{
                  flex: 1,
                  height: "2px",
                  backgroundColor: idx < currentStep ? TOKENS.colors.textPrimary : TOKENS.colors.border,
                  margin: "0 0.75rem",
                  marginBottom: "1.25rem",
                  transition: "background-color 150ms ease",
                }}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};
