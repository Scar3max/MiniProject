import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Send,
  Square,
  Clock,
  RotateCcw,
  Printer,
  CheckCircle2,
  AlertTriangle,
  Info,
  HelpCircle,
  AlertCircle,
} from "lucide-react";
import { api, RateLimitError } from "../services/apiClient";
import { submitAnswerStream } from "../services/interviewStream";
import type { StreamStatusPayload } from "../services/interviewStream";
import { stripEmojis } from "../utils/emojiStripper";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Badge } from "../components/Badge";
import { FeedbackBadge } from "../components/FeedbackBadge";
import { Spinner } from "../components/Spinner";
import { Modal } from "../components/Modal";
import { useToast } from "../components/Toast";
import { TOKENS } from "../tokens";

interface TurnData {
  turn_number: number;
  question_text: string;
  candidate_answer?: string | null;
  score?: number | null;
  answer_classification?: string | null;
  subtopic?: string | null;
  justification?: string | null;
  momentum?: string | null;
}

interface SummaryItem {
  category: "strength" | "gap" | "info" | string;
  title: string;
  text: string;
}

export const InterviewRoomPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { showError, showSuccess } = useToast();

  const [isLoading, setIsLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  // Session state
  const [sessionInfo, setSessionInfo] = useState<any>(null);
  const [turns, setTurns] = useState<TurnData[]>([]);
  const [pendingQuestion, setPendingQuestion] = useState<string>("");
  const [currentDifficulty, setCurrentDifficulty] = useState<string>("Fundamental");
  const [sessionStatus, setSessionStatus] = useState<"IN_PROGRESS" | "COMPLETED">("IN_PROGRESS");
  const [summaryItems, setSummaryItems] = useState<SummaryItem[]>([]);

  // Input & submission state
  const [answerInput, setAnswerInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [streamStatus, setStreamStatus] = useState<StreamStatusPayload | null>(null);
  const [rateLimitCountdown, setRateLimitCountdown] = useState<number | null>(null);

  // End Interview Modal
  const [showEndModal, setShowEndModal] = useState(false);
  const [isEnding, setIsEnding] = useState(false);

  // Elapsed timer
  const [secondsElapsed, setSecondsElapsed] = useState(0);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Timer interval for in-progress session
  useEffect(() => {
    if (sessionStatus !== "IN_PROGRESS") return;
    const interval = setInterval(() => {
      setSecondsElapsed((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [sessionStatus]);

  // Rate limit countdown interval
  useEffect(() => {
    if (rateLimitCountdown === null || rateLimitCountdown <= 0) return;
    const interval = setInterval(() => {
      setRateLimitCountdown((prev) => {
        if (prev === null || prev <= 1) return null;
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [rateLimitCountdown]);

  // Fetch interview data on mount or id change
  const fetchSession = async () => {
    if (!id) return;
    try {
      setIsLoading(true);
      setNotFound(false);

      const data = await api.getInterview(id);
      const sess = (data as any).session || data;
      setSessionInfo(sess);
      setTurns((data as any).turns || []);
      setPendingQuestion((data as any).pending_question || sess.pending_question || "");
      setCurrentDifficulty((data as any).current_difficulty || sess.current_difficulty || "Fundamental");
      
      const status = (sess.ended_at || (data as any).status === "COMPLETED") ? "COMPLETED" : "IN_PROGRESS";
      setSessionStatus(status);
      setSummaryItems((data as any).final_summary_items || sess.final_summary_items || []);

      // Calculate initial elapsed seconds if started_at exists
      if (sess.started_at) {
        const start = new Date(sess.started_at).getTime();
        const end = sess.ended_at ? new Date(sess.ended_at).getTime() : Date.now();
        setSecondsElapsed(Math.max(0, Math.floor((end - start) / 1000)));
      }
    } catch (err: any) {
      if (err.status === 404 || err.status === 403) {
        setNotFound(true);
      } else {
        showError(err?.message || "Could not load interview session.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSession();
  }, [id]);

  useEffect(() => {
    scrollToBottom();
  }, [turns, pendingQuestion, streamStatus, isSubmitting]);

  // Submit candidate answer
  const handleSubmitAnswer = async () => {
    const text = answerInput.trim();
    if (!text || isSubmitting || rateLimitCountdown !== null || !id) return;

    // Check for "quit" alias
    if (text.toLowerCase() === "quit") {
      setAnswerInput("");
      handleEndInterview();
      return;
    }

    setIsSubmitting(true);
    setStreamStatus({ stage: "evaluating", message: "Evaluating technical answer..." });

    // Optimistically record the candidate answer in current turn
    const activeQuestion = pendingQuestion;
    setAnswerInput("");

    try {
      const turnResult: any = await submitAnswerStream(id, text, {
        onStatus: (status) => setStreamStatus(status),
        onResult: () => setStreamStatus(null),
        onError: (err) => console.warn("Stream event error:", err),
      });

      // Update state with confirmed turn response
      if (turnResult.status === "COMPLETED") {
        setSessionStatus("COMPLETED");
        await fetchSession(); // Refresh complete summary and stats
        showSuccess("Interview completed successfully.");
      } else {
        setTurns((prev) => [
          ...prev,
          {
            turn_number: turnResult.turn_number,
            question_text: activeQuestion,
            candidate_answer: text,
            score: turnResult.score,
            answer_classification: turnResult.answer_type || turnResult.label,
            subtopic: turnResult.current_subtopic,
          },
        ]);
        setPendingQuestion(stripEmojis(turnResult.interviewer_message || ""));
        if (turnResult.current_difficulty) {
          setCurrentDifficulty(turnResult.current_difficulty);
        }
      }
    } catch (err: any) {
      if (err instanceof RateLimitError) {
        setRateLimitCountdown(err.retryAfterSeconds);
        showError(`Rate limit reached. Please wait ${err.retryAfterSeconds}s before retrying.`);
      } else {
        showError(err?.message || "Failed to submit answer. Session refreshed.");
        // Refetch state safely to prevent duplicate turns
        await fetchSession();
      }
    } finally {
      setIsSubmitting(false);
      setStreamStatus(null);
      textareaRef.current?.focus();
    }
  };

  const handleEndInterview = async () => {
    if (!id || isEnding) return;
    setIsEnding(true);
    try {
      await api.endInterview(id);
      setShowEndModal(false);
      setSessionStatus("COMPLETED");
      await fetchSession();
      showSuccess("Interview concluded.");
    } catch (err: any) {
      showError(err?.message || "Failed to end interview.");
    } finally {
      setIsEnding(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmitAnswer();
    }
  };

  const formatTimer = (totalSec: number) => {
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  };

  // 404 / 403 Not Found State
  if (notFound) {
    return (
      <div style={{ textAlign: "center", padding: "4rem 1rem" }}>
        <Card style={{ maxWidth: "480px", margin: "0 auto", padding: "2.5rem" }}>
          <div
            style={{
              width: "3rem",
              height: "3rem",
              borderRadius: "50%",
              backgroundColor: TOKENS.colors.dangerBg,
              color: TOKENS.colors.dangerText,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: "1rem",
            }}
          >
            <AlertCircle size={24} />
          </div>
          <h2 style={{ fontSize: TOKENS.typography.sizes.xl, fontWeight: 600, margin: "0 0 0.5rem 0" }}>
            Interview Not Found
          </h2>
          <p style={{ fontSize: TOKENS.typography.sizes.sm, color: TOKENS.colors.textSecondary, marginBottom: "1.5rem" }}>
            The requested interview session does not exist or you do not have permission to view it.
          </p>
          <Button variant="primary" onClick={() => navigate("/")}>
            Back to Dashboard
          </Button>
        </Card>
      </div>
    );
  }

  // Loading State / Preparing Interview State
  if (isLoading) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "50vh",
          textAlign: "center",
        }}
      >
        <Spinner size="lg" />
        <h2 style={{ fontSize: TOKENS.typography.sizes.lg, fontWeight: 600, marginTop: "1.5rem", color: TOKENS.colors.textPrimary }}>
          Preparing your technical interview...
        </h2>
        <p style={{ fontSize: TOKENS.typography.sizes.sm, color: TOKENS.colors.textSecondary, marginTop: "0.5rem" }}>
          Synthesizing syllabus structure and initial technical opener.
        </p>
      </div>
    );
  }

  // ==========================================
  // COMPLETED SUMMARY VIEW
  // ==========================================
  if (sessionStatus === "COMPLETED") {
    const overallScore = sessionInfo?.overall_score !== null && sessionInfo?.overall_score !== undefined
      ? Math.round(sessionInfo.overall_score * 10) / 10
      : null;

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
        {/* Header Bar */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Badge variant="success">Interview Completed</Badge>
              <span style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textMuted }}>
                Duration: {formatTimer(secondsElapsed)}
              </span>
            </div>
            <h1
              style={{
                fontSize: TOKENS.typography.sizes["2xl"],
                fontWeight: 700,
                color: TOKENS.colors.textPrimary,
                margin: "0.25rem 0 0 0",
              }}
            >
              {sessionInfo?.domain || "Technical"} Evaluation Report
            </h1>
          </div>

          <div style={{ display: "flex", gap: "0.75rem" }} className="no-print">
            <Button variant="outline" size="sm" onClick={() => window.print()}>
              <Printer size={16} /> Download Report
            </Button>
            <Button variant="primary" size="sm" onClick={() => navigate("/")}>
              <RotateCcw size={16} /> Practice Again
            </Button>
          </div>
        </div>

        {/* Score Overview Card */}
        <Card style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "1.5rem" }}>
          <div>
            <div style={{ fontSize: TOKENS.typography.sizes.sm, color: TOKENS.colors.textSecondary, fontWeight: 500 }}>
              Overall Technical Score
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem", marginTop: "0.25rem" }}>
              <span style={{ fontSize: "2.5rem", fontWeight: 700, color: TOKENS.colors.textPrimary }}>
                {overallScore !== null ? overallScore : "Evaluated"}
              </span>
              {overallScore !== null && (
                <span style={{ fontSize: TOKENS.typography.sizes.lg, color: TOKENS.colors.textMuted }}>
                  / 10
                </span>
              )}
            </div>
            <div style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textSecondary, marginTop: "0.25rem" }}>
              Based on {turns.length} technical evaluation turns across {sessionInfo?.domain} subtopics.
            </div>
          </div>

          <div style={{ display: "flex", gap: "1.5rem" }}>
            <div style={{ textAlign: "center", padding: "0.75rem 1.25rem", backgroundColor: TOKENS.colors.surfaceSubdued, borderRadius: TOKENS.radii.md }}>
              <div style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textMuted }}>Turns Answered</div>
              <div style={{ fontSize: TOKENS.typography.sizes.xl, fontWeight: 700, color: TOKENS.colors.textPrimary }}>{turns.length}</div>
            </div>
            <div style={{ textAlign: "center", padding: "0.75rem 1.25rem", backgroundColor: TOKENS.colors.surfaceSubdued, borderRadius: TOKENS.radii.md }}>
              <div style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textMuted }}>Peak Difficulty</div>
              <div style={{ fontSize: TOKENS.typography.sizes.xl, fontWeight: 700, color: TOKENS.colors.textPrimary }}>{currentDifficulty}</div>
            </div>
          </div>
        </Card>

        {/* Performance Summary Feedback Items (Strengths, Gaps, Info) */}
        {summaryItems.length > 0 && (
          <div>
            <h2 style={{ fontSize: TOKENS.typography.sizes.lg, fontWeight: 600, color: TOKENS.colors.textPrimary, marginBottom: "1rem" }}>
              Performance Analysis & Subtopic Insights
            </h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem" }}>
              {summaryItems.map((item, idx) => {
                const isStrength = item.category === "strength";
                const isGap = item.category === "gap";

                const config = isStrength
                  ? { bg: TOKENS.colors.successBg, border: "#bbf7d0", text: TOKENS.colors.successText, icon: CheckCircle2 }
                  : isGap
                  ? { bg: TOKENS.colors.warningBg, border: "#fde68a", text: TOKENS.colors.warningText, icon: AlertTriangle }
                  : { bg: TOKENS.colors.infoBg, border: "#bae6fd", text: TOKENS.colors.infoText, icon: Info };

                const IconComp = config.icon;

                return (
                  <Card
                    key={idx}
                    style={{
                      borderLeft: `4px solid ${config.text}`,
                      padding: "1.25rem",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
                      <span style={{ color: config.text }}>
                        <IconComp size={18} />
                      </span>
                      <h3 style={{ fontSize: TOKENS.typography.sizes.sm, fontWeight: 600, color: TOKENS.colors.textPrimary, margin: 0 }}>
                        {stripEmojis(item.title)}
                      </h3>
                    </div>
                    <p style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textSecondary, lineHeight: 1.5, margin: 0 }}>
                      {stripEmojis(item.text)}
                    </p>
                  </Card>
                );
              })}
            </div>
          </div>
        )}

        {/* Turn-by-Turn Question Breakdown */}
        <div>
          <h2 style={{ fontSize: TOKENS.typography.sizes.lg, fontWeight: 600, color: TOKENS.colors.textPrimary, marginBottom: "1rem" }}>
            Question & Answer Breakdown
          </h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {turns.map((turn) => (
              <Card key={turn.turn_number} style={{ padding: "1.25rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <span style={{ fontWeight: 600, fontSize: TOKENS.typography.sizes.sm, color: TOKENS.colors.textPrimary }}>
                      Question {turn.turn_number}
                    </span>
                    {turn.subtopic && <Badge variant="neutral">{turn.subtopic}</Badge>}
                  </div>
                  <FeedbackBadge
                    classification={turn.answer_classification}
                    score={turn.score}
                  />
                </div>

                <div
                  style={{
                    backgroundColor: TOKENS.colors.surfaceSubdued,
                    padding: "0.75rem 1rem",
                    borderRadius: TOKENS.radii.md,
                    fontSize: TOKENS.typography.sizes.sm,
                    color: TOKENS.colors.textPrimary,
                    marginBottom: "0.75rem",
                    borderLeft: `3px solid ${TOKENS.colors.accent}`,
                  }}
                >
                  {stripEmojis(turn.question_text)}
                </div>

                <div style={{ padding: "0 0.25rem" }}>
                  <div style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textMuted, marginBottom: "0.25rem" }}>
                    Candidate Answer:
                  </div>
                  <div style={{ fontSize: TOKENS.typography.sizes.sm, color: TOKENS.colors.textSecondary, whiteSpace: "pre-wrap" }}>
                    {turn.candidate_answer || "(No response recorded)"}
                  </div>
                  {turn.justification && (
                    <div
                      style={{
                        marginTop: "0.5rem",
                        padding: "0.5rem 0.75rem",
                        borderRadius: TOKENS.radii.sm,
                        backgroundColor: "#F8FAFC",
                        border: `1px solid ${TOKENS.colors.border}`,
                        fontSize: TOKENS.typography.sizes.xs,
                        color: TOKENS.colors.textMuted,
                      }}
                    >
                      <span style={{ fontWeight: 500 }}>Evaluator Notes:</span> {stripEmojis(turn.justification)}
                    </div>
                  )}
                </div>
              </Card>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ==========================================
  // IN-PROGRESS INTERVIEW ROOM VIEW
  // ==========================================
  return (
    <div style={{ display: "flex", gap: "1.5rem", position: "relative" }}>
      {/* Rate Limit Banner */}
      {rateLimitCountdown !== null && (
        <div
          style={{
            position: "fixed",
            top: "5rem",
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 40,
            backgroundColor: TOKENS.colors.warningBg,
            color: TOKENS.colors.warningText,
            border: "1px solid #fde68a",
            padding: "0.75rem 1.25rem",
            borderRadius: TOKENS.radii.md,
            boxShadow: TOKENS.shadows.md,
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            fontSize: TOKENS.typography.sizes.sm,
            fontWeight: 500,
          }}
          role="alert"
        >
          <Clock size={16} />
          <span>Rate limit reached. Please wait {rateLimitCountdown} seconds before sending your next answer.</span>
        </div>
      )}

      {/* Main Chat Column */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, gap: "1rem" }}>
        {/* Chat Stream Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            paddingBottom: "0.5rem",
            borderBottom: `1px solid ${TOKENS.colors.border}`,
          }}
        >
          <div>
            <h2 style={{ fontSize: TOKENS.typography.sizes.lg, fontWeight: 600, color: TOKENS.colors.textPrimary, margin: 0 }}>
              {sessionInfo?.domain || "Technical"} Interview
            </h2>
            <div style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textMuted, marginTop: "0.2rem" }}>
              Turn {turns.length + 1} &bull; Adaptive Difficulty
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowEndModal(true)}
            style={{ color: TOKENS.colors.dangerText, borderColor: "#fca5a5" }}
          >
            <Square size={14} /> End Interview
          </Button>
        </div>

        {/* Conversation Thread */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "1.25rem",
            minHeight: "400px",
            paddingBottom: "1rem",
          }}
          aria-live="polite"
        >
          {/* Historical Turns */}
          {turns.map((turn) => (
            <React.Fragment key={turn.turn_number}>
              {/* Interviewer Question Bubble (Left) */}
              <div style={{ display: "flex", justifyContent: "flex-start" }}>
                <div
                  style={{
                    maxWidth: "85%",
                    backgroundColor: TOKENS.colors.surface,
                    border: `1px solid ${TOKENS.colors.border}`,
                    borderRadius: TOKENS.radii.lg,
                    padding: "1rem 1.25rem",
                    boxShadow: TOKENS.shadows.sm,
                  }}
                >
                  <div style={{ fontSize: TOKENS.typography.sizes.xs, fontWeight: 600, color: "#0369a1", marginBottom: "0.25rem" }}>
                    Interviewer &bull; Q{turn.turn_number}
                  </div>
                  <div style={{ fontSize: TOKENS.typography.sizes.base, color: TOKENS.colors.textPrimary, lineHeight: 1.5 }}>
                    {stripEmojis(turn.question_text)}
                  </div>
                </div>
              </div>

              {/* Candidate Answer Bubble (Right) */}
              {turn.candidate_answer && (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "0.375rem" }}>
                  <div
                    style={{
                      maxWidth: "85%",
                      backgroundColor: TOKENS.colors.surfaceSubdued,
                      border: `1px solid ${TOKENS.colors.border}`,
                      borderRadius: TOKENS.radii.lg,
                      padding: "1rem 1.25rem",
                    }}
                  >
                    <div style={{ fontSize: TOKENS.typography.sizes.xs, fontWeight: 600, color: TOKENS.colors.textSecondary, marginBottom: "0.25rem", textAlign: "right" }}>
                      You
                    </div>
                    <div style={{ fontSize: TOKENS.typography.sizes.base, color: TOKENS.colors.textPrimary, lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
                      {turn.candidate_answer}
                    </div>
                  </div>

                  {/* Feedback Badge on Answer */}
                  <FeedbackBadge
                    classification={turn.answer_classification}
                    score={turn.score}
                  />
                </div>
              )}
            </React.Fragment>
          ))}

          {/* Current Pending Question */}
          {pendingQuestion && (
            <div style={{ display: "flex", justifyContent: "flex-start" }}>
              <div
                style={{
                  maxWidth: "85%",
                  backgroundColor: TOKENS.colors.surface,
                  border: `1px solid ${TOKENS.colors.border}`,
                  borderRadius: TOKENS.radii.lg,
                  padding: "1rem 1.25rem",
                  boxShadow: TOKENS.shadows.sm,
                }}
              >
                <div style={{ fontSize: TOKENS.typography.sizes.xs, fontWeight: 600, color: "#0369a1", marginBottom: "0.25rem" }}>
                  Interviewer &bull; Q{turns.length + 1}
                </div>
                <div style={{ fontSize: TOKENS.typography.sizes.base, color: TOKENS.colors.textPrimary, lineHeight: 1.5 }}>
                  {stripEmojis(pendingQuestion)}
                </div>
              </div>
            </div>
          )}

          {/* Live Streaming / Processing Indicator */}
          {isSubmitting && (
            <div style={{ display: "flex", justifyContent: "flex-start", alignItems: "center", gap: "0.75rem", padding: "0.5rem" }}>
              <Spinner size="sm" />
              <span style={{ fontSize: TOKENS.typography.sizes.sm, color: TOKENS.colors.textMuted }}>
                {streamStatus?.message || "Interviewer is evaluating your response..."}
              </span>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Candidate Answer Input Box */}
        <Card style={{ padding: "1rem", marginTop: "auto" }}>
          <div style={{ position: "relative" }}>
            <textarea
              ref={textareaRef}
              rows={3}
              value={answerInput}
              onChange={(e) => setAnswerInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isSubmitting || rateLimitCountdown !== null}
              placeholder="Type your answer here... (Press Enter to send, Shift+Enter for newline)"
              style={{
                width: "100%",
                padding: "0.75rem 1rem",
                paddingRight: "5rem",
                fontSize: TOKENS.typography.sizes.base,
                borderRadius: TOKENS.radii.md,
                border: `1px solid ${TOKENS.colors.border}`,
                backgroundColor: TOKENS.colors.surface,
                color: TOKENS.colors.textPrimary,
                fontFamily: "inherit",
                resize: "vertical",
              }}
              className="focus:outline-none focus:border-[#46c4f6] focus:ring-1 focus:ring-[#46c4f6]"
              aria-label="Candidate answer input"
            />
            <div style={{ position: "absolute", bottom: "0.75rem", right: "0.75rem" }}>
              <Button
                variant="primary"
                size="sm"
                onClick={handleSubmitAnswer}
                disabled={!answerInput.trim() || isSubmitting || rateLimitCountdown !== null}
                isLoading={isSubmitting}
              >
                Send <Send size={14} />
              </Button>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "0.5rem" }}>
            <span style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textMuted }}>
              Type "quit" to conclude session early.
            </span>
            <span style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textMuted }}>
              {answerInput.length} characters
            </span>
          </div>
        </Card>
      </div>

      {/* Slim Side Panel (Desktop) */}
      <aside
        style={{
          width: "280px",
          display: "flex",
          flexDirection: "column",
          gap: "1rem",
          flexShrink: 0,
        }}
        className="hidden lg:flex"
      >
        {/* Session Status Card */}
        <Card style={{ padding: "1.25rem" }}>
          <h3 style={{ fontSize: TOKENS.typography.sizes.sm, fontWeight: 600, color: TOKENS.colors.textPrimary, margin: "0 0 1rem 0" }}>
            Session Monitor
          </h3>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textMuted }}>Elapsed Time</span>
              <span style={{ fontSize: TOKENS.typography.sizes.sm, fontWeight: 600, color: TOKENS.colors.textPrimary }}>
                {formatTimer(secondsElapsed)}
              </span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textMuted }}>Question Number</span>
              <span style={{ fontSize: TOKENS.typography.sizes.sm, fontWeight: 600, color: TOKENS.colors.textPrimary }}>
                {turns.length + 1}
              </span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textMuted }}>Difficulty</span>
              <Badge variant="accent">{currentDifficulty}</Badge>
            </div>

            {turns.length > 0 && turns[turns.length - 1].answer_classification && (
              <div style={{ paddingTop: "0.5rem", borderTop: `1px solid ${TOKENS.colors.border}` }}>
                <div style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textMuted, marginBottom: "0.375rem" }}>
                  Latest Feedback:
                </div>
                <FeedbackBadge
                  classification={turns[turns.length - 1].answer_classification}
                  score={turns[turns.length - 1].score}
                />
              </div>
            )}
          </div>
        </Card>

        {/* Quick Tips */}
        <Card subdued style={{ padding: "1.25rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
            <HelpCircle size={16} />
            <h4 style={{ fontSize: TOKENS.typography.sizes.xs, fontWeight: 600, margin: 0, color: TOKENS.colors.textPrimary }}>
              Tip for this question
            </h4>
          </div>
          <p style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textSecondary, lineHeight: 1.4, margin: 0 }}>
            Focus on core architectural trade-offs. The model detects vague phrases and will drill deeper into technical specifics.
          </p>
        </Card>
      </aside>

      {/* Confirmation Modal for Ending Interview */}
      <Modal
        isOpen={showEndModal}
        onClose={() => setShowEndModal(false)}
        title="End Interview Session?"
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setShowEndModal(false)}>
              Continue Interview
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={handleEndInterview}
              isLoading={isEnding}
            >
              End and Finalize Score
            </Button>
          </>
        }
      >
        <p style={{ margin: 0, fontSize: TOKENS.typography.sizes.sm, color: TOKENS.colors.textSecondary }}>
          Ending the interview will finalize your technical score based on the questions completed so far ({turns.length} turns). You will be able to review the full feedback report immediately.
        </p>
      </Modal>
    </div>
  );
};
