"""
migrate_db.py - Safe additive migration script for Phase 1.
Adds users, user_profiles, candidates.user_id, sessions.is_excluded.
Never drops tables, never drops columns, preserves existing rows.
"""

import sqlite3
import os
import shutil

MIGRATION_SQL = """
-- 1. Create users table
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR NOT NULL UNIQUE,
    password_hash VARCHAR,
    role VARCHAR NOT NULL DEFAULT 'candidate',
    is_guest BOOLEAN NOT NULL DEFAULT 0,
    guest_expires_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);

-- 2. Create user_profiles table
CREATE TABLE IF NOT EXISTS user_profiles (
    profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    full_name VARCHAR,
    college_org VARCHAR,
    year_experience VARCHAR,
    target_role VARCHAR,
    preferred_domains TEXT,
    preferred_difficulty VARCHAR NOT NULL DEFAULT 'adaptive',
    consent_save_sessions BOOLEAN NOT NULL DEFAULT 1,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_user_profiles_user_id ON user_profiles (user_id);
"""

def get_row_counts(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM candidates"); cand_cnt = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM sessions"); sess_cnt = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM turns"); turn_cnt = c.fetchone()[0]
    conn.close()
    return {"candidates": cand_cnt, "sessions": sess_cnt, "turns": turn_cnt}

def apply_migration(db_path):
    print("=" * 60)
    print(f"Applying migration to: {db_path}")
    print("=" * 60)
    print("MIGRATION SQL TO BE APPLIED:")
    print(MIGRATION_SQL.strip())
    print("-" * 60)

    counts_before = get_row_counts(db_path)
    print(f"Row counts BEFORE: {counts_before}")

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # 1. Enable WAL mode & busy timeout
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=5000")

    # 2. Create new tables
    c.executescript(MIGRATION_SQL)

    # 3. Additive column: candidates.user_id
    c.execute("PRAGMA table_info(candidates)")
    cols_cand = [row[1] for row in c.fetchall()]
    if "user_id" not in cols_cand:
        print("Adding column 'user_id' to 'candidates' table...")
        c.execute("ALTER TABLE candidates ADD COLUMN user_id INTEGER REFERENCES users(user_id)")
    else:
        print("Column 'user_id' already exists in 'candidates'.")

    # 4. Additive column: sessions.is_excluded
    c.execute("PRAGMA table_info(sessions)")
    cols_sess = [row[1] for row in c.fetchall()]
    if "is_excluded" not in cols_sess:
        print("Adding column 'is_excluded' to 'sessions' table...")
        c.execute("ALTER TABLE sessions ADD COLUMN is_excluded BOOLEAN NOT NULL DEFAULT 0")
    else:
        print("Column 'is_excluded' already exists in 'sessions'.")

    conn.commit()
    conn.close()

    counts_after = get_row_counts(db_path)
    print(f"Row counts AFTER:  {counts_after}")
    assert counts_before == counts_after, f"Row count mismatch: {counts_before} != {counts_after}"
    print("[PASS] Migration applied safely. All existing row counts strictly unchanged.")
    print("=" * 60)

if __name__ == "__main__":
    db_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "interview_history.db")
    apply_migration(db_file)
