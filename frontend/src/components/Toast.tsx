import React, { createContext, useContext, useState, useCallback } from "react";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";
import { TOKENS } from "../tokens";

export type ToastType = "success" | "error" | "info" | "warning";

export interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
  duration?: number;
}

interface ToastContextValue {
  showToast: (message: string, type?: ToastType, duration?: number) => void;
  showError: (message: string) => void;
  showSuccess: (message: string) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(
    (message: string, type: ToastType = "info", duration = 4000) => {
      const id = Math.random().toString(36).substring(2, 9);
      setToasts((prev) => [...prev, { id, type, message, duration }]);
      if (duration > 0) {
        setTimeout(() => removeToast(id), duration);
      }
    },
    [removeToast]
  );

  const showError = useCallback(
    (message: string) => showToast(message, "error", 6000),
    [showToast]
  );

  const showSuccess = useCallback(
    (message: string) => showToast(message, "success", 4000),
    [showToast]
  );

  return (
    <ToastContext.Provider value={{ showToast, showError, showSuccess }}>
      {children}
      <div
        style={{
          position: "fixed",
          bottom: "1.5rem",
          right: "1.5rem",
          zIndex: 100,
          display: "flex",
          flexDirection: "column",
          gap: "0.5rem",
          maxWidth: "400px",
          width: "100%",
          pointerEvents: "none",
        }}
        aria-live="polite"
      >
        {toasts.map((toast) => {
          const config = {
            success: { bg: TOKENS.colors.successBg, color: TOKENS.colors.successText, border: "#86efac", icon: CheckCircle2 },
            error: { bg: TOKENS.colors.dangerBg, color: TOKENS.colors.dangerText, border: "#fca5a5", icon: AlertCircle },
            warning: { bg: TOKENS.colors.warningBg, color: TOKENS.colors.warningText, border: "#fde68a", icon: AlertCircle },
            info: { bg: TOKENS.colors.infoBg, color: TOKENS.colors.infoText, border: "#7dd3fc", icon: Info },
          }[toast.type];

          const IconComponent = config.icon;

          return (
            <div
              key={toast.id}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "0.75rem",
                padding: "0.75rem 1rem",
                backgroundColor: config.bg,
                color: config.color,
                border: `1px solid ${config.border}`,
                borderRadius: TOKENS.radii.md,
                boxShadow: TOKENS.shadows.md,
                pointerEvents: "auto",
                fontSize: TOKENS.typography.sizes.sm,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <IconComponent size={16} />
                <span>{toast.message}</span>
              </div>
              <button
                onClick={() => removeToast(toast.id)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "currentColor",
                  cursor: "pointer",
                  padding: "2px",
                  display: "flex",
                }}
                aria-label="Dismiss alert"
              >
                <X size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
};

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}
