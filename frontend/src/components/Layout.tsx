import React, { useState } from "react";
import { Link, useLocation, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  History,
  BarChart2,
  Settings,
  LogOut,
  User,
  Clock,
  Menu,
  X,
  Sparkles,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { TOKENS } from "../tokens";
import { Badge } from "./Badge";

interface NavItem {
  name: string;
  path: string;
  icon: React.ReactNode;
}

export const Layout: React.FC = () => {
  const { user, logout, isGuest } = useAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems: NavItem[] = [
    { name: "Dashboard", path: "/", icon: <LayoutDashboard size={18} /> },
    { name: "History", path: "/history", icon: <History size={18} /> },
    { name: "Analytics", path: "/analytics", icon: <BarChart2 size={18} /> },
    { name: "Settings", path: "/settings", icon: <Settings size={18} /> },
  ];

  const getPageTitle = () => {
    const current = navItems.find((item) => item.path === location.pathname);
    if (current) return current.name;
    if (location.pathname.startsWith("/interview/")) return "Interview Room";
    if (location.pathname === "/onboarding") return "Profile Setup";
    return "Interview Platform";
  };

  return (
    <div style={{ display: "flex", minHeight: "100vh", backgroundColor: TOKENS.colors.background }}>
      {/* Left Sidebar (Desktop) */}
      <aside
        style={{
          width: "250px",
          backgroundColor: TOKENS.colors.surface,
          borderRight: `1px solid ${TOKENS.colors.border}`,
          display: "flex",
          flexDirection: "column",
          flexShrink: 0,
        }}
        className="hidden md:flex no-print"
      >
        {/* Brand / Logo */}
        <div
          style={{
            padding: "1.5rem 1.25rem",
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
            borderBottom: `1px solid ${TOKENS.colors.border}`,
          }}
        >
          <div
            style={{
              width: "2rem",
              height: "2rem",
              borderRadius: TOKENS.radii.md,
              backgroundColor: TOKENS.colors.textPrimary,
              color: TOKENS.colors.accent,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 700,
            }}
          >
            <Sparkles size={18} />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: TOKENS.typography.sizes.base, color: TOKENS.colors.textPrimary, letterSpacing: "-0.02em" }}>
              Bekon Interview
            </div>
            <div style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textMuted }}>
              Adaptive Platform
            </div>
          </div>
        </div>

        {/* Navigation items */}
        <nav style={{ padding: "1rem 0.75rem", display: "flex", flexDirection: "column", gap: "0.25rem", flex: 1 }}>
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                  padding: "0.625rem 0.875rem",
                  fontSize: TOKENS.typography.sizes.sm,
                  fontWeight: isActive ? 600 : 500,
                  borderRadius: TOKENS.radii.md,
                  color: isActive ? TOKENS.colors.textPrimary : TOKENS.colors.textSecondary,
                  backgroundColor: isActive ? TOKENS.colors.surfaceSubdued : "transparent",
                  textDecoration: "none",
                  transition: "all 150ms ease",
                }}
                className="hover:bg-slate-100"
              >
                <span style={{ color: isActive ? TOKENS.colors.accent : "inherit" }}>
                  {item.icon}
                </span>
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>

        {/* User Card at bottom */}
        <div
          style={{
            padding: "1rem 1.25rem",
            borderTop: `1px solid ${TOKENS.colors.border}`,
            backgroundColor: TOKENS.colors.surfaceSubdued,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.5rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", overflow: "hidden" }}>
              <div
                style={{
                  width: "2rem",
                  height: "2rem",
                  borderRadius: "50%",
                  backgroundColor: TOKENS.colors.surface,
                  border: `1px solid ${TOKENS.colors.border}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: TOKENS.colors.textSecondary,
                  flexShrink: 0,
                }}
              >
                <User size={14} />
              </div>
              <div style={{ overflow: "hidden" }}>
                <div
                  style={{
                    fontSize: TOKENS.typography.sizes.sm,
                    fontWeight: 600,
                    color: TOKENS.colors.textPrimary,
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                  title={user?.full_name || user?.email || "User"}
                >
                  {user?.full_name || user?.email || "Candidate"}
                </div>
                <div style={{ fontSize: TOKENS.typography.sizes.xs, color: TOKENS.colors.textMuted }}>
                  {isGuest ? "Guest (24h)" : user?.email}
                </div>
              </div>
            </div>
            <button
              onClick={() => logout()}
              title="Sign out"
              style={{
                background: "transparent",
                border: "none",
                cursor: "pointer",
                padding: "0.375rem",
                borderRadius: TOKENS.radii.sm,
                color: TOKENS.colors.textMuted,
                display: "flex",
                alignItems: "center",
              }}
              className="hover:text-red-600 hover:bg-slate-200"
              aria-label="Sign out"
            >
              <LogOut size={16} />
            </button>
          </div>
          {isGuest && (
            <Badge variant="warning" style={{ fontSize: "10px", width: "100%", justifyContent: "center" }}>
              <Clock size={10} /> Temporary Guest Session
            </Badge>
          )}
        </div>
      </aside>

      {/* Main Content Column */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, overflowY: "auto" }}>
        {/* Top bar */}
        <header
          style={{
            height: "4rem",
            backgroundColor: TOKENS.colors.surface,
            borderBottom: `1px solid ${TOKENS.colors.border}`,
            padding: "0 1.5rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexShrink: 0,
          }}
          className="no-print"
        >
          <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
            {/* Mobile Hamburger toggle */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden flex items-center justify-center p-2 rounded-md hover:bg-slate-100"
              aria-label="Toggle navigation menu"
              style={{ background: "transparent", border: "none", color: TOKENS.colors.textPrimary, cursor: "pointer" }}
            >
              {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
            <h1
              style={{
                fontSize: TOKENS.typography.sizes.lg,
                fontWeight: 600,
                color: TOKENS.colors.textPrimary,
                margin: 0,
              }}
            >
              {getPageTitle()}
            </h1>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            {isGuest ? (
              <Badge variant="warning">
                <Clock size={12} /> Guest Mode
              </Badge>
            ) : (
              <Badge variant="info">Verified Account</Badge>
            )}
          </div>
        </header>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div
            style={{
              backgroundColor: TOKENS.colors.surface,
              borderBottom: `1px solid ${TOKENS.colors.border}`,
              padding: "1rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.5rem",
            }}
            className="md:hidden no-print"
          >
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setMobileMenuOpen(false)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.75rem",
                  padding: "0.625rem 0.875rem",
                  fontSize: TOKENS.typography.sizes.sm,
                  fontWeight: 500,
                  borderRadius: TOKENS.radii.md,
                  color: TOKENS.colors.textPrimary,
                  textDecoration: "none",
                }}
              >
                {item.icon}
                <span>{item.name}</span>
              </Link>
            ))}
            <button
              onClick={() => {
                setMobileMenuOpen(false);
                logout();
              }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.75rem",
                padding: "0.625rem 0.875rem",
                fontSize: TOKENS.typography.sizes.sm,
                fontWeight: 500,
                color: TOKENS.colors.dangerText,
                background: "transparent",
                border: "none",
                cursor: "pointer",
                textAlign: "left",
              }}
            >
              <LogOut size={16} />
              <span>Sign out</span>
            </button>
          </div>
        )}

        {/* Page Content Container */}
        <main
          style={{
            flex: 1,
            padding: "2rem",
            maxWidth: "1200px",
            width: "100%",
            margin: "0 auto",
          }}
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
};
