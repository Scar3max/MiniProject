import React from "react";
import { TOKENS } from "../tokens";

export interface TabItem {
  id: string;
  label: string;
  icon?: React.ReactNode;
}

export interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (tabId: string) => void;
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({ tabs, activeTab, onChange, className = "" }) => {
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "0.25rem",
        backgroundColor: TOKENS.colors.surfaceSubdued,
        borderRadius: TOKENS.radii.full,
        border: `1px solid ${TOKENS.colors.border}`,
        gap: "0.25rem",
      }}
      className={className}
      role="tablist"
    >
      {tabs.map((tab) => {
        const isActive = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.375rem",
              padding: "0.375rem 0.875rem",
              fontSize: TOKENS.typography.sizes.sm,
              fontWeight: isActive ? 600 : 500,
              borderRadius: TOKENS.radii.full,
              border: "none",
              cursor: "pointer",
              transition: "all 150ms ease",
              backgroundColor: isActive ? TOKENS.colors.surface : "transparent",
              color: isActive ? TOKENS.colors.textPrimary : TOKENS.colors.textSecondary,
              boxShadow: isActive ? TOKENS.shadows.sm : "none",
            }}
          >
            {tab.icon}
            {tab.label}
          </button>
        );
      })}
    </div>
  );
};
