import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "hacksphere.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'participant', -- 'participant' or 'organizer'
        bio TEXT,
        avatar_url TEXT,
        created_at TEXT NOT NULL
    );
    """)

    # Hackathons Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hackathons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        organizer_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        tagline TEXT,
        description TEXT NOT NULL,
        theme TEXT NOT NULL,
        format TEXT NOT NULL DEFAULT 'online', -- 'online', 'in-person', 'hybrid'
        location TEXT,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        registration_deadline TEXT NOT NULL,
        submission_deadline TEXT NOT NULL,
        team_size_min INTEGER NOT NULL DEFAULT 1,
        team_size_max INTEGER NOT NULL DEFAULT 4,
        eligibility TEXT,
        rules TEXT,
        schedule TEXT,
        judging_criteria TEXT,
        prizes TEXT,
        banner_url TEXT,
        status TEXT NOT NULL DEFAULT 'upcoming', -- 'upcoming', 'ongoing', 'ended'
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (organizer_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    # Registrations Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hackathon_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        user_email TEXT NOT NULL,
        user_name TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'registered', -- 'registered', 'checked_in', 'cancelled'
        registered_at TEXT NOT NULL,
        UNIQUE(hackathon_id, user_id),
        FOREIGN KEY (hackathon_id) REFERENCES hackathons (id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    # Project Submissions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hackathon_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        project_name TEXT NOT NULL,
        description TEXT NOT NULL,
        team_members TEXT NOT NULL,
        demo_url TEXT NOT NULL,
        repo_url TEXT,
        image_url TEXT,
        file_path TEXT,
        status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'accepted', 'rejected'
        feedback TEXT,
        submitted_at TEXT NOT NULL,
        reviewed_at TEXT,
        UNIQUE(hackathon_id, user_id),
        FOREIGN KEY (hackathon_id) REFERENCES hackathons (id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    # Certificates Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS certificates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        certificate_code TEXT UNIQUE NOT NULL,
        hackathon_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        submission_id INTEGER NOT NULL,
        participant_name TEXT NOT NULL,
        hackathon_title TEXT NOT NULL,
        event_dates TEXT NOT NULL,
        organizer_name TEXT NOT NULL,
        issued_at TEXT NOT NULL,
        pdf_path TEXT,
        UNIQUE(hackathon_id, user_id),
        FOREIGN KEY (hackathon_id) REFERENCES hackathons (id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (submission_id) REFERENCES submissions (id) ON DELETE CASCADE
    );
    """)

    # Password Reset Tokens Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS password_resets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token TEXT UNIQUE NOT NULL,
        expires_at TEXT NOT NULL,
        used INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at", DB_PATH)
