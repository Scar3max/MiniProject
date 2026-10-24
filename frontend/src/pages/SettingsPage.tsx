import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  User,
  KeyRound,
  Trash2,
  AlertTriangle,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/apiClient";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { Select } from "../components/Select";
import { Modal } from "../components/Modal";
import { useToast } from "../components/Toast";
import { TOKENS } from "../tokens";

export const SettingsPage: React.FC = () => {
  const { user, isGuest, logout, refreshUser } = useAuth();
  const navigate = useNavigate();
  const { showSuccess, showError } = useToast();

  // Profile State
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [collegeOrg, setCollegeOrg] = useState("");
  const [targetRole, setTargetRole] = useState("Software Engineer");
  const [yearExperience, setYearExperience] = useState("0-1");
  const [consentSaveSessions, setConsentSaveSessions] = useState(true);
  const [isSavingProfile, setIsSavingProfile] = useState(false);

  // Password State
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isUpdatingPassword, setIsUpdatingPassword] = useState(false);

  // Delete Data State
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirmationText, setDeleteConfirmationText] = useState("");
  const [isDeletingData, setIsDeletingData] = useState(false);

  useEffect(() => {
    async function loadProfile() {
      try {
        const res: any = await api.getProfile();
        if (res) {
          if (res.full_name) setFullName(res.full_name);
          if (res.college_org) setCollegeOrg(res.college_org);
          if (res.target_role) setTargetRole(res.target_role);
          if (res.year_experience) setYearExperience(String(res.year_experience));
          if (typeof res.consent_save_sessions === "boolean") {
            setConsentSaveSessions(res.consent_save_sessions);
          }
        }
      } catch {
        // Fallback to user object
      }
    }
    loadProfile();
  }, []);

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingProfile(true);
    try {
      await api.updateProfile({
        full_name: fullName,
        college_org: collegeOrg,
        target_role: targetRole,
        year_experience: yearExperience,
        consent_save_sessions: consentSaveSessions,
      });
      await refreshUser();
      showSuccess("Profile settings updated successfully.");
    } catch (err: any) {
      showError(err?.message || "Failed to update profile settings.");
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handleUpdatePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      showError("New passwords do not match.");
      return;
    }
    if (newPassword.length < 6) {
      showError("New password must be at least 6 characters.");
      return;
    }

    setIsUpdatingPassword(true);
    try {
      await api.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      showSuccess("Password changed successfully.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: any) {
      showError(err?.message || "Failed to change password.");
    } finally {
      setIsUpdatingPassword(false);
    }
  };

  const handleDeleteAllData = async () => {
    if (deleteConfirmationText.trim() !== "DELETE MY DATA") {
      showError("Please type 'DELETE MY DATA' exactly to confirm deletion.");
      return;
    }

    setIsDeletingData(true);
    try {
      await api.deleteData({ confirmation: "DELETE MY DATA" });
      await logout();
      showSuccess("All personal account and interview data has been permanently deleted.");
      navigate("/login", { replace: true });
    } catch (err: any) {
      showError(err?.message || "Failed to delete account data.");
      setIsDeletingData(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2rem", maxWidth: "800px" }}>
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
          Account & Privacy Settings
        </h1>
        <p style={{ fontSize: TOKENS.typography.sizes.sm, color: TOKENS.colors.textSecondary, marginTop: "0.25rem" }}>
          Manage your candidate profile, interview defaults, and data retention preferences
        </p>
      </div>

      {/* Profile Section */}
      <Card>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1.25rem" }}>
          <User size={20} />
          <h2 style={{ fontSize: TOKENS.typography.sizes.base, fontWeight: 600, color: TOKENS.colors.textPrimary, margin: 0 }}>
            Profile Defaults
          </h2>
        </div>

        <form onSubmit={handleSaveProfile} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <Input
              label="Full Name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Candidate Name"
            />
            <Input
              label="College or Organisation"
              value={collegeOrg}
              onChange={(e) => setCollegeOrg(e.target.value)}
              placeholder="University or Employer"
            />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <Select
              label="Target Role"
              value={targetRole}
              onChange={(e) => setTargetRole(e.target.value)}
              options={[
                { value: "Software Engineer", label: "Software Engineer" },
                { value: "Full Stack Developer", label: "Full Stack Developer" },
                { value: "Machine Learning Engineer", label: "Machine Learning Engineer" },
                { value: "Systems Engineer", label: "Systems / DevOps Engineer" },
              ]}
            />
            <Select
              label="Years of Experience"
              value={yearExperience}
              onChange={(e) => setYearExperience(e.target.value)}
              options={[
                { value: "student", label: "Current Student" },
                { value: "0-1", label: "0-1 years" },
                { value: "1-3", label: "1-3 years" },
                { value: "3-5", label: "3-5 years" },
                { value: "5+", label: "5+ years" },
              ]}
            />
          </div>

          {/* Data Consent Toggle */}
          <div
            style={{
              marginTop: "0.5rem",
              padding: "1rem",
              borderRadius: TOKENS.radii.md,
              backgroundColor: TOKENS.colors.surfaceSubdued,
              border: `1px solid ${TOKENS.colors.border}`,
            }}
          >
            <label style={{ display: "flex", alignItems: "flex-start", gap: "0.75rem", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={consentSaveSessions}
                onChange={(e) => setConsentSaveSessions(e.target.checked)}
                style={{ marginTop: "0.25rem", width: "1rem", height: "1rem" }}
              />
              <div>
                <div style={{ fontWeight: 600, fontSize: TOKENS.typography.sizes.sm, color: TOKENS.colors.textPrimary }}>
                  Save Session Transcripts and Cohort Benchmarks
                </div>
                <div style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textSecondary, marginTop: "0.25rem", lineHeight: 1.4 }}>
                  When enabled, completed interview sessions are saved to your personal history and aggregate metrics. When disabled, transcripts are retained only for the duration of the active interview and excluded from history.
                </div>
              </div>
            </label>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "0.5rem" }}>
            <Button type="submit" variant="primary" size="sm" isLoading={isSavingProfile}>
              Save Profile Changes
            </Button>
          </div>
        </form>
      </Card>

      {/* Password Change Section (Non-Guests) */}
      {!isGuest && (
        <Card>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1.25rem" }}>
            <KeyRound size={20} />
            <h2 style={{ fontSize: TOKENS.typography.sizes.base, fontWeight: 600, color: TOKENS.colors.textPrimary, margin: 0 }}>
              Change Password
            </h2>
          </div>

          <form onSubmit={handleUpdatePassword} style={{ display: "flex", flexDirection: "column", gap: "1rem", maxWidth: "450px" }}>
            <Input
              label="Current Password"
              type="password"
              placeholder="••••••••"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
            <Input
              label="New Password"
              type="password"
              placeholder="••••••••"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              helperText="Minimum 6 characters"
            />
            <Input
              label="Confirm New Password"
              type="password"
              placeholder="••••••••"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />

            <div>
              <Button type="submit" variant="outline" size="sm" isLoading={isUpdatingPassword}>
                Update Password
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* GDPR Right to Erasure / Delete Account Data */}
      <Card style={{ borderColor: "#fecaca" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem", color: TOKENS.colors.dangerText }}>
          <AlertTriangle size={20} />
          <h2 style={{ fontSize: TOKENS.typography.sizes.base, fontWeight: 600, margin: 0 }}>
            Delete Account and Personal Data
          </h2>
        </div>
        <p style={{ fontSize: TOKENS.typography.sizes.sm, color: TOKENS.colors.textSecondary, margin: "0 0 1.25rem 0", lineHeight: 1.5 }}>
          Permanently erase your candidate profile, authentication account, all interview sessions, questions, and scores from the database. This action is irreversible.
        </p>

        <Button
          variant="danger"
          size="sm"
          onClick={() => {
            setDeleteConfirmationText("");
            setShowDeleteModal(true);
          }}
        >
          <Trash2 size={16} /> Delete My Data
        </Button>
      </Card>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="Confirm Irreversible Data Deletion"
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setShowDeleteModal(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={handleDeleteAllData}
              disabled={deleteConfirmationText.trim() !== "DELETE MY DATA" || isDeletingData}
              isLoading={isDeletingData}
            >
              Permanently Delete Account
            </Button>
          </>
        }
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <p style={{ margin: 0, fontSize: TOKENS.typography.sizes.sm, color: TOKENS.colors.dangerText, fontWeight: 500 }}>
            Warning: This will permanently delete your account, candidate record, and all interview sessions from the database.
          </p>
          <p style={{ margin: 0, fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textSecondary }}>
            To proceed, please type <strong style={{ color: TOKENS.colors.textPrimary }}>DELETE MY DATA</strong> in the field below:
          </p>
          <Input
            value={deleteConfirmationText}
            onChange={(e) => setDeleteConfirmationText(e.target.value)}
            placeholder="Type 'DELETE MY DATA'"
            autoFocus
          />
        </div>
      </Modal>
    </div>
  );
};
