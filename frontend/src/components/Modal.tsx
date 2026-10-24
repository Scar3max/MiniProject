import React, { useEffect } from "react";
import { X } from "lucide-react";
import { TOKENS } from "../tokens";

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children, footer }) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 50,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "rgba(15, 23, 42, 0.4)",
        padding: "1rem",
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div
        style={{
          backgroundColor: TOKENS.colors.surface,
          borderRadius: TOKENS.radii.lg,
          border: `1px solid ${TOKENS.colors.border}`,
          boxShadow: TOKENS.shadows.lg,
          maxWidth: "500px",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "1rem 1.25rem",
            borderBottom: `1px solid ${TOKENS.colors.border}`,
          }}
        >
          <h2
            id="modal-title"
            style={{
              fontSize: TOKENS.typography.sizes.lg,
              fontWeight: 600,
              color: TOKENS.colors.textPrimary,
              margin: 0,
            }}
          >
            {title}
          </h2>
          <button
            onClick={onClose}
            aria-label="Close modal"
            style={{
              background: "transparent",
              border: "none",
              color: TOKENS.colors.textSecondary,
              cursor: "pointer",
              padding: "0.25rem",
              borderRadius: TOKENS.radii.sm,
              display: "flex",
              alignItems: "center",
            }}
          >
            <X size={18} />
          </button>
        </div>

        <div style={{ padding: "1.25rem", color: TOKENS.colors.textPrimary, lineHeight: 1.6 }}>
          {children}
        </div>

        {footer && (
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              gap: "0.75rem",
              padding: "0.75rem 1.25rem",
              backgroundColor: TOKENS.colors.surfaceSubdued,
              borderTop: `1px solid ${TOKENS.colors.border}`,
            }}
          >
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};
