/**
 * frontend/src/utils/emojiStripper.ts
 * Strips emoji characters, presentation selectors, and pictographs from text.
 * Ensures that any backend/prompt responses or inputs are sanitized for the Bekon calm design language.
 */

// Comprehensive regex matching emojis, emoticons, pictographs, and presentation selectors
const EMOJI_REGEX = /(?:\p{Extended_Pictographic}|\p{Emoji_Presentation}|\p{Emoji_Modifier_Base}|\p{Emoji_Modifier}|\uFE0F|\u200D)/gu;

/**
 * Strips all emoji characters from the given string and collapses redundant whitespace.
 */
export function stripEmojis(text: string | null | undefined): string {
  if (!text) return "";
  return text
    .replace(EMOJI_REGEX, "")
    .replace(/[ \t]+/g, " ")
    .trim();
}
