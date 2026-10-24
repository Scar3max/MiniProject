import React from "react";
import { TOKENS } from "../tokens";

export interface Column<T> {
  header: string;
  accessorKey?: keyof T;
  cell?: (item: T) => React.ReactNode;
  width?: string;
}

export interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (item: T) => string | number;
  emptyMessage?: string;
  isLoading?: boolean;
}

export function Table<T>({
  columns,
  data,
  keyExtractor,
  emptyMessage = "No records found.",
  isLoading = false,
}: TableProps<T>) {
  return (
    <div
      style={{
        width: "100%",
        overflowX: "auto",
        border: `1px solid ${TOKENS.colors.border}`,
        borderRadius: TOKENS.radii.lg,
        backgroundColor: TOKENS.colors.surface,
      }}
    >
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          textAlign: "left",
          fontSize: TOKENS.typography.sizes.sm,
        }}
      >
        <thead>
          <tr
            style={{
              borderBottom: `1px solid ${TOKENS.colors.border}`,
              backgroundColor: TOKENS.colors.surfaceSubdued,
            }}
          >
            {columns.map((col, idx) => (
              <th
                key={idx}
                style={{
                  padding: "0.75rem 1rem",
                  fontWeight: 600,
                  color: TOKENS.colors.textSecondary,
                  width: col.width,
                }}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            <tr>
              <td
                colSpan={columns.length}
                style={{ padding: "2.5rem", textAlign: "center", color: TOKENS.colors.textMuted }}
              >
                Loading table data...
              </td>
            </tr>
          ) : data.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                style={{ padding: "2.5rem", textAlign: "center", color: TOKENS.colors.textMuted }}
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((item) => (
              <tr
                key={keyExtractor(item)}
                style={{
                  borderBottom: `1px solid ${TOKENS.colors.border}`,
                  transition: "background-color 100ms ease",
                }}
                className="hover:bg-slate-50"
              >
                {columns.map((col, idx) => (
                  <td
                    key={idx}
                    style={{
                      padding: "0.875rem 1rem",
                      color: TOKENS.colors.textPrimary,
                    }}
                  >
                    {col.cell
                      ? col.cell(item)
                      : col.accessorKey
                      ? String(item[col.accessorKey] ?? "")
                      : null}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
