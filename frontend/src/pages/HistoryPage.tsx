import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { History as HistoryIcon, ArrowRight } from "lucide-react";
import { api } from "../services/apiClient";

import { Card } from "../components/Card";
import { Input } from "../components/Input";
import { Badge } from "../components/Badge";
import { Button } from "../components/Button";
import { Table } from "../components/Table";
import type { Column } from "../components/Table";
import { EmptyState } from "../components/EmptyState";
import { useToast } from "../components/Toast";
import { TOKENS } from "../tokens";

export interface SessionRow {
  session_id: number;
  domain: string;
  started_at?: string | null;
  ended_at?: string | null;
  overall_score?: number | null;
  status?: string;
}

export const HistoryPage: React.FC = () => {
  const { showError } = useToast();
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedDomain, setSelectedDomain] = useState<string>("all");

  const fetchHistory = async () => {
    setIsLoading(true);
    try {
      const res: any = await api.getHistory({
        search: searchTerm.trim() || undefined,
        domain: selectedDomain !== "all" ? selectedDomain : undefined,
      });
      const sessionsList = Array.isArray(res) ? res : (res?.sessions || []);
      setSessions(sessionsList);
    } catch {
      showError("Could not retrieve interview history.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchHistory();
    }, 250);
    return () => clearTimeout(timer);
  }, [searchTerm, selectedDomain]);

  const uniqueDomains = Array.from(new Set(sessions.map((s) => s.domain).filter(Boolean)));

  const columns: Column<SessionRow>[] = [
    {
      header: "Domain",
      cell: (row) => (
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Badge variant="accent">{row.domain}</Badge>
        </div>
      ),
    },
    {
      header: "Date & Time",
      cell: (row) => (
        <span style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textSecondary }}>
          {row.started_at ? new Date(row.started_at).toLocaleString() : "—"}
        </span>
      ),
    },
    {
      header: "Status",
      cell: (row) => {
        const isDone = row.ended_at !== null && row.ended_at !== undefined;
        return isDone ? (
          <Badge variant="success">Completed</Badge>
        ) : (
          <Badge variant="warning">In Progress</Badge>
        );
      },
    },
    {
      header: "Score",
      cell: (row) => {
        if (row.overall_score === null || row.overall_score === undefined) {
          return <span style={{ color: TOKENS.colors.textMuted }}>—</span>;
        }
        const score = Math.round(row.overall_score * 10) / 10;
        const variant = score >= 7 ? "success" : score >= 5 ? "warning" : "danger";
        return <Badge variant={variant}>{score} / 10</Badge>;
      },
    },
    {
      header: "Actions",
      cell: (row) => (
        <Link to={`/interview/${row.session_id}`} style={{ textDecoration: "none" }}>
          <Button variant="ghost" size="sm">
            View Details <ArrowRight size={14} />
          </Button>
        </Link>
      ),
      width: "120px",
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <div>
        <h1
          style={{
            fontSize: TOKENS.typography.sizes["2xl"],
            fontWeight: 700,
            color: TOKENS.colors.textPrimary,
            margin: 0,
            letterSpacing: "-0.02em",
          }}
        >
          Interview History
        </h1>
        <p style={{ fontSize: TOKENS.typography.sizes.sm, color: TOKENS.colors.textSecondary, marginTop: "0.25rem" }}>
          Review your past technical interview sessions, scores, and feedback
        </p>
      </div>

      {/* Search and Domain Pill Filters */}
      <Card style={{ padding: "1rem" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div style={{ maxWidth: "400px" }}>
            <Input
              placeholder="Search by domain name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          {uniqueDomains.length > 0 && (
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
              <span style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textMuted, marginRight: "0.25rem" }}>
                Filter:
              </span>
              <button
                type="button"
                onClick={() => setSelectedDomain("all")}
                style={{
                  padding: "0.25rem 0.75rem",
                  fontSize: TOKENS.typography.sizes.xs,
                  fontWeight: selectedDomain === "all" ? 600 : 500,
                  borderRadius: TOKENS.radii.full,
                  border: `1px solid ${selectedDomain === "all" ? TOKENS.colors.accent : TOKENS.colors.border}`,
                  backgroundColor: selectedDomain === "all" ? TOKENS.colors.accentLight : TOKENS.colors.surface,
                  color: selectedDomain === "all" ? "#0369a1" : TOKENS.colors.textSecondary,
                  cursor: "pointer",
                }}
              >
                All Domains
              </button>
              {uniqueDomains.map((dom) => (
                <button
                  key={dom}
                  type="button"
                  onClick={() => setSelectedDomain(dom)}
                  style={{
                    padding: "0.25rem 0.75rem",
                    fontSize: TOKENS.typography.sizes.xs,
                    fontWeight: selectedDomain === dom ? 600 : 500,
                    borderRadius: TOKENS.radii.full,
                    border: `1px solid ${selectedDomain === dom ? TOKENS.colors.accent : TOKENS.colors.border}`,
                    backgroundColor: selectedDomain === dom ? TOKENS.colors.accentLight : TOKENS.colors.surface,
                    color: selectedDomain === dom ? "#0369a1" : TOKENS.colors.textSecondary,
                    cursor: "pointer",
                  }}
                >
                  {dom}
                </button>
              ))}
            </div>
          )}
        </div>
      </Card>

      {/* History Table */}
      {sessions.length === 0 && !isLoading ? (
        <EmptyState
          icon={<HistoryIcon size={24} />}
          title="No interview history found"
          description={searchTerm ? "No sessions match your search query." : "You have not completed any interview sessions yet. Start one from the dashboard."}
          actionLabel="Start New Interview"
          onAction={() => window.location.assign("/")}
        />
      ) : (
        <Table
          columns={columns}
          data={sessions}
          keyExtractor={(row) => row.session_id}
          isLoading={isLoading}
        />
      )}
    </div>
  );
};
