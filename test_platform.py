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
        self.assertIn(b"OFFICIALLY VERIFIED CREDENTIAL", verify_res.data)
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

    def test_10_organizer_isolation_and_complete_workflow(self):
        """Test strict organizer isolation, pending approval badge, PDF submission, review, and QR verified certificate."""
        import io

        # 1. New Organizer with 0 hackathons sees empty state and NEVER other hackathons
        org_email = "independent.org@example.com"
        org_pass = "OrgPass2026!"
        self.client.post("/auth/signup", data={
            "name": "Jane Organizer",
            "email": org_email,
            "password": org_pass,
            "confirm_password": org_pass,
            "role": "organizer"
        }, follow_redirects=True)

        res = self.client.get("/organizer/dashboard")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"You haven't created any hackathons yet", res.data)
        # Verify other organizers' hackathons are NOT leaked
        self.assertNotIn(b"Global HealthTech Innovation Challenge", res.data)

        # 2. Organizer hosts a new hackathon
        create_res = self.client.post("/hackathons/create", data={
            "title": "Quantum Neural Hackathon 2026",
            "tagline": "Next-generation quantum computing and neural systems",
            "description": "A comprehensive competitive hackathon for building quantum neural network algorithms.",
            "theme": "Quantum AI",
            "format": "online",
            "location": "Global Online",
            "start_date": "2026-12-10",
            "end_date": "2026-12-15",
            "registration_deadline": "2026-12-08",
            "submission_deadline": "2026-12-14",
            "team_size_min": "1",
            "team_size_max": "3",
            "eligibility": "Open to all researchers and engineers worldwide",
            "rules": "Original work only.",
            "schedule": "Dec 10: Kickoff, Dec 14: Submissions Due",
            "judging_criteria": "Algorithmic efficiency and practical applicability",
            "prizes": "$25,000",
            "status": "upcoming"
        }, follow_redirects=True)
        self.assertEqual(create_res.status_code, 200)
        self.assertIn(b"Quantum Neural Hackathon 2026", create_res.data)

        # Get the new hackathon id
        db = get_db()
        new_hack = db.execute("SELECT id FROM hackathons WHERE title = 'Quantum Neural Hackathon 2026'").fetchone()
        hack_id = new_hack["id"]
        db.close()

        # 3. New Participant registers for this hackathon
        part_email = "quantum.builder@example.com"
        part_pass = "BuilderPass2026!"
        self.client.get("/auth/logout")
        self.client.post("/auth/signup", data={
            "name": "Alan Turing Jr",
            "email": part_email,
            "password": part_pass,
            "confirm_password": part_pass,
            "role": "participant"
        }, follow_redirects=True)

        reg_res = self.client.post(f"/hackathons/{hack_id}/register", data={
            "team_name": "Team Quantum",
            "team_members": "Alan Turing Jr",
            "experience_level": "advanced",
            "motivation": "Excited to demonstrate hybrid quantum algorithms."
        }, follow_redirects=True)
        self.assertEqual(reg_res.status_code, 200)

        # 4. Organizer logs in: Immediately sees Action Required for Pending Registration
        self.client.get("/auth/logout")
        self.client.post("/auth/login", data={"email": org_email, "password": org_pass})
        org_dash = self.client.get("/organizer/dashboard")
        self.assertEqual(org_dash.status_code, 200)
        self.assertIn(b"Action Required: Participant Registrations Awaiting Approval", org_dash.data)
        self.assertIn(b"Alan Turing Jr", org_dash.data)

        # Find registration id
        db = get_db()
        reg_row = db.execute("SELECT id FROM registrations WHERE hackathon_id = ? AND user_id = (SELECT id FROM users WHERE email = ?)", (hack_id, part_email)).fetchone()
        reg_id = reg_row["id"]
        db.close()

        # 5. Organizer Approves Registration directly from dashboard
        approve_reg = self.client.post(f"/organizer/hackathons/{hack_id}/registrations/{reg_id}/review", data={
            "decision": "accepted",
            "next": "dashboard"
        }, follow_redirects=True)
        self.assertEqual(approve_reg.status_code, 200)
        self.assertIn(b"accepted", approve_reg.data.lower())

        # 6. Participant submits project with PDF document
        self.client.get("/auth/logout")
        self.client.post("/auth/login", data={"email": part_email, "password": part_pass})
        sub_res = self.client.post(f"/hackathons/{hack_id}/submit", data={
            "project_name": "Quantum Matrix Simulator",
            "description": "High performance simulation suite using tensor decomposition on GPU nodes.",
            "team_members": "Alan Turing Jr",
            "demo_url": "https://quantum-matrix-sim.vercel.app",
            "repo_url": "https://github.com/alan/quantum-sim",
            "document": (io.BytesIO(b"%PDF-1.4 Mock PDF Project Architecture Document"), "architecture.pdf")
        }, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(sub_res.status_code, 200)
        self.assertIn(b"submitted successfully", sub_res.data.lower())

        # 7. Organizer logs in: Immediately sees Action Required for Project Submission Review & Certificate Approval
        self.client.get("/auth/logout")
        self.client.post("/auth/login", data={"email": org_email, "password": org_pass})
        org_dash2 = self.client.get("/organizer/dashboard")
        self.assertEqual(org_dash2.status_code, 200)
        self.assertIn(b"Action Required: Project Submissions Awaiting Review", org_dash2.data)
        self.assertIn(b"Quantum Matrix Simulator", org_dash2.data)

        # Find submission id
        db = get_db()
        sub_row = db.execute("SELECT id FROM submissions WHERE hackathon_id = ? AND project_name = 'Quantum Matrix Simulator'", (hack_id,)).fetchone()
        sub_id = sub_row["id"]
        db.close()

        # 8. Organizer 1-Click Quick-Approves Project & Awards Verified Certificate
        quick_app = self.client.post(f"/organizer/submissions/{sub_id}/quick-approve", follow_redirects=True)
        self.assertEqual(quick_app.status_code, 200)
        self.assertIn(b"APPROVED", quick_app.data)

        # 9. Verify Certificate exists and Participant can download it
        db = get_db()
        cert_row = db.execute("SELECT * FROM certificates WHERE submission_id = ?", (sub_id,)).fetchone()
        self.assertIsNotNone(cert_row)
        cert_code = cert_row["certificate_code"]
        cert_id = cert_row["id"]
        db.close()

        self.client.get("/auth/logout")
        self.client.post("/auth/login", data={"email": part_email, "password": part_pass})
        download_res = self.client.get(f"/certificates/{cert_code}/download")
        self.assertEqual(download_res.status_code, 200)
        self.assertEqual(download_res.mimetype, "application/pdf")
        self.assertTrue(download_res.data.startswith(b"%PDF-1."))
        self.assertGreater(len(download_res.data), 1000)

        # 10. Public QR Scan Verification Page
        verify_res = self.client.get(f"/verify-certificate/{cert_code}")
        self.assertEqual(verify_res.status_code, 200)
        self.assertIn(b"Alan Turing Jr", verify_res.data)
        self.assertIn(b"Quantum Matrix Simulator", verify_res.data)
        self.assertIn(b"Quantum Neural Hackathon 2026", verify_res.data)
        self.assertIn(b"OFFICIALLY VERIFIED", verify_res.data)

    def test_11_admin_dashboard_and_participant_profile(self):
        """Test Administrator Control Center, moderation actions, and participant profile portfolio."""
        # 1. Non-admin cannot access admin console
        self.client.get("/auth/logout")
        self.client.post("/auth/login", data={"email": "alex.dev@example.com", "password": "Password123!"})
        res = self.client.get("/admin", follow_redirects=True)
        self.assertIn(b"Access denied", res.data)

        # 2. Admin logs in
        self.client.get("/auth/logout")
        admin_login = self.client.post("/auth/login", data={
            "email": "admin@hacksphere.com",
            "password": "Password123!"
        }, follow_redirects=True)
        self.assertEqual(admin_login.status_code, 200)
        self.assertIn(b"Admin Control Center", admin_login.data)
        self.assertIn(b"PLATFORM MASTER ADMINISTRATOR", admin_login.data)

        # 3. View Admin Dashboard KPIs and user list
        admin_dash = self.client.get("/admin/dashboard")
        self.assertEqual(admin_dash.status_code, 200)
        self.assertIn(b"Total Users", admin_dash.data)
        self.assertIn(b"Published Hackathons", admin_dash.data)
        self.assertIn(b"Verified Credentials Audit Log", admin_dash.data)
        self.assertIn(b"Alex Rivera", admin_dash.data)
        self.assertIn(b"Sarah Chen", admin_dash.data)

        # 4. Admin moderates user status (Suspend and Unsuspend)
        db = get_db()
        target_user = db.execute("SELECT id FROM users WHERE email = 'marcus.vance@example.com'").fetchone()
        target_id = target_user["id"]
        db.close()

        suspend_res = self.client.post(f"/admin/users/{target_id}/status", data={"status": "suspended"}, follow_redirects=True)
        self.assertEqual(suspend_res.status_code, 200)
        self.assertIn(b"suspended", suspend_res.data.lower())

        unsuspend_res = self.client.post(f"/admin/users/{target_id}/status", data={"status": "active"}, follow_redirects=True)
        self.assertEqual(unsuspend_res.status_code, 200)
        self.assertIn(b"active", unsuspend_res.data.lower())

        # 5. Participant Profile view and update
        self.client.get("/auth/logout")
        self.client.post("/auth/login", data={"email": "alex.dev@example.com", "password": "Password123!"})
        profile_get = self.client.get("/participant/profile")
        self.assertEqual(profile_get.status_code, 200)
        self.assertIn(b"Builder Profile", profile_get.data)
        self.assertIn(b"Alex Rivera", profile_get.data)
        self.assertIn(b"Participation History", profile_get.data)

        # Update profile bio
        profile_post = self.client.post("/participant/profile", data={
            "name": "Alex Rivera",
            "bio": "Lead Full-Stack AI Engineer building neural distributed systems."
        }, follow_redirects=True)
        self.assertEqual(profile_post.status_code, 200)
        self.assertIn(b"updated successfully", profile_post.data)
        self.assertIn(b"Lead Full-Stack AI Engineer", profile_post.data)

if __name__ == "__main__":
    unittest.main()
