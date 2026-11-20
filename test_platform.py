import os
import unittest
from app import app
from database import init_db, get_db
from seed import seed_database
from auth import verify_password

class TestHackSpherePlatform(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        init_db()
        seed_database()

    def setUp(self):
        self.client = app.test_client()

    def test_01_homepage_and_listing(self):
        """Test home page and hackathon listing with filters."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"HackSphere", res.data)
        self.assertIn(b"AI Agents", res.data)

        # Explore page with filters
        res = self.client.get("/hackathons?format=online")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"online", res.data.lower())

        res = self.client.get("/hackathons?q=Autonomous")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Autonomous", res.data)

    def test_02_password_security_and_hashing(self):
        """Verify that passwords are NEVER stored in plain text."""
        db = get_db()
        users = db.execute("SELECT email, password_hash FROM users").fetchall()
        db.close()
        for u in users:
            self.assertNotIn("Password123!", u["password_hash"])
            self.assertIn("$", u["password_hash"])
            # Verify timing-resistant hash verification
            self.assertTrue(verify_password(u["password_hash"], "Password123!"))

    def test_03_journey_1_participant_signup_login_register_submit(self):
        """Journey 1: Participant signs up, logs in, registers for hackathon, and submits project."""
        test_email = "test.participant@example.com"
        test_pass = "SecurePass2026!"
        test_name = "Jordan Lee"

        # 1. Sign Up
        res = self.client.post("/auth/signup", data={
            "name": test_name,
            "email": test_email,
            "password": test_pass,
            "confirm_password": test_pass,
            "role": "participant"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Participant Dashboard", res.data)

        # 2. Log Out & Log In
        self.client.get("/auth/logout")
        res = self.client.post("/auth/login", data={
            "email": test_email,
            "password": test_pass
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Jordan", res.data)

        # 3. Register for ongoing AI Hackathon
        db = get_db()
        ai_hack = db.execute("SELECT id FROM hackathons WHERE title LIKE '%AI Agents%'").fetchone()
        db.close()
        self.assertIsNotNone(ai_hack)
        ai_hack_id = ai_hack["id"]

        res = self.client.post(f"/hackathons/{ai_hack_id}/register", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Successfully registered", res.data)

        # 4. Submit Project
        res = self.client.post(f"/hackathons/{ai_hack_id}/submit", data={
            "project_name": "AgentFlow Automator",
            "description": "An end-to-end multi-agent orchestration runtime with memory persistence and dynamic tool binding.",
            "team_members": "Jordan Lee, Sam Taylor",
            "demo_url": "https://agentflow.demo.app",
            "repo_url": "https://github.com/jordanlee/agentflow"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"AgentFlow Automator", res.data)
        self.assertIn(b"PENDING", res.data)

    def test_04_journey_2_organizer_create_and_accept_submission(self):
        """Journey 2: Organizer creates a hackathon, reviews a submission, and accepts it with feedback."""
        # Log in as Organizer Sarah Chen
        self.client.get("/auth/logout")
        res = self.client.post("/auth/login", data={
            "email": "sarah.organizer@example.com",
            "password": "Password123!"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Organizer Hub", res.data)

        # 1. Create a new hackathon
        res = self.client.post("/hackathons/create", data={
            "title": "Quantum Computing & Cryptography Sprint",
            "tagline": "Build post-quantum algorithms and cryptographic protocols.",
            "description": "Explore quantum algorithms, post-quantum cryptography, and fault-tolerant computing simulations.",
            "theme": "Quantum Computing",
            "format": "online",
            "location": "Virtual / Global",
            "start_date": "2026-12-01",
            "end_date": "2026-12-05",
            "registration_deadline": "2026-11-30",
            "submission_deadline": "2026-12-04",
            "team_size_min": 1,
            "team_size_max": 4,
            "eligibility": "Open to all researchers and developers",
            "rules": "1. Original algorithms\n2. Open source repo",
            "schedule": "Day 1: Kickoff, Day 5: Demo Day",
            "judging_criteria": "Quantum efficiency 50%, code quality 50%",
            "prizes": "$10,000 in Grants",
            "banner_url": "",
            "status": "upcoming"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Quantum Computing", res.data)

        # 2. Review Priya's pending submission on AI Hackathon
        db = get_db()
        priya_sub = db.execute(
            "SELECT id FROM submissions WHERE status = 'pending' AND project_name LIKE '%CogniFlow%'"
        ).fetchone()
        db.close()
        self.assertIsNotNone(priya_sub)

        # Accept Priya's project with feedback
        review_res = self.client.post(f"/api/submissions/{priya_sub['id']}/review", data={
            "decision": "accepted",
            "feedback": "Outstanding real-time voice latency and polished multimodal interface! Well deserved acceptance."
        }, follow_redirects=True)
        self.assertEqual(review_res.status_code, 200)
        self.assertIn(b"ACCEPTED", review_res.data)

        # Check certificate generation in DB
        db = get_db()
        cert = db.execute("SELECT * FROM certificates WHERE submission_id = ?", (priya_sub["id"],)).fetchone()
        db.close()
        self.assertIsNotNone(cert)
        self.assertTrue(cert["certificate_code"].startswith("HS-2026-"))
        self.assertEqual(cert["participant_name"], "Priya Patel")

    def test_05_journey_3_participant_downloads_certificate(self):
        """Journey 3: Accepted participant logs in and downloads their personalized PDF certificate."""
        # Log in as Priya Patel
        self.client.get("/auth/logout")
        res = self.client.post("/auth/login", data={
            "email": "priya.patel@example.com",
            "password": "Password123!"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Check that dashboard shows certificate and accepted project
        dash_res = self.client.get("/dashboard")
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b"Download PDF", dash_res.data)

        # Fetch Priya's certificate code
        db = get_db()
        cert = db.execute("SELECT certificate_code FROM certificates WHERE participant_name = 'Priya Patel'").fetchone()
        db.close()
        self.assertIsNotNone(cert)

        # Download PDF Certificate
        download_res = self.client.get(f"/certificates/{cert['certificate_code']}/download")
        self.assertEqual(download_res.status_code, 200)
        self.assertEqual(download_res.mimetype, "application/pdf")
        self.assertTrue(len(download_res.data) > 1000)
        # Verify PDF header
        self.assertTrue(download_res.data.startswith(b"%PDF"))

        # Verify on public verification registry
        verify_res = self.client.get(f"/verify-certificate/{cert['certificate_code']}")
        self.assertEqual(verify_res.status_code, 200)
        self.assertIn(b"Officially Verified Credential", verify_res.data)
        self.assertIn(b"Priya Patel", verify_res.data)

    def test_06_edge_case_unauthorized_certificate_download_prevented(self):
        """Test that unaccepted submissions cannot download certificates."""
        # Log in as a new user with no accepted submission
        self.client.get("/auth/logout")
        self.client.post("/auth/login", data={
            "email": "marcus.vance@example.com",
            "password": "Password123!"
        }, follow_redirects=True)

        # Try to download someone else's certificate (e.g. Alex's HS-2026-HC98B2)
        res = self.client.get("/certificates/HS-2026-HC98B2/download", follow_redirects=True)
        self.assertIn(b"not authorized", res.data)

    def test_07_edge_case_role_protection(self):
        """Test that a participant cannot access organizer endpoints."""
        self.client.get("/auth/logout")
        self.client.post("/auth/login", data={
            "email": "alex.dev@example.com",
            "password": "Password123!"
        }, follow_redirects=True)

        # Participant tries to access /hackathons/create
        res = self.client.get("/hackathons/create", follow_redirects=True)
        self.assertIn(b"Access denied", res.data)

if __name__ == "__main__":
    unittest.main()
