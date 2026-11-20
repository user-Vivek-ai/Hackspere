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

        # 3b. Organizer Sarah accepts Jordan's registration
        db = get_db()
        reg = db.execute("SELECT id FROM registrations WHERE hackathon_id = ? AND user_email = ?", (ai_hack_id, test_email)).fetchone()
        db.close()
        self.assertIsNotNone(reg)

        # Log in as Sarah
        self.client.get("/auth/logout")
        self.client.post("/auth/login", data={"email": "sarah.organizer@example.com", "password": "Password123!"})
        res = self.client.post(f"/organizer/hackathons/{ai_hack_id}/registrations/{reg['id']}/review", data={"decision": "accepted"}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Log back in as Jordan Lee
        self.client.get("/auth/logout")
        self.client.post("/auth/login", data={"email": test_email, "password": test_pass})

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

    def test_08_full_role_separated_lifecycle(self):
        """Verify: participant registers (pending) -> submission blocked while pending ->
        organizer accepts registration -> participant submits -> organizer reviews & approves ->
        certificate issued with participant's name -> participant downloads."""
        # 1. New Participant signs up
        p_email = "taylor.dev@example.com"
        p_pass = "Taylor2026Pass!"
        p_name = "Taylor Swift"

        self.client.get("/auth/logout")
        self.client.post("/auth/signup", data={
            "name": p_name,
            "email": p_email,
            "password": p_pass,
            "confirm_password": p_pass,
            "role": "participant"
        }, follow_redirects=True)

        db = get_db()
        ai_hack = db.execute("SELECT id FROM hackathons WHERE title LIKE '%AI Agents%'").fetchone()
        db.close()
        h_id = ai_hack["id"]

        # 2. Register for hackathon -> status is pending
        reg_res = self.client.post(f"/hackathons/{h_id}/register", follow_redirects=True)
        self.assertEqual(reg_res.status_code, 200)

        db = get_db()
        reg_row = db.execute("SELECT id, status FROM registrations WHERE hackathon_id = ? AND user_email = ?", (h_id, p_email)).fetchone()
        db.close()
        self.assertEqual(reg_row["status"], "pending")

        # 3. Participant tries to submit while pending -> blocked
        blocked_res = self.client.post(f"/hackathons/{h_id}/submit", data={
            "project_name": "Early Bird AI",
            "description": "An AI system that attempted to submit early before registration approval.",
            "team_members": "Taylor",
            "demo_url": "https://early.demo.app",
            "repo_url": "https://github.com/early/ai"
        }, follow_redirects=True)
        self.assertIn(b"Pending organizer acceptance", blocked_res.data)

        # 4. Organizer Sarah logs in and accepts the registration
        self.client.get("/auth/logout")
        self.client.post("/auth/login", data={"email": "sarah.organizer@example.com", "password": "Password123!"})
        accept_res = self.client.post(f"/organizer/hackathons/{h_id}/registrations/{reg_row['id']}/review", data={"decision": "accepted"}, follow_redirects=True)
        self.assertEqual(accept_res.status_code, 200)

        db = get_db()
        reg_row = db.execute("SELECT status FROM registrations WHERE id = ?", (reg_row["id"],)).fetchone()
        db.close()
        self.assertEqual(reg_row["status"], "accepted")

        # 5. Participant logs back in and successfully submits
        self.client.get("/auth/logout")
        self.client.post("/auth/login", data={"email": p_email, "password": p_pass})
        sub_res = self.client.post(f"/hackathons/{h_id}/submit", data={
            "project_name": "SoundWave Studio",
            "description": "Real-time acoustic neural synth with multi-track vocal harmonic synthesis.",
            "team_members": "Taylor Swift",
            "demo_url": "https://soundwave.demo.app",
            "repo_url": "https://github.com/taylor/soundwave"
        }, follow_redirects=True)
        self.assertEqual(sub_res.status_code, 200)
        self.assertIn(b"SoundWave Studio", sub_res.data)

        db = get_db()
        sub_row = db.execute("SELECT id, status FROM submissions WHERE hackathon_id = ? AND project_name = 'SoundWave Studio'", (h_id,)).fetchone()
        db.close()
        self.assertIn(sub_row["status"], ("under_review", "pending"))

        # 6. Organizer Sarah approves the project
        self.client.get("/auth/logout")
        self.client.post("/auth/login", data={"email": "sarah.organizer@example.com", "password": "Password123!"})
        rev_res = self.client.post(f"/api/submissions/{sub_row['id']}/review", data={
            "decision": "approved",
            "feedback": "Spectacular audio synthesis architecture and clean user experience!"
        }, follow_redirects=True)
        self.assertEqual(rev_res.status_code, 200)

        # 7. Check that Certificate was generated with Taylor's profile name
        db = get_db()
        cert = db.execute("SELECT * FROM certificates WHERE submission_id = ?", (sub_row["id"],)).fetchone()
        db.close()
        self.assertIsNotNone(cert)
        self.assertEqual(cert["participant_name"], "Taylor Swift")

        # 8. Taylor logs in and downloads their certificate
        self.client.get("/auth/logout")
        self.client.post("/auth/login", data={"email": p_email, "password": p_pass})
        down_res = self.client.get(f"/certificates/{cert['certificate_code']}/download")
        self.assertEqual(down_res.status_code, 200)
        self.assertEqual(down_res.mimetype, "application/pdf")

        # 9. Verify another participant cannot download Taylor's certificate
        self.client.get("/auth/logout")
        self.client.post("/auth/login", data={"email": "marcus.vance@example.com", "password": "Password123!"})
        hack_res = self.client.get(f"/certificates/{cert['certificate_code']}/download", follow_redirects=True)
        self.assertIn(b"not authorized", hack_res.data)

        # 10. Verify organizer David cannot manage Sarah's hackathon
        self.client.get("/auth/logout")
        self.client.post("/auth/login", data={"email": "david.host@example.com", "password": "Password123!"})
        tamper_res = self.client.get(f"/organizer/hackathons/{h_id}/manage", follow_redirects=True)
        self.assertIn(b"not authorized", tamper_res.data)

    def test_09_concurrency_and_no_database_lock(self):
        """Verify that multi-threaded concurrent operations never encounter 'database is locked' errors."""
        import concurrent.futures

        # Log in as organizer
        self.client.get("/auth/logout")
        self.client.post("/auth/login", data={"email": "sarah.organizer@example.com", "password": "Password123!"})

        def create_event(idx):
            with app.test_client() as c:
                with c.session_transaction() as sess:
                    sess["user_id"] = 4
                    sess["user_role"] = "organizer"
                    sess["user_name"] = "Sarah Chen"
                res = c.post("/hackathons/create", data={
                    "title": f"Concurrent Stress Event #{idx} - NextGen Systems",
                    "tagline": "High-throughput event creation under stress test",
                    "description": "Comprehensive description for testing database concurrency and resilience under rapid load (at least 30 chars).",
                    "theme": "AI & Distributed Systems",
                    "format": "online",
                    "location": "Global Virtual Cloud",
                    "start_date": "2026-12-01",
                    "end_date": "2026-12-05",
                    "registration_deadline": "2026-11-30",
                    "submission_deadline": "2026-12-04",
                    "team_size_min": "1",
                    "team_size_max": "4",
                    "eligibility": "Global builders",
                    "rules": "1. Safe concurrency test.",
                    "schedule": "Day 1 to 5",
                    "judging_criteria": "Speed and Reliability",
                    "prizes": "$10,000",
                    "status": "upcoming"
                }, follow_redirects=True)
                return res

        # Run 8 concurrent creations across 4 threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(create_event, i) for i in range(1, 9)]
            results = [f.result() for f in futures]

        for r in results:
            self.assertEqual(r.status_code, 200)
            self.assertNotIn(b"database is locked", r.data)
            self.assertIn(b"created successfully", r.data)

if __name__ == "__main__":
    unittest.main()
