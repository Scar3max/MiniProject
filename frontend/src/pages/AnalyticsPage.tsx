import React, { useState, useEffect } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import {
  TrendingUp,
  Users,
} from "lucide-react";
import { api } from "../services/apiClient";
import { Card } from "../components/Card";
import { Badge } from "../components/Badge";
import { EmptyState } from "../components/EmptyState";
import { Spinner } from "../components/Spinner";
import { Tabs } from "../components/Tabs";
import { useToast } from "../components/Toast";
import { TOKENS, ACCENT_HEX } from "../tokens";

export const AnalyticsPage: React.FC = () => {
  const { showError } = useToast();
  const [activeTab, setActiveTab] = useState<string>("personal");
  const [isLoading, setIsLoading] = useState(true);

  // Analytics data
  const [summary, setSummary] = useState<any>(null);
  const [trends, setTrends] = useState<any>(null);
  const [topics, setTopics] = useState<any>(null);
  const [classifications, setClassifications] = useState<any>(null);
  const [cohort, setCohort] = useState<any>(null);

  useEffect(() => {
    async function loadAnalytics() {
      setIsLoading(true);
      try {
        const [sumRes, trRes, topRes, clsRes, cohRes] = await Promise.all([
          api.getAnalyticsSummary().catch(() => null),
          api.getTrends().catch(() => null),
          api.getTopics().catch(() => null),
          api.getClassifications().catch(() => null),
          api.getCohort().catch(() => null),
        ]);

        setSummary(sumRes);
        setTrends(trRes);
        setTopics(topRes);
        setClassifications(clsRes);
        setCohort(cohRes);
      } catch (err: any) {
        showError("Failed to fetch analytics data.");
      } finally {
        setIsLoading(false);
      }
    }
    loadAnalytics();
  }, [showError]);

  if (isLoading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "400px" }}>
        <Spinner size="lg" label="Computing technical analytics..." />
      </div>
    );
  }

  // Format trend points for Recharts
  const performanceTrendData = (trends?.sessions || [])
    .slice()
    .reverse()
    .map((s: any, idx: number) => ({
      index: idx + 1,
      name: `S${idx + 1} (${s.domain || "Gen"})`,
      score: s.overall_score !== null ? Math.round(s.overall_score * 10) / 10 : null,
      date: s.started_at ? new Date(s.started_at).toLocaleDateString() : "",
    }))
    .filter((d: any) => d.score !== null);

  // Format classification distribution for Recharts
  const classificationData = (classifications?.distribution || []).map((c: any) => ({
    name: c.category.replace(/_/g, " "),
    count: c.count,
    percentage: c.percentage,
  }));

  // Format topic performance for Recharts
  const topicData = (topics?.topics || []).map((t: any) => ({
    name: t.topic,
    avgScore: t.average_score !== null ? Math.round(t.average_score * 10) / 10 : 0,
    turns: t.turns_count,
  }));

  const hasPersonalData = performanceTrendData.length > 0 || (summary?.total_sessions || 0) > 0;
  const isCohortAvailable = cohort?.available === true;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
      {/* Page Title & Tab Selector */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
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
            Performance Analytics
          </h1>
          <p style={{ fontSize: TOKENS.typography.sizes.sm, color: TOKENS.colors.textSecondary, marginTop: "0.25rem" }}>
            Track your technical trajectory, topic strengths, and cohort benchmarks
          </p>
        </div>

        <Tabs
          tabs={[
            { id: "personal", label: "Personal Analytics", icon: <TrendingUp size={16} /> },
            { id: "cohort", label: "Cohort Benchmarks", icon: <Users size={16} /> },
          ]}
          activeTab={activeTab}
          onChange={setActiveTab}
        />
      </div>

      {activeTab === "personal" ? (
        <>
          {/* Summary KPI Cards */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "1.25rem",
            }}
          >
            <Card style={{ padding: "1.25rem" }}>
              <div style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textMuted, fontWeight: 500 }}>
                Total Sessions
              </div>
              <div style={{ fontSize: "2rem", fontWeight: 700, color: TOKENS.colors.textPrimary, marginTop: "0.25rem" }}>
                {summary?.total_sessions || 0}
              </div>
              <div style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textSecondary, marginTop: "0.25rem" }}>
                {summary?.stats?.total_answers || 0} evaluated questions
              </div>
            </Card>

            <Card style={{ padding: "1.25rem" }}>
              <div style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textMuted, fontWeight: 500 }}>
                Average Overall Score
              </div>
              <div style={{ fontSize: "2rem", fontWeight: 700, color: TOKENS.colors.textPrimary, marginTop: "0.25rem" }}>
                {summary?.avg_score !== null && summary?.avg_score !== undefined
                  ? `${Math.round(summary.avg_score * 10) / 10}`
                  : "—"}
                <span style={{ fontSize: TOKENS.typography.sizes.sm, color: TOKENS.colors.textMuted, fontWeight: 400 }}>
                  {" "}/ 10
                </span>
              </div>
              <div style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textSecondary, marginTop: "0.25rem" }}>
                Across all completed turns
              </div>
            </Card>

            <Card style={{ padding: "1.25rem" }}>
              <div style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textMuted, fontWeight: 500 }}>
                Strongest Topic
              </div>
              <div style={{ fontSize: TOKENS.typography.sizes.lg, fontWeight: 600, color: TOKENS.colors.textPrimary, marginTop: "0.5rem" }}>
                {summary?.strongest_topic || "In progress"}
              </div>
              <div style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.successText, marginTop: "0.25rem" }}>
                Highest evaluation score
              </div>
            </Card>

            <Card style={{ padding: "1.25rem" }}>
              <div style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textMuted, fontWeight: 500 }}>
                Focus Subtopic
              </div>
              <div style={{ fontSize: TOKENS.typography.sizes.lg, fontWeight: 600, color: TOKENS.colors.textPrimary, marginTop: "0.5rem" }}>
                {summary?.weakest_topic || "In progress"}
              </div>
              <div style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.warningText, marginTop: "0.25rem" }}>
                Recommended for practice
              </div>
            </Card>
          </div>

          {!hasPersonalData ? (
            <EmptyState
              icon={<TrendingUp size={24} />}
              title="No interview analytics yet"
              description="Complete your first technical interview to generate performance trend charts and topic breakdowns."
              actionLabel="Start New Interview"
              onAction={() => window.location.assign("/")}
            />
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(450px, 1fr))", gap: "1.5rem" }}>
              {/* Chart 1: Performance Trend */}
              <Card>
                <div style={{ marginBottom: "1rem" }}>
                  <h3 style={{ fontSize: TOKENS.typography.sizes.base, fontWeight: 600, color: TOKENS.colors.textPrimary, margin: 0 }}>
                    Score Progression Across Sessions
                  </h3>
                  <p style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textSecondary, margin: "0.25rem 0 0 0" }}>
                    Overall technical score (0–10) plotted by session
                  </p>
                </div>
                {performanceTrendData.length === 0 ? (
                  <div style={{ padding: "3rem 1rem", textAlign: "center", color: TOKENS.colors.textMuted }}>
                    Complete at least one session to render score trend.
                  </div>
                ) : (
                  <div style={{ width: "100%", height: 260 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={performanceTrendData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                        <XAxis dataKey="name" stroke="#64748B" fontSize={12} tickLine={false} />
                        <YAxis domain={[0, 10]} stroke="#64748B" fontSize={12} tickLine={false} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#FFFFFF",
                            border: "1px solid #E2E8F0",
                            borderRadius: "6px",
                            fontSize: "12px",
                          }}
                        />
                        <Line
                          type="monotone"
                          dataKey="score"
                          stroke={ACCENT_HEX}
                          strokeWidth={2.5}
                          dot={{ r: 4, fill: ACCENT_HEX }}
                          activeDot={{ r: 6 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </Card>

              {/* Chart 2: Answer Quality Distribution */}
              <Card>
                <div style={{ marginBottom: "1rem" }}>
                  <h3 style={{ fontSize: TOKENS.typography.sizes.base, fontWeight: 600, color: TOKENS.colors.textPrimary, margin: 0 }}>
                    Answer Quality Distribution
                  </h3>
                  <p style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textSecondary, margin: "0.25rem 0 0 0" }}>
                    Counts of classified responses across all turns
                  </p>
                </div>
                <div style={{ width: "100%", height: 260 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={classificationData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                      <XAxis dataKey="name" stroke="#64748B" fontSize={11} tickLine={false} />
                      <YAxis allowDecimals={false} stroke="#64748B" fontSize={12} tickLine={false} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#FFFFFF",
                          border: "1px solid #E2E8F0",
                          borderRadius: "6px",
                          fontSize: "12px",
                        }}
                      />
                      <Bar dataKey="count" fill={TOKENS.colors.textPrimary} radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>

              {/* Chart 3: Topic Performance Breakdown */}
              <Card style={{ gridColumn: "1 / -1" }}>
                <div style={{ marginBottom: "1rem" }}>
                  <h3 style={{ fontSize: TOKENS.typography.sizes.base, fontWeight: 600, color: TOKENS.colors.textPrimary, margin: 0 }}>
                    Technical Topic Mastery
                  </h3>
                  <p style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textSecondary, margin: "0.25rem 0 0 0" }}>
                    Average performance score per evaluated technical area
                  </p>
                </div>
                <div style={{ width: "100%", height: 240 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={topicData} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                      <XAxis type="number" domain={[0, 10]} stroke="#64748B" fontSize={12} />
                      <YAxis type="category" dataKey="name" stroke="#64748B" fontSize={12} tickLine={false} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#FFFFFF",
                          border: "1px solid #E2E8F0",
                          borderRadius: "6px",
                          fontSize: "12px",
                        }}
                      />
                      <Bar dataKey="avgScore" fill={ACCENT_HEX} radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </div>
          )}
        </>
      ) : (
        /* ================= Cohort Benchmarks View ================= */
        <div>
          {!isCohortAvailable ? (
            <Card style={{ padding: "3rem 1.5rem", textAlign: "center" }}>
              <div
                style={{
                  width: "3.5rem",
                  height: "3.5rem",
                  borderRadius: "50%",
                  backgroundColor: TOKENS.colors.surfaceSubdued,
                  color: TOKENS.colors.textMuted,
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: "1.25rem",
                  border: `1px solid ${TOKENS.colors.border}`,
                }}
              >
                <Users size={28} />
              </div>
              <h2
                style={{
                  fontSize: TOKENS.typography.sizes.lg,
                  fontWeight: 600,
                  color: TOKENS.colors.textPrimary,
                  margin: "0 0 0.5rem 0",
                }}
              >
                Cohort Analytics Unlocking Soon
              </h2>
              <p
                style={{
                  fontSize: TOKENS.typography.sizes.sm,
                  color: TOKENS.colors.textSecondary,
                  maxWidth: "460px",
                  margin: "0 auto 1.5rem auto",
                  lineHeight: 1.5,
                }}
              >
                {cohort?.message ||
                  `To protect privacy and compute statistically valid percentiles, cohort benchmarks require at least 5 distinct candidates (currently ${cohort?.total_candidates || 1}).`}
              </p>
              <Badge variant="neutral">Minimum threshold: 5 candidates</Badge>
            </Card>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
              {/* Cohort KPI Banner */}
              <Card style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem" }}>
                <div>
                  <div style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textMuted }}>Cohort Candidates</div>
                  <div style={{ fontSize: "1.75rem", fontWeight: 700, color: TOKENS.colors.textPrimary }}>
                    {cohort.summary?.total_candidates}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textMuted }}>Cohort Average Score</div>
                  <div style={{ fontSize: "1.75rem", fontWeight: 700, color: TOKENS.colors.textPrimary }}>
                    {cohort.summary?.cohort_avg_score} / 10
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textMuted }}>Easiest Topic</div>
                  <div style={{ fontSize: "1.25rem", fontWeight: 600, color: TOKENS.colors.successText }}>
                    {cohort.summary?.easiest_topic}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textMuted }}>Hardest Topic</div>
                  <div style={{ fontSize: "1.25rem", fontWeight: 600, color: TOKENS.colors.warningText }}>
                    {cohort.summary?.hardest_topic}
                  </div>
                </div>
              </Card>

              {/* Cohort Topic Difficulty & Time Trend Charts */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(450px, 1fr))", gap: "1.5rem" }}>
                <Card>
                  <h3 style={{ fontSize: TOKENS.typography.sizes.base, fontWeight: 600, color: TOKENS.colors.textPrimary, margin: "0 0 1rem 0" }}>
                    Cohort Topic Difficulty Benchmarks
                  </h3>
                  <div style={{ width: "100%", height: 260 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={cohort.topic_benchmarks || []} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                        <XAxis dataKey="subtopic" stroke="#64748B" fontSize={11} tickLine={false} />
                        <YAxis domain={[0, 10]} stroke="#64748B" fontSize={12} tickLine={false} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#FFFFFF",
                            border: "1px solid #E2E8F0",
                            borderRadius: "6px",
                            fontSize: "12px",
                          }}
                        />
                        <Bar dataKey="avg_score" fill={ACCENT_HEX} radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </Card>

                <Card>
                  <h3 style={{ fontSize: TOKENS.typography.sizes.base, fontWeight: 600, color: TOKENS.colors.textPrimary, margin: "0 0 1rem 0" }}>
                    Cohort Average Time Trend
                  </h3>
                  <div style={{ width: "100%", height: 260 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={cohort.time_trend || []} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                        <XAxis dataKey="date" stroke="#64748B" fontSize={11} tickLine={false} />
                        <YAxis domain={[0, 10]} stroke="#64748B" fontSize={12} tickLine={false} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#FFFFFF",
                            border: "1px solid #E2E8F0",
                            borderRadius: "6px",
                            fontSize: "12px",
                          }}
                        />
                        <Line type="monotone" dataKey="avg_overall_score" stroke={TOKENS.colors.textPrimary} strokeWidth={2} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
