import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Sparkles, ArrowRight, UserCheck, AlertCircle } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { TOKENS } from "../tokens";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { ApiError } from "../services/apiClient";

export const AuthPage: React.FC<{ initialMode?: "login" | "register" }> = ({
  initialMode = "login",
}) => {
  const [mode, setMode] = useState<"login" | "register">(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login, register, loginAsGuest } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as any)?.from?.pathname || "/";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      if (mode === "login") {
        await login({ email, password });
        navigate(from, { replace: true });
      } else {
        await register({ email, password, full_name: fullName });
        // Redirect to onboarding for new registered users
        navigate("/onboarding", { replace: true });
      }
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError(err?.message || "An unexpected error occurred. Please check your credentials.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGuestLogin = async () => {
    setError(null);
    setIsSubmitting(true);
    try {
      await loginAsGuest();
      navigate("/", { replace: true });
    } catch (err: any) {
      setError(err?.message || "Could not start guest session.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: TOKENS.colors.background,
        padding: "1.5rem",
      }}
    >
      <div style={{ maxWidth: "440px", width: "100%" }}>
        {/* Brand Header */}
        <div style={{ textAlign: "center", marginBottom: "2rem" }}>
          <div
            style={{
              width: "3rem",
              height: "3rem",
              borderRadius: TOKENS.radii.lg,
              backgroundColor: TOKENS.colors.textPrimary,
              color: TOKENS.colors.accent,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: "1rem",
            }}
          >
            <Sparkles size={24} />
          </div>
          <h1
            style={{
              fontSize: TOKENS.typography.sizes["2xl"],
              fontWeight: 700,
              color: TOKENS.colors.textPrimary,
              margin: "0 0 0.5rem 0",
              letterSpacing: "-0.02em",
            }}
          >
            Bekon Interview
          </h1>
          <p style={{ fontSize: TOKENS.typography.sizes.sm, color: TOKENS.colors.textSecondary, margin: 0 }}>
            Adaptive technical interviews powered by hybrid intelligence
          </p>
        </div>

        {/* Auth Card */}
        <Card>
          {/* Mode Switcher Tabs */}
          <div
            style={{
              display: "flex",
              borderBottom: `1px solid ${TOKENS.colors.border}`,
              marginBottom: "1.5rem",
            }}
          >
            <button
              type="button"
              onClick={() => {
                setMode("login");
                setError(null);
              }}
              style={{
                flex: 1,
                padding: "0.75rem",
                textAlign: "center",
                fontWeight: mode === "login" ? 600 : 500,
                color: mode === "login" ? TOKENS.colors.textPrimary : TOKENS.colors.textMuted,
                borderBottom: `2px solid ${mode === "login" ? TOKENS.colors.accent : "transparent"}`,
                background: "transparent",
                borderTop: "none",
                borderLeft: "none",
                borderRight: "none",
                cursor: "pointer",
              }}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("register");
                setError(null);
              }}
              style={{
                flex: 1,
                padding: "0.75rem",
                textAlign: "center",
                fontWeight: mode === "register" ? 600 : 500,
                color: mode === "register" ? TOKENS.colors.textPrimary : TOKENS.colors.textMuted,
                borderBottom: `2px solid ${mode === "register" ? TOKENS.colors.accent : "transparent"}`,
                background: "transparent",
                borderTop: "none",
                borderLeft: "none",
                borderRight: "none",
                cursor: "pointer",
              }}
            >
              Create Account
            </button>
          </div>

          {error && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                padding: "0.75rem 1rem",
                backgroundColor: TOKENS.colors.dangerBg,
                color: TOKENS.colors.dangerText,
                borderRadius: TOKENS.radii.md,
                fontSize: TOKENS.typography.sizes.sm,
                marginBottom: "1.25rem",
                border: "1px solid #fecaca",
              }}
              role="alert"
            >
              <AlertCircle size={16} style={{ flexShrink: 0 }} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {mode === "register" && (
              <Input
                label="Full Name"
                placeholder="Jane Doe"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
              />
            )}

            <Input
              label="Email Address"
              type="email"
              placeholder="candidate@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />

            <Input
              label="Password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              helperText={mode === "register" ? "Must be at least 8 characters" : undefined}
            />

            <Button
              type="submit"
              variant="primary"
              size="lg"
              isLoading={isSubmitting}
              style={{ marginTop: "0.5rem", width: "100%" }}
            >
              {mode === "login" ? "Sign In" : "Register & Continue"}
              <ArrowRight size={16} />
            </Button>
          </form>

          {/* Divider */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              margin: "1.5rem 0",
              color: TOKENS.colors.textMuted,
              fontSize: TOKENS.typography.sizes.xs,
            }}
          >
            <div style={{ flex: 1, height: "1px", backgroundColor: TOKENS.colors.border }} />
            <span style={{ padding: "0 0.75rem" }}>or</span>
            <div style={{ flex: 1, height: "1px", backgroundColor: TOKENS.colors.border }} />
          </div>

          {/* One-Click Guest Access */}
          <Button
            type="button"
            variant="outline"
            size="md"
            onClick={handleGuestLogin}
            disabled={isSubmitting}
            style={{ width: "100%" }}
          >
            <UserCheck size={16} />
            Continue as Guest
          </Button>

          {/* Guest Explanation Note */}
          <p
            style={{
              fontSize: TOKENS.typography.sizes.xs,
              color: TOKENS.colors.textMuted,
              textAlign: "center",
              marginTop: "0.75rem",
              lineHeight: 1.4,
            }}
          >
            Guest sessions are preserved for 24 hours with full interview features and history. No password required.
          </p>
        </Card>
      </div>
    </div>
  );
};
