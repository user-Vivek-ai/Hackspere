import os
import sys
from database import init_db, get_db
from seed import seed_database
from app import app

def prepare_app():
    init_db()
    db = get_db()
    user_count = db.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    db.close()
    if user_count == 0:
        print("Empty database detected. Seeding sample hackathons, users, submissions, and certificates...")
        seed_database()
    else:
        print(f"Database ready with {user_count} registered users.")

if __name__ == "__main__":
    prepare_app()
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"\n=======================================================")
    print(f"🚀 HackSphere Platform running live at http://{host}:{port}")
    print(f"=======================================================\n")
    app.run(host=host, port=port, debug=False)
