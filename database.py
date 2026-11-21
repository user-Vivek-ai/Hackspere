import sqlite3
import os
import shutil
import tempfile
import time
from datetime import datetime

IS_VERCEL = os.environ.get("VERCEL") == "1" or "VERCEL" in os.environ

if IS_VERCEL:
    TEMP_DIR = tempfile.gettempdir()
    DB_PATH = os.path.join(TEMP_DIR, "hacksphere.db")
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), "hacksphere.db")

def ensure_db_file():
    """Ensure database file is copied, synchronized, and writable in Vercel serverless /tmp."""
    if IS_VERCEL:
        src_db = os.path.join(os.path.dirname(__file__), "hacksphere.db")
        needs_copy = False
        if not os.path.exists(DB_PATH):
            needs_copy = True
        elif os.path.exists(src_db):
            try:
                if os.path.getsize(DB_PATH) == 0:
                    needs_copy = True
            except Exception:
                pass

        if needs_copy and os.path.exists(src_db):
            try:
                shutil.copyfile(src_db, DB_PATH)
            except Exception as e:
                print("DB copy error:", e)
        elif os.path.exists(DB_PATH) and os.path.exists(src_db):
            # If DB in /tmp already exists, synchronize base records from src_db
            try:
                sync_conn = sqlite3.connect(DB_PATH, timeout=15.0)
                try:
                    sync_conn.execute("PRAGMA foreign_keys = OFF;")
                except Exception:
                    pass
                sync_conn.execute("ATTACH ? AS src", (src_db,))
                sync_conn.execute("INSERT OR IGNORE INTO users SELECT * FROM src.users;")
                sync_conn.execute("INSERT OR IGNORE INTO hackathons SELECT * FROM src.hackathons;")
                try:
                    sync_conn.execute("INSERT OR IGNORE INTO certificates SELECT * FROM src.certificates;")
                except Exception:
                    pass
                try:
                    sync_conn.execute("INSERT OR IGNORE INTO registrations SELECT * FROM src.registrations;")
                except Exception:
                    pass
                try:
                    sync_conn.execute("INSERT OR IGNORE INTO submissions SELECT * FROM src.submissions;")
                except Exception:
                    pass
                sync_conn.commit()
                sync_conn.execute("DETACH DATABASE src;")
                try:
                    sync_conn.execute("PRAGMA foreign_keys = ON;")
                except Exception:
                    pass
                sync_conn.close()
            except Exception as e:
                print("Sync src to /tmp DB error:", e)

        # Ensure write permissions
        for ext in ["", "-wal", "-shm", "-journal"]:
            p = DB_PATH + ext
            if os.path.exists(p):
                try:
                    os.chmod(p, 0o666)
                except Exception:
                    pass

# Call immediately on module load
ensure_db_file()

def create_raw_connection():
    """Create a raw, properly configured sqlite3 connection with WAL mode and high timeout."""
    ensure_db_file()
    conn = sqlite3.connect(
        DB_PATH,
        timeout=60.0,
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
    except Exception:
        pass
    try:
        conn.execute("PRAGMA busy_timeout = 60000;")
    except Exception:
        pass
    try:
        conn.execute("PRAGMA synchronous = NORMAL;")
    except Exception:
        pass
    try:
        conn.execute("PRAGMA temp_store = MEMORY;")
    except Exception:
        pass
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

class RobustCursorProxy:
    def __init__(self, cursor):
        self._cursor = cursor

    def __getattr__(self, name):
        return getattr(self._cursor, name)

    def execute(self, *args, **kwargs):
        delay = 0.05
        for attempt in range(6):
            try:
                return self._cursor.execute(*args, **kwargs)
            except sqlite3.OperationalError as e:
                if ("locked" in str(e).lower() or "busy" in str(e).lower()) and attempt < 5:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise

    def executemany(self, *args, **kwargs):
        delay = 0.05
        for attempt in range(6):
            try:
                return self._cursor.executemany(*args, **kwargs)
            except sqlite3.OperationalError as e:
                if ("locked" in str(e).lower() or "busy" in str(e).lower()) and attempt < 5:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise

class RobustConnectionProxy:
    def __init__(self, conn, is_request=False):
        self._conn = conn
        self._is_request = is_request

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def cursor(self):
        return RobustCursorProxy(self._conn.cursor())

    def execute(self, *args, **kwargs):
        delay = 0.05
        for attempt in range(6):
            try:
                return self._conn.execute(*args, **kwargs)
            except sqlite3.OperationalError as e:
                if ("locked" in str(e).lower() or "busy" in str(e).lower()) and attempt < 5:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise

    def executemany(self, *args, **kwargs):
        delay = 0.05
        for attempt in range(6):
            try:
                return self._conn.executemany(*args, **kwargs)
            except sqlite3.OperationalError as e:
                if ("locked" in str(e).lower() or "busy" in str(e).lower()) and attempt < 5:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise

    def commit(self):
        delay = 0.05
        for attempt in range(6):
            try:
                return self._conn.commit()
            except sqlite3.OperationalError as e:
                if ("locked" in str(e).lower() or "busy" in str(e).lower()) and attempt < 5:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise

    def close(self):
        # In request context, actual physical closure is deferred to request teardown
        # so multiple queries in the same request don't fail or create locks.
        if not self._is_request:
            try:
                self._conn.close()
            except Exception:
                pass

def get_db():
    """
    Get database connection. If running in Flask request context,
    reuses the connection from flask.g so all operations in the same request
    share one connection and avoid database locks.
    """
    try:
        from flask import g, has_app_context
        if has_app_context():
            if not hasattr(g, "_database") or g._database is None:
                g._database = create_raw_connection()
            return RobustConnectionProxy(g._database, is_request=True)
    except (ImportError, RuntimeError):
        pass
    return RobustConnectionProxy(create_raw_connection(), is_request=False)

def close_db_connection(e=None):
    """Teardown handler to safely close the connection at the end of each request."""
    try:
        from flask import g
        db = getattr(g, "_database", None)
        if db is not None:
            g._database = None
            try:
                if e is not None:
                    db.rollback()
                else:
                    db.commit()
            except Exception:
                pass
            try:
                db.close()
            except Exception:
                pass
    except (ImportError, RuntimeError):
        pass

def init_db():
    """Initialize database tables idempotently."""
    conn = create_raw_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'participant', -- 'participant', 'organizer', 'admin'
        status TEXT NOT NULL DEFAULT 'active',    -- 'active', 'pending_approval', 'suspended'
        bio TEXT,
        avatar_url TEXT,
        created_at TEXT NOT NULL
    );
    """)

    # Ensure status column exists in existing DBs
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'active';")
    except Exception:
        pass

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
