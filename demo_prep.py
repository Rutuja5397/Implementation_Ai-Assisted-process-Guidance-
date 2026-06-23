"""
Demo preparation script.
Creates / resets the five clean demo accounts used in DEMO_TEST_GUIDE.md.
Run once before the professor demo:

    python3 demo_prep.py

Does NOT touch production logic — only inserts/updates rows in the users table.
"""

import os
import sys
import sqlite3
from pathlib import Path

import bcrypt

# ─── Config ───────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent
_env_url = os.getenv("DATABASE_URL", "")
if _env_url:
    DB_PATH = _env_url.replace("sqlite:///", "")
    if not os.path.isabs(DB_PATH):
        DB_PATH = str(PROJECT_ROOT / DB_PATH.lstrip("./"))
else:
    DB_PATH = str(PROJECT_ROOT / "crane_ai.db")

# Demo accounts: (name, username, password, role)
DEMO_USERS = [
    ("Alice Engineer",    "alice",    "test123",   "ME"),
    ("Bob Senior",        "bob",      "test123",   "SME"),
    ("Carol Admin",       "carol",    "test123",   "ADM"),
    ("Demo Supervisor",   "demo_sup", "demo1234",  "SUP"),
    ("Demo KE",           "demo_ke",  "demo1234",  "KE"),
]


def hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def main():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found at: {DB_PATH}")
        print("  Start the backend first to initialise the database, then re-run.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print(f"Database: {DB_PATH}\n")

    for name, username, password, role in DEMO_USERS:
        hp = hash_pw(password)
        existing = cur.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()

        if existing:
            cur.execute(
                "UPDATE users SET hashed_password = ?, role = ?, is_active = 1 WHERE username = ?",
                (hp, role, username),
            )
            print(f"  [UPDATED]  {username:<18} role={role}  password reset to '{password}'")
        else:
            cur.execute(
                """INSERT INTO users (username, name, hashed_password, role, is_active, created_at)
                   VALUES (?, ?, ?, ?, 1, datetime('now'))""",
                (username, name, hp, role),
            )
            print(f"  [CREATED]  {username:<18} role={role}  password='{password}'")

    conn.commit()
    conn.close()

    print("\nDemo accounts ready.")
    print("─" * 50)
    print(f"{'Role':<6}  {'Username':<18}  {'Password'}")
    print(f"{'─'*6}  {'─'*18}  {'─'*10}")
    for _, username, password, role in DEMO_USERS:
        print(f"{role:<6}  {username:<18}  {password}")
    print()


if __name__ == "__main__":
    main()
