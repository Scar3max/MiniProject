import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, ArrowRight, ArrowLeft } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/apiClient";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { Select } from "../components/Select";
import { Stepper } from "../components/Stepper";
import { useToast } from "../components/Toast";
import { TOKENS } from "../tokens";

export const OnboardingPage: React.FC = () => {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const { showSuccess, showError } = useToast();

  const [step, setStep] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form State
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [collegeOrg, setCollegeOrg] = useState("");
  const [yearExperience, setYearExperience] = useState("0-1");
  const [targetRole, setTargetRole] = useState("Software Engineer");
  const [preferredDomains, setPreferredDomains] = useState("Python Programming, Operating Systems");
  const [consentSaveSessions, setConsentSaveSessions] = useState(true);

  const steps = [
    { title: "Identity", description: "Name and background" },
    { title: "Preferences", description: "Target role & topics" },
    { title: "Privacy", description: "Data consent" },
  ];

  const handleNext = () => {
    if (step < steps.length - 1) {
      setStep((prev) => prev + 1);
    }
  };

  const handlePrev = () => {
    if (step > 0) {
      setStep((prev) => prev - 1);
    }
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      await api.updateProfile({
        full_name: fullName,
        college_org: collegeOrg,
        target_role: targetRole,
        year_experience: yearExperience,
        preferred_domains: preferredDomains.split(",").map((d) => d.trim()),
        preferred_difficulty: "adaptive",
        consent_save_sessions: consentSaveSessions,
      });

      await refreshUser();
      showSuccess("Profile preferences saved successfully.");
      navigate("/");
    } catch (err: any) {
      showError(err?.message || "Failed to update profile.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: "600px", margin: "2rem auto" }}>
      <div style={{ textAlign: "center", marginBottom: "2rem" }}>
        <h1
          style={{
            fontSize: TOKENS.typography.sizes["2xl"],
            fontWeight: 700,
            color: TOKENS.colors.textPrimary,
            margin: "0 0 0.5rem 0",
          }}
        >
          Candidate Profile Setup
        </h1>
        <p style={{ fontSize: TOKENS.typography.sizes.sm, color: TOKENS.colors.textSecondary, margin: 0 }}>
          Configure your interview preferences to tailor adaptive questions
        </p>
      </div>

      <Card>
        <Stepper steps={steps} currentStep={step} />

        {step === 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            <Input
              label="Full Name"
              placeholder="e.g. Alex Chen"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
            <Input
              label="College or Organisation"
              placeholder="e.g. University of Technology / Acme Corp"
              value={collegeOrg}
              onChange={(e) => setCollegeOrg(e.target.value)}
            />
            <Select
              label="Years of Experience"
              value={yearExperience}
              onChange={(e) => setYearExperience(e.target.value)}
              options={[
                { value: "student", label: "Current Student" },
                { value: "0-1", label: "0-1 years (Entry Level)" },
                { value: "1-3", label: "1-3 years (Junior)" },
                { value: "3-5", label: "3-5 years (Mid-Level)" },
                { value: "5+", label: "5+ years (Senior)" },
              ]}
            />
          </div>
        )}

        {step === 1 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            <Select
              label="Target Role"
              value={targetRole}
              onChange={(e) => setTargetRole(e.target.value)}
              options={[
                { value: "Software Engineer", label: "Software Engineer / Backend" },
                { value: "Full Stack Developer", label: "Full Stack Developer" },
                { value: "Machine Learning Engineer", label: "Machine Learning / AI Engineer" },
                { value: "Systems Engineer", label: "Systems / DevOps Engineer" },
              ]}
            />
            <Input
              label="Preferred Technical Domains (comma-separated)"
              placeholder="e.g. Python Programming, Machine Learning, Operating Systems"
              value={preferredDomains}
              onChange={(e) => setPreferredDomains(e.target.value)}
              helperText="You can also choose any arbitrary topic when starting an interview"
            />
          </div>
        )}

        {step === 2 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            <div
              style={{
                padding: "1rem",
                borderRadius: TOKENS.radii.md,
                backgroundColor: TOKENS.colors.surfaceSubdued,
                border: `1px solid ${TOKENS.colors.border}`,
              }}
            >
              <label
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "0.75rem",
                  cursor: "pointer",
                }}
              >
                <input
                  type="checkbox"
                  checked={consentSaveSessions}
                  onChange={(e) => setConsentSaveSessions(e.target.checked)}
                  style={{ marginTop: "0.25rem", width: "1rem", height: "1rem" }}
                />
                <div>
                  <div style={{ fontWeight: 600, fontSize: TOKENS.typography.sizes.sm, color: TOKENS.colors.textPrimary }}>
                    Consent to Save Session Transcripts
                  </div>
                  <div style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textSecondary, marginTop: "0.25rem", lineHeight: 1.4 }}>
                    Allows the system to save completed interview questions and responses to your personal history and calculate cohort statistics. If disabled, transcripts are retained only while the session is active.
                  </div>
                </div>
              </label>
            </div>
          </div>
        )}

        {/* Stepper Buttons */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginTop: "2rem",
            paddingTop: "1.5rem",
            borderTop: `1px solid ${TOKENS.colors.border}`,
          }}
        >
          {step > 0 ? (
            <Button variant="outline" onClick={handlePrev}>
              <ArrowLeft size={16} /> Previous
            </Button>
          ) : (
            <div />
          )}

          {step < steps.length - 1 ? (
            <Button variant="primary" onClick={handleNext}>
              Next Step <ArrowRight size={16} />
            </Button>
          ) : (
            <Button variant="secondary" onClick={handleSubmit} isLoading={isSubmitting}>
              <CheckCircle2 size={16} /> Complete Setup
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
};
