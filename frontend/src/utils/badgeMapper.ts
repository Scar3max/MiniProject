/**
 * frontend/src/utils/badgeMapper.ts
 * Total mapping function from backend classification / category to calm label,
 * pastel colors, and Lucide icons without raw enums or emojis.
 */

import { TOKENS } from "../tokens";

export type BadgeVariant = "success" | "warning" | "danger" | "info" | "neutral";

export interface BadgeConfig {
  label: string;
  variant: BadgeVariant;
  bg: string;
  color: string;
  borderColor: string;
  iconName: "CheckCircle2" | "AlertCircle" | "XCircle" | "HelpCircle" | "Clock" | "MinusCircle";
}

export function getBadgeConfig(rawTypeOrLabel: string | null | undefined): BadgeConfig {
  const norm = (rawTypeOrLabel || "").trim().toUpperCase().replace(/[\s_-]+/g, "_");

  switch (norm) {
    case "GOOD":
    case "GOOD_ANSWER":
    case "POSITIVE":
    case "CORRECT":
      return {
        label: "Good Answer",
        variant: "success",
        bg: TOKENS.colors.successBg,
        color: TOKENS.colors.successText,
        borderColor: "#bbf7d0",
        iconName: "CheckCircle2",
      };

    case "VAGUE":
      return {
        label: "Vague",
        variant: "warning",
        bg: TOKENS.colors.warningBg,
        color: TOKENS.colors.warningText,
        borderColor: "#fde68a",
        iconName: "AlertCircle",
      };

    case "HESITATION":
    case "HESITATION_SIGNAL":
      return {
        label: "Hesitation",
        variant: "warning",
        bg: TOKENS.colors.warningBg,
        color: TOKENS.colors.warningText,
        borderColor: "#fde68a",
        iconName: "Clock",
      };

    case "PARTIALLY_CORRECT":
      return {
        label: "Partially Correct",
        variant: "info",
        bg: TOKENS.colors.infoBg,
        color: TOKENS.colors.infoText,
        borderColor: "#bae6fd",
        iconName: "HelpCircle",
      };

    case "KNOWLEDGE_GAP":
      return {
        label: "Knowledge Gap",
        variant: "danger",
        bg: TOKENS.colors.dangerBg,
        color: TOKENS.colors.dangerText,
        borderColor: "#fecaca",
        iconName: "XCircle",
      };

    case "EVASIVE":
    case "EVASIVE_NON_ANSWER":
    case "EVASIVE_CHALLENGE":
      return {
        label: "Evasive",
        variant: "danger",
        bg: TOKENS.colors.dangerBg,
        color: TOKENS.colors.dangerText,
        borderColor: "#fecaca",
        iconName: "AlertCircle",
      };

    case "INCORRECT":
    case "FACTUALLY_INCORRECT":
    case "DANGER":
      return {
        label: "Incorrect",
        variant: "danger",
        bg: TOKENS.colors.dangerBg,
        color: TOKENS.colors.dangerText,
        borderColor: "#fecaca",
        iconName: "XCircle",
      };

    default:
      return {
        label: rawTypeOrLabel ? rawTypeOrLabel.replace(/_/g, " ") : "Evaluated",
        variant: "neutral",
        bg: TOKENS.colors.neutralBg,
        color: TOKENS.colors.neutralText,
        borderColor: "#cbd5e1",
        iconName: "MinusCircle",
      };
  }
}
