/**
 * frontend/src/services/interviewStream.ts
 * Implements SSE streaming over HTTP POST using fetch and ReadableStream.
 * Handles custom CSRF headers, emits typed status and result events, and supports
 * seamless fallback to standard POST /api/interviews/{id}/answer upon connection failures.
 */

import { api, getCookie, RateLimitError } from "./apiClient";
import type { paths } from "../types/api";

export type TurnResponse = paths["/api/interviews/{session_id}/answer"]["post"]["responses"]["200"]["content"]["application/json"];

export interface StreamStatusPayload {
  stage: string;
  message: string;
}

export interface StreamCallbacks {
  onStatus?: (status: StreamStatusPayload) => void;
  onResult?: (result: TurnResponse) => void;
  onError?: (error: Error) => void;
}

/**
 * Submit an answer using SSE streaming. If streaming cannot connect or drops,
 * automatically falls back to standard POST /answer.
 */
export async function submitAnswerStream(
  sessionId: string,
  answer: string,
  callbacks: StreamCallbacks
): Promise<TurnResponse> {
  const url = `/api/interviews/${sessionId}/answer/stream`;
  const csrfToken = getCookie("csrf_token");

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "text/event-stream",
  };
  if (csrfToken) {
    headers["X-CSRF-Token"] = csrfToken;
  }

  let receivedResult: TurnResponse | null = null;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify({ answer }),
      credentials: "include",
    });

    if (response.status === 429) {
      const retryHeader = response.headers.get("Retry-After");
      const seconds = retryHeader ? parseInt(retryHeader, 10) || 60 : 60;
      throw new RateLimitError(seconds);
    }

    if (!response.ok || !response.body) {
      // If streaming endpoint returned 404/501 or server doesn't support streaming, fall back to plain POST
      return await api.submitAnswer(sessionId, { answer });
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      // Keep unfinished line in buffer
      buffer = lines.pop() || "";

      let currentEvent = "message";
      let currentData = "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) {
          // Empty line indicates event boundary
          if (currentData) {
            try {
              const parsed = JSON.parse(currentData);
              if (currentEvent === "status") {
                callbacks.onStatus?.(parsed as StreamStatusPayload);
              } else if (currentEvent === "result") {
                receivedResult = parsed as TurnResponse;
                callbacks.onResult?.(receivedResult);
              } else if (currentEvent === "error") {
                const err = new Error(parsed.detail || parsed.error || "Streaming error occurred");
                callbacks.onError?.(err);
                throw err;
              }
            } catch (err: any) {
              if (err.name === "RateLimitError" || err.message?.includes("Streaming error")) {
                throw err;
              }
            }
            currentData = "";
            currentEvent = "message";
          }
          continue;
        }

        if (trimmed.startsWith("event:")) {
          currentEvent = trimmed.slice(6).trim();
        } else if (trimmed.startsWith("data:")) {
          currentData = trimmed.slice(5).trim();
        }
      }
    }

    if (receivedResult) {
      return receivedResult;
    }

    // If stream closed cleanly without a result payload, fetch latest interview state
    const interview: any = await api.getInterview(sessionId);
    if (interview && interview.turns && interview.turns.length > 0) {
      const latestTurn = interview.turns[interview.turns.length - 1];
      return {
        session_id: typeof sessionId === "string" ? parseInt(sessionId, 10) : sessionId,
        turn_number: latestTurn.turn_number,
        score: latestTurn.score,
        answer_type: latestTurn.answer_classification,
        label: latestTurn.answer_classification,
        category: "neutral",
        interviewer_message: interview.pending_question || "",
        current_subtopic: latestTurn.subtopic || "",
        current_difficulty: interview.current_difficulty || 1,
        status: interview.status || "IN_PROGRESS",
      };
    }

    throw new Error("Stream concluded without receiving turn result.");
  } catch (err: any) {
    if (err instanceof RateLimitError) {
      throw err;
    }
    // Network or streaming failure: fallback to plain endpoint
    callbacks.onStatus?.({ stage: "fallback", message: "Reconnecting via standard connection..." });
    return await api.submitAnswer(sessionId, { answer });
  }
}
