import { describe, it, expect } from "vitest";
import { stripEmojis } from "./emojiStripper";

describe("stripEmojis utility", () => {
  it("removes basic pictographic emojis", () => {
    const input = "Great answer! 🎯 Let's dive deeper 🚀";
    expect(stripEmojis(input)).toBe("Great answer! Let's dive deeper");
  });

  it("removes compound emojis and modifiers", () => {
    const input = "Candidate response 👍🏽 with fire 🔥 and celebration 🎉!";
    expect(stripEmojis(input)).toBe("Candidate response with fire and celebration !");
  });

  it("preserves alphanumeric characters and standard punctuation", () => {
    const input = "ACID properties: Atomicity, Consistency, Isolation, Durability (100%).";
    expect(stripEmojis(input)).toBe(input);
  });

  it("handles null and undefined gracefully", () => {
    expect(stripEmojis(null)).toBe("");
    expect(stripEmojis(undefined)).toBe("");
    expect(stripEmojis("")).toBe("");
  });
});
