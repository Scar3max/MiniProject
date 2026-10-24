import React from "react";
import { Link } from "react-router-dom";
import { AlertCircle } from "lucide-react";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { TOKENS } from "../tokens";

export const NotFoundPage: React.FC = () => {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "60vh",
        textAlign: "center",
      }}
    >
      <Card style={{ maxWidth: "450px", padding: "2.5rem" }}>
        <div
          style={{
            width: "3rem",
            height: "3rem",
            borderRadius: "50%",
            backgroundColor: TOKENS.colors.surfaceSubdued,
            color: TOKENS.colors.textMuted,
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: "1rem",
            border: `1px solid ${TOKENS.colors.border}`,
          }}
        >
          <AlertCircle size={24} />
        </div>
        <h1
          style={{
            fontSize: TOKENS.typography.sizes.xl,
            fontWeight: 700,
            color: TOKENS.colors.textPrimary,
            margin: "0 0 0.5rem 0",
          }}
        >
          Page Not Found (404)
        </h1>
        <p
          style={{
            fontSize: TOKENS.typography.sizes.sm,
            color: TOKENS.colors.textSecondary,
            marginBottom: "1.5rem",
            lineHeight: 1.5,
          }}
        >
          The page or resource you requested could not be located.
        </p>
        <Link to="/" style={{ textDecoration: "none" }}>
          <Button variant="primary">Return to Dashboard</Button>
        </Link>
      </Card>
    </div>
  );
};
