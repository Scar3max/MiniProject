import { describe, it, expect } from "vitest";
import { getBadgeConfig } from "./badgeMapper";

describe("getBadgeConfig", () => {
  it("maps GOOD and positive classifications to success variant", () => {
    const config = getBadgeConfig("GOOD");
    expect(config.label).toBe("Good Answer");
    expect(config.variant).toBe("success");
    expect(config.iconName).toBe("CheckCircle2");
  });

  it("maps VAGUE and HESITATION to warning variant", () => {
    const vagueConfig = getBadgeConfig("VAGUE");
    expect(vagueConfig.label).toBe("Vague");
    expect(vagueConfig.variant).toBe("warning");
    expect(vagueConfig.iconName).toBe("AlertCircle");

    const hesitationConfig = getBadgeConfig("HESITATION_SIGNAL");
    expect(hesitationConfig.label).toBe("Hesitation");
    expect(hesitationConfig.variant).toBe("warning");
    expect(hesitationConfig.iconName).toBe("Clock");
  });

  it("maps INCORRECT, KNOWLEDGE_GAP and EVASIVE to danger variant", () => {
    const incorrectConfig = getBadgeConfig("FACTUALLY_INCORRECT");
    expect(incorrectConfig.label).toBe("Incorrect");
    expect(incorrectConfig.variant).toBe("danger");
    expect(incorrectConfig.iconName).toBe("XCircle");

    const gapConfig = getBadgeConfig("KNOWLEDGE_GAP");
    expect(gapConfig.label).toBe("Knowledge Gap");
    expect(gapConfig.variant).toBe("danger");

    const evasiveConfig = getBadgeConfig("EVASIVE_NON_ANSWER");
    expect(evasiveConfig.label).toBe("Evasive");
    expect(evasiveConfig.variant).toBe("danger");
  });

  it("falls back to neutral variant for unexpected or null input", () => {
    const nullConfig = getBadgeConfig(null);
    expect(nullConfig.variant).toBe("neutral");
    expect(nullConfig.label).toBe("Evaluated");

    const unknownConfig = getBadgeConfig("CUSTOM_FEEDBACK");
    expect(unknownConfig.variant).toBe("neutral");
    expect(unknownConfig.label).toBe("CUSTOM FEEDBACK");
  });
});
