import React, { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  Terminal,
  Cpu,
  HardDrive,
  Database,
  Layers,
  Globe,
  BookOpen,
  ArrowRight,
  Play,
  Lightbulb,
  History,
  TrendingUp,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/apiClient";

import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { Badge } from "../components/Badge";
import { Spinner } from "../components/Spinner";
import { EmptyState } from "../components/EmptyState";
import { useToast } from "../components/Toast";
import { TOKENS } from "../tokens";

type DomainItem = {
  id: string;
  name: string;
  description: string;
};

export interface SessionItem {
  session_id: number;
  domain: string;
  started_at?: string | null;
  ended_at?: string | null;
  overall_score?: number | null;
  status?: string;
}

const DOMAIN_ICONS: Record<string, React.ReactNode> = {
  python: <Terminal size={20} />,
  "python programming": <Terminal size={20} />,
  "machine learning": <Cpu size={20} />,
  ml: <Cpu size={20} />,
  "operating systems": <HardDrive size={20} />,
  os: <HardDrive size={20} />,
  databases: <Database size={20} />,
  database: <Database size={20} />,
  "data structures": <Layers size={20} />,
  web: <Globe size={20} />,
};

function getDomainIcon(domainName: string): React.ReactNode {
  const norm = domainName.toLowerCase();
  for (const [key, icon] of Object.entries(DOMAIN_ICONS)) {
    if (norm.includes(key)) return icon;
  }
  return <BookOpen size={20} />;
}

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError } = useToast();

  const [domains, setDomains] = useState<DomainItem[]>([]);
  const [recentSessions, setRecentSessions] = useState<SessionItem[]>([]);
  const [customDomain, setCustomDomain] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isStarting, setIsStarting] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        const [domainsRes, historyRes] = await Promise.all([
          api.getDomains().catch(() => ({ domains: [] })),
          api.getHistory({ page_size: 3 }).catch(() => ({ sessions: [], total: 0 })),
        ]);

        const fetchedDomains = (domainsRes as any).domains || [
          { id: "python", name: "Python Programming", description: "Core data structures, generators, OOP, and memory management." },
          { id: "ml", name: "Machine Learning", description: "Supervised & unsupervised learning, evaluation metrics, and model tuning." },
          { id: "os", name: "Operating Systems", description: "Processes, threads, synchronization primitives, and virtual memory." },
          { id: "db", name: "Database Systems", description: "ACID properties, indexing strategies, normalization, and concurrency." },
        ];
        setDomains(fetchedDomains);
        const sessionsList = Array.isArray(historyRes) ? historyRes : (historyRes as any)?.sessions || [];
        setRecentSessions(sessionsList);
      } catch (err: any) {
        showError("Failed to load dashboard data.");
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, [showError]);

  const handleStartInterview = async (domain: string) => {
    if (!domain.trim()) return;
    setIsStarting(true);
    try {
      const res = await api.startInterview({ domain: domain.trim() });
      navigate(`/interview/${res.session_id}`);
    } catch (err: any) {
      showError(err?.message || "Could not initialize interview session.");
      setIsStarting(false);
    }
  };

  if (isLoading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "400px" }}>
        <Spinner size="lg" label="Loading dashboard..." />
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
      {/* Greeting and Quick Hero */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem" }}>
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
            Welcome, {user?.full_name || "Candidate"}
          </h1>
          <p style={{ fontSize: TOKENS.typography.sizes.sm, color: TOKENS.colors.textSecondary, marginTop: "0.25rem" }}>
            Select a domain to begin your adaptive technical interview.
          </p>
        </div>
        <Link to="/analytics" style={{ textDecoration: "none" }}>
          <Button variant="outline" size="sm">
            <TrendingUp size={16} /> View Performance Analytics
          </Button>
        </Link>
      </div>

      {/* Custom Domain Launch Card */}
      <Card style={{ backgroundColor: TOKENS.colors.surface }}>
        <h2
          style={{
            fontSize: TOKENS.typography.sizes.base,
            fontWeight: 600,
            color: TOKENS.colors.textPrimary,
            margin: "0 0 0.5rem 0",
          }}
        >
          Custom Technical Domain
        </h2>
        <p style={{ fontSize: TOKENS.typography.sizes.sm, color: TOKENS.colors.textSecondary, margin: "0 0 1rem 0" }}>
          Type any technical topic, library, or programming stack (e.g. "Distributed Systems", "Kubernetes", "Golang Concurrency")
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleStartInterview(customDomain);
          }}
          style={{ display: "flex", gap: "0.75rem", maxWidth: "600px" }}
        >
          <Input
            placeholder="Enter custom domain..."
            value={customDomain}
            onChange={(e) => setCustomDomain(e.target.value)}
          />
          <Button
            type="submit"
            variant="primary"
            isLoading={isStarting}
            disabled={!customDomain.trim() || isStarting}
            style={{ flexShrink: 0 }}
          >
            <Play size={16} /> Start
          </Button>
        </form>
      </Card>

      {/* Popular Domains Grid */}
      <div>
        <h2
          style={{
            fontSize: TOKENS.typography.sizes.lg,
            fontWeight: 600,
            color: TOKENS.colors.textPrimary,
            marginBottom: "1rem",
          }}
        >
          Popular Interview Domains
        </h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
            gap: "1.25rem",
          }}
        >
          {domains.map((dom) => (
            <Card
              key={dom.id || dom.name}
              style={{
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                padding: "1.25rem",
              }}
            >
              <div>
                <div
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: "2.5rem",
                    height: "2.5rem",
                    borderRadius: TOKENS.radii.md,
                    backgroundColor: TOKENS.colors.accentLight,
                    color: "#0369a1",
                    marginBottom: "1rem",
                  }}
                >
                  {getDomainIcon(dom.name)}
                </div>
                <h3
                  style={{
                    fontSize: TOKENS.typography.sizes.base,
                    fontWeight: 600,
                    color: TOKENS.colors.textPrimary,
                    margin: "0 0 0.5rem 0",
                  }}
                >
                  {dom.name}
                </h3>
                <p
                  style={{
                    fontSize: TOKENS.typography.sizes.xs,
                    color: TOKENS.colors.textSecondary,
                    lineHeight: 1.4,
                    margin: "0 0 1.25rem 0",
                  }}
                >
                  {dom.description}
                </p>
              </div>

              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleStartInterview(dom.name)}
                disabled={isStarting}
                style={{ width: "100%" }}
              >
                <Play size={14} /> Begin Interview
              </Button>
            </Card>
          ))}
        </div>
      </div>

      {/* Two Column Section: Recent Sessions + Quick Tips */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1.5rem" }}>
        {/* Recent Sessions */}
        <Card>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <h2
              style={{
                fontSize: TOKENS.typography.sizes.base,
                fontWeight: 600,
                color: TOKENS.colors.textPrimary,
                margin: 0,
              }}
            >
              Recent Sessions
            </h2>
            <Link to="/history" style={{ fontSize: TOKENS.typography.sizes.xs, color: "#0369a1", textDecoration: "none", fontWeight: 500 }}>
              View all
            </Link>
          </div>

          {recentSessions.length === 0 ? (
            <EmptyState
              icon={<History size={20} />}
              title="No recent sessions"
              description="Completed interview sessions and their breakdown will show up here."
            />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {recentSessions.map((sess) => (
                <div
                  key={sess.session_id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "0.75rem",
                    borderRadius: TOKENS.radii.md,
                    backgroundColor: TOKENS.colors.surfaceSubdued,
                    border: `1px solid ${TOKENS.colors.border}`,
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: TOKENS.typography.sizes.sm, color: TOKENS.colors.textPrimary }}>
                      {sess.domain}
                    </div>
                    <div style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textMuted }}>
                      {sess.started_at ? new Date(sess.started_at).toLocaleDateString() : "Recent"}
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                    {sess.overall_score !== null && sess.overall_score !== undefined ? (
                      <Badge variant="success">Score: {Math.round(sess.overall_score)}/10</Badge>
                    ) : (
                      <Badge variant="neutral">{sess.status || "In progress"}</Badge>
                    )}
                    <Link to={`/interview/${sess.session_id}`} style={{ color: TOKENS.colors.textSecondary }}>
                      <ArrowRight size={16} />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Quick Tips Card */}
        <Card subdued>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem", color: TOKENS.colors.textPrimary }}>
            <Lightbulb size={20} />
            <h2 style={{ fontSize: TOKENS.typography.sizes.base, fontWeight: 600, margin: 0 }}>
              Interview Quick Tips
            </h2>
          </div>
          <ul
            style={{
              fontSize: TOKENS.typography.sizes.sm,
              color: TOKENS.colors.textSecondary,
              paddingLeft: "1.25rem",
              margin: 0,
              display: "flex",
              flexDirection: "column",
              gap: "0.5rem",
              lineHeight: 1.5,
            }}
          >
            <li>State concrete mechanisms and technical definitions clearly before providing examples.</li>
            <li>If you are unsure about a subtopic, state your reasoning rather than giving evasive non-answers.</li>
            <li>The interviewer automatically adapts question depth based on your technical precision.</li>
            <li>Type "quit" or click "End Interview" at any turn to finalize your evaluation score.</li>
          </ul>
        </Card>
      </div>
    </div>
  );
};
