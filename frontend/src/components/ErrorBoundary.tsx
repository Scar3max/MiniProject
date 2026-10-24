import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { TOKENS } from "../tokens";
import { Button } from "./Button";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public override state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught application error:", error, errorInfo);
  }

  public override render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: TOKENS.colors.background,
            padding: "2rem",
          }}
        >
          <div
            style={{
              maxWidth: "500px",
              width: "100%",
              backgroundColor: TOKENS.colors.surface,
              border: `1px solid ${TOKENS.colors.border}`,
              borderRadius: TOKENS.radii.lg,
              padding: "2.5rem",
              textAlign: "center",
              boxShadow: TOKENS.shadows.md,
            }}
          >
            <div
              style={{
                width: "3.5rem",
                height: "3.5rem",
                borderRadius: "50%",
                backgroundColor: TOKENS.colors.dangerBg,
                color: TOKENS.colors.dangerText,
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                marginBottom: "1.25rem",
              }}
            >
              <AlertCircle size={28} />
            </div>
            <h1
              style={{
                fontSize: TOKENS.typography.sizes.xl,
                fontWeight: 600,
                color: TOKENS.colors.textPrimary,
                margin: "0 0 0.5rem 0",
              }}
            >
              Something went wrong
            </h1>
            <p
              style={{
                fontSize: TOKENS.typography.sizes.sm,
                color: TOKENS.colors.textSecondary,
                margin: "0 0 1.5rem 0",
                lineHeight: 1.5,
              }}
            >
              {this.state.error?.message || "An unexpected application error occurred. You can safely retry or return home."}
            </p>
            <div style={{ display: "flex", gap: "0.75rem", justifyContent: "center" }}>
              <Button
                variant="outline"
                onClick={() => window.location.assign("/")}
              >
                Return to Dashboard
              </Button>
              <Button
                variant="primary"
                onClick={() => window.location.reload()}
              >
                <RefreshCw size={14} />
                Reload Page
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
