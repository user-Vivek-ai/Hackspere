import os
from datetime import datetime, timedelta
from database import get_db, init_db
from auth import hash_password
from certificates import generate_certificate_code, generate_certificate_pdf

def seed_database():
    init_db()
    db = get_db()
    cursor = db.cursor()

    # Clear existing data for fresh seed
    cursor.execute("DELETE FROM password_resets;")
    cursor.execute("DELETE FROM certificates;")
    cursor.execute("DELETE FROM submissions;")
    cursor.execute("DELETE FROM registrations;")
    cursor.execute("DELETE FROM hackathons;")
    cursor.execute("DELETE FROM users;")
    try:
        cursor.execute("DELETE FROM sqlite_sequence;")
    except Exception:
        pass

    # 1. Create Sample Users
    # Password for all demo accounts is 'Password123!'
    pw_hash = hash_password("Password123!")
    
    users = [
        # Participants
        ("Alex Rivera", "alex.dev@example.com", pw_hash, "participant", "Full-stack developer passionate about AI and distributed systems.", None),
        ("Priya Patel", "priya.patel@example.com", pw_hash, "participant", "Frontend engineer & UI designer building accessible web apps.", None),
        ("Marcus Vance", "marcus.vance@example.com", pw_hash, "participant", "Data scientist & machine learning engineer.", None),
        # Organizers
        ("Sarah Chen", "sarah.organizer@example.com", pw_hash, "organizer", "VP of Community at TechInnovate Global. Host of 20+ hackathons.", None),
        ("David Miller", "david.host@example.com", pw_hash, "organizer", "Director of DevRel at CloudPulse & AI Guild Founder.", None),
        ("AI", "ai@example.com", pw_hash, "organizer", "Organizer & AI Hackathon Lead.", None),
        ("AI", "ai.organizer@example.com", pw_hash, "organizer", "Organizer & AI Hackathon Lead.", None),
        ("AI", "2403A51258@sru.edu.in", pw_hash, "organizer", "Organizer & AI Hackathon Lead.", None),
        ("Vivek", "vivek@example.com", pw_hash, "organizer", "Hackathon Lead & Community Founder.", None)
    ]

    cursor.executemany("""
    INSERT INTO users (name, email, password_hash, role, bio, avatar_url, created_at)
    VALUES (?, ?, ?, ?, ?, ?, datetime('now', '-30 days'));
    """, users)

    # Fetch user IDs
    user_map = {}
    for row in cursor.execute("SELECT id, email FROM users;").fetchall():
        user_map[row["email"]] = row["id"]

    alex_id = user_map["alex.dev@example.com"]
    priya_id = user_map["priya.patel@example.com"]
    marcus_id = user_map["marcus.vance@example.com"]
    sarah_id = user_map["sarah.organizer@example.com"]
    david_id = user_map["david.host@example.com"]
    ai_id = user_map.get("ai@example.com", sarah_id)

    # 2. Create Hackathons
    now = datetime.now()
    
    hackathons = [
        (
            ai_id,
            "NextGen AI Hackathon 2026",
            "Practical AI for a better future — build useful, responsible AI solutions for everyday challenges.",
            "Join the NextGen AI Hackathon and turn your ideas into AI-powered solutions. Build a project that addresses a real-world problem, learn from other creators, and present your work to a panel of judges. Beginners and experienced developers are welcome.",
            "AI & Machine Learning",
            "online",
            "Online. Event announcements, team coordination, and submission instructions will be shared with registered participants.",
            (now - timedelta(days=1)).strftime("%Y-%m-%d"),
            (now + timedelta(days=30)).strftime("%Y-%m-%d"),
            (now + timedelta(days=20)).strftime("%Y-%m-%d"),
            (now + timedelta(days=25)).strftime("%Y-%m-%d"),
            1, 4,
            "Open to all developers, designers, and students globally. All team members must be registered.",
            "1. All project code must be original.\n2. Projects must be open-source or freely testable via live URL.\n3. Third-party APIs and open-source models are encouraged with proper attribution.\n4. Submissions require a working demo URL and a project description.",
            "• Day 1: Opening Ceremony & Keynote\n• Day 2: AI Multi-Agent Architecture Workshop\n• Day 4: Mentorship & Office Hours\n• Day 7: Final Submissions Due\n• Day 9: Winner Showcase & Awards",
            "• Innovation & Originality (30%)\n• Technical Complexity & Execution (30%)\n• Practical Utility & Impact (20%)\n• Polish & User Experience (20%)",
            "Participation certificates for eligible submissions",
            "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1200&auto=format&fit=crop&q=80",
            "upcoming",
            (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
            (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        ),
        (
            sarah_id,
            "AI Agents & Autonomous Systems Global Hackathon",
            "Build next-generation autonomous AI agents that solve real-world problems.",
            "Join over 1,500 builders worldwide in the premier AI hackathon of 2026. Create multi-agent workflows, tool-using assistants, or autonomous agent swarms utilizing cutting-edge LLMs and real-time execution frameworks.",
            "AI & Machine Learning",
            "online",
            "Virtual / Worldwide (Discord & Zoom)",
            (now - timedelta(days=5)).strftime("%Y-%m-%d"),
            (now + timedelta(days=60)).strftime("%Y-%m-%d"),
            (now + timedelta(days=45)).strftime("%Y-%m-%d"),
            (now + timedelta(days=55)).strftime("%Y-%m-%d"),
            1, 4,
            "Open to all developers, designers, and students globally. All team members must be registered.",
            "1. All project code must be written during the hackathon.\n2. Projects must be open-source or freely testable via live URL.\n3. Third-party APIs and open-source models are encouraged with proper attribution.\n4. Submissions require a working demo URL and a project description.",
            "• Day 1: Opening Ceremony & Keynote\n• Day 2: AI Multi-Agent Architecture Workshop\n• Day 4: Mentorship & Office Hours\n• Day 7: Final Submissions Due at 23:59 UTC\n• Day 9: Winner Showcase & Awards",
            "• Innovation & Originality (30%)\n• Technical Complexity & Execution (30%)\n• Practical Utility & Impact (20%)\n• Polish & User Experience (20%)",
            "$25,000 Total Cash Pool ($12,000 Grand Prize, $7,000 Runner-Up, $3,000 Track Winners) + $50,000 Cloud Credits",
            "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1200&auto=format&fit=crop&q=80",
            "ongoing",
            (now - timedelta(days=15)).strftime("%Y-%m-%d %H:%M:%S"),
            (now - timedelta(days=15)).strftime("%Y-%m-%d %H:%M:%S")
        ),
        (
            david_id,
            "NextGen Web3 & Decentralized Finance Summit",
            "Revolutionize decentralized identity, DeFi, and privacy protocols.",
            "Push the boundaries of Web3 infrastructure. Build zero-knowledge proofs, smart contract primitives, cross-chain messaging, or decentralized finance tools that provide actual utility to billions.",
            "Web3 & Blockchain",
            "hybrid",
            "San Francisco, CA & Online Stream",
            (now + timedelta(days=10)).strftime("%Y-%m-%d"),
            (now + timedelta(days=90)).strftime("%Y-%m-%d"),
            (now + timedelta(days=75)).strftime("%Y-%m-%d"),
            (now + timedelta(days=85)).strftime("%Y-%m-%d"),
            1, 4,
            "Developers 18+ worldwide. In-person participants must check-in at SF venue.",
            "1. Smart contracts must compile and be deployed to a testnet.\n2. No pre-built code; public git commit history must reflect hackathon dates.\n3. Teams must adhere to ethical security guidelines.",
            "• Day 1: Hacker Registration & Mixer\n• Day 2: Zero-Knowledge Protocols Masterclass\n• Day 3: Sponsor Bounty Demos\n• Day 4: Project Demos & Live Judging",
            "• Technical Rigor & Security (35%)\n• Web3 Innovation (30%)\n• UI/UX Usability (20%)\n• Presentation (15%)",
            "$35,000 Prize Pool + Founder VC Introductions",
            "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=1200&auto=format&fit=crop&q=80",
            "upcoming",
            (now - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S"),
            (now - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        ),
        (
            sarah_id,
            "ClimateHack Global: Technology for Earth",
            "Harness software, IoT, and AI to mitigate carbon emissions and protect ecosystems.",
            "Focusing on real impact: renewable energy forecasting, carbon accounting, smart agriculture, biodiversity tracking, and circular economy platforms.",
            "Climate Tech",
            "online",
            "Virtual / Global",
            (now + timedelta(days=20)).strftime("%Y-%m-%d"),
            (now + timedelta(days=120)).strftime("%Y-%m-%d"),
            (now + timedelta(days=100)).strftime("%Y-%m-%d"),
            (now + timedelta(days=115)).strftime("%Y-%m-%d"),
            2, 5,
            "Open to anyone passionate about sustainable development goals.",
            "Projects must clearly articulate climate impact metrics. Open-source repositories strongly preferred.",
            "• Kickoff: Climate Scientists Panel\n• Mid-point: Data Pipeline Review\n• Final: Pitch to Climate Investors",
            "• Climate Impact Potential (40%)\n• Feasibility & Scalability (30%)\n• Technical Architecture (30%)",
            "$20,000 Grant Funding + Accelerator Fast-Track",
            "https://images.unsplash.com/photo-1497435334941-8c899ee9e8e9?w=1200&auto=format&fit=crop&q=80",
            "upcoming",
            (now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"),
            (now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
        ),
        (
            david_id,
            "Global HealthTech Innovation Challenge 2026",
            "Pioneering digital therapeutics, patient diagnostics, and telehealth tools.",
            "An international hackathon uniting doctors, engineers, and designers to build healthcare accessibility tools, AI triage assistants, and mental wellness systems.",
            "Healthcare",
            "in-person",
            "Boston Innovation Hub, Boston, MA",
            (now - timedelta(days=25)).strftime("%Y-%m-%d"),
            (now - timedelta(days=21)).strftime("%Y-%m-%d"),
            (now - timedelta(days=26)).strftime("%Y-%m-%d"),
            (now - timedelta(days=22)).strftime("%Y-%m-%d"),
            1, 4,
            "Open to healthcare practitioners, researchers, and software engineers.",
            "Must comply with healthcare privacy best practices (HIPAA/GDPR-compliant concepts).",
            "• Day 1: Clinical Problem Statements\n• Day 2: Rapid Prototyping\n• Day 3: Clinical Validation\n• Day 4: Final Showcase",
            "• Clinical Relevance (35%)\n• Technical Integrity (30%)\n• Patient Accessibility (20%)\n• Viability (15%)",
            "$40,000 in Non-Dilutive Grants",
            "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=1200&auto=format&fit=crop&q=80",
            "ended",
            (now - timedelta(days=35)).strftime("%Y-%m-%d %H:%M:%S"),
            (now - timedelta(days=20)).strftime("%Y-%m-%d %H:%M:%S")
        )
    ]

    cursor.executemany("""
    INSERT INTO hackathons (
        organizer_id, title, tagline, description, theme, format, location,
        start_date, end_date, registration_deadline, submission_deadline,
        team_size_min, team_size_max, eligibility, rules, schedule, judging_criteria,
        prizes, banner_url, status, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, hackathons)

    # Fetch hackathon IDs
    h_map = {row["title"]: row["id"] for row in cursor.execute("SELECT id, title FROM hackathons;").fetchall()}
    nextgen_hack_id = h_map["NextGen AI Hackathon 2026"]
    ai_hack_id = h_map["AI Agents & Autonomous Systems Global Hackathon"]
    web3_hack_id = h_map["NextGen Web3 & Decentralized Finance Summit"]
    climate_hack_id = h_map["ClimateHack Global: Technology for Earth"]
    health_hack_id = h_map["Global HealthTech Innovation Challenge 2026"]

    # 3. Create Registrations
    registrations = [
        # NextGen AI Hackathon 2026 (Hosted by AI) -> 1 Pending registration ready to review
        (nextgen_hack_id, alex_id, "alex.dev@example.com", "Alex Rivera", "pending", (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")),
        # AI Hackathon
        (ai_hack_id, alex_id, "alex.dev@example.com", "Alex Rivera", "accepted", (now - timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S")),
        (ai_hack_id, priya_id, "priya.patel@example.com", "Priya Patel", "accepted", (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")),
        (ai_hack_id, marcus_id, "marcus.vance@example.com", "Marcus Vance", "pending", (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")),
        # Web3 Hackathon
        (web3_hack_id, alex_id, "alex.dev@example.com", "Alex Rivera", "pending", (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")),
        # HealthTech Hackathon (ended)
        (health_hack_id, alex_id, "alex.dev@example.com", "Alex Rivera", "accepted", (now - timedelta(days=25)).strftime("%Y-%m-%d %H:%M:%S")),
        (health_hack_id, priya_id, "priya.patel@example.com", "Priya Patel", "accepted", (now - timedelta(days=24)).strftime("%Y-%m-%d %H:%M:%S"))
    ]

    cursor.executemany("""
    INSERT INTO registrations (hackathon_id, user_id, user_email, user_name, status, registered_at)
    VALUES (?, ?, ?, ?, ?, ?);
    """, registrations)

    # 4. Create Project Submissions
    # Alex submitted to AI hackathon -> pending review
    # Priya submitted to AI hackathon -> pending review
    # Alex submitted to HealthTech hackathon -> accepted! With feedback & certificate!
    # Priya submitted to HealthTech hackathon -> rejected (sample with constructive feedback)
    submissions = [
        (
            ai_hack_id,
            alex_id,
            "AutoAgent Swarm Studio",
            "An autonomous multi-agent orchestration engine with browser automation, code execution sandboxes, and human-in-the-loop checkpoints.",
            "Alex Rivera, Elena Rostova",
            "https://autoagent-swarm.demo.app",
            "https://github.com/alexrivera/autoagent-swarm",
            "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=800&auto=format&fit=crop&q=80",
            None,
            "pending",
            None,
            (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            None
        ),
        (
            ai_hack_id,
            priya_id,
            "CogniFlow Voice Assistant",
            "Ultra-low-latency real-time voice intelligence assistant for customer workflows with multimodal screen understanding.",
            "Priya Patel, Kevin Zhang",
            "https://cogniflow.demo.dev",
            "https://github.com/priyapatel/cogniflow-ai",
            "https://images.unsplash.com/photo-1589254065878-42c9da997008?w=800&auto=format&fit=crop&q=80",
            None,
            "pending",
            None,
            (now - timedelta(hours=14)).strftime("%Y-%m-%d %H:%M:%S"),
            None
        ),
        (
            health_hack_id,
            alex_id,
            "PulseCare Telehealth Diagnostics",
            "A HIPAA-conscious remote diagnostic dashboard featuring real-time vitals telemetry, clinical decision support, and encrypted provider consultation rooms.",
            "Alex Rivera, Dr. John Harris",
            "https://pulsecare.healthtech.demo",
            "https://github.com/alexrivera/pulsecare-telehealth",
            "https://images.unsplash.com/photo-1576091160550-2173dba999ef?w=800&auto=format&fit=crop&q=80",
            None,
            "accepted",
            "Exceptional technical architecture and clinical usability. The real-time telemetry streaming and patient privacy controls were brilliantly demonstrated.",
            (now - timedelta(days=22)).strftime("%Y-%m-%d %H:%M:%S"),
            (now - timedelta(days=21)).strftime("%Y-%m-%d %H:%M:%S")
        ),
        (
            health_hack_id,
            priya_id,
            "VitalSync Mobile Tracker",
            "A prototype wearable sync companion for patient medication reminders.",
            "Priya Patel",
            "https://vitalsync.sample.io",
            "https://github.com/priyapatel/vitalsync",
            None,
            None,
            "rejected",
            "Thank you for your submission. The team felt that while the mobile UI was clean, the technical backend integration and clinical validation scope were insufficient compared to competing entries.",
            (now - timedelta(days=22)).strftime("%Y-%m-%d %H:%M:%S"),
            (now - timedelta(days=21)).strftime("%Y-%m-%d %H:%M:%S")
        )
    ]

    cursor.executemany("""
    INSERT INTO submissions (
        hackathon_id, user_id, project_name, description, team_members,
        demo_url, repo_url, image_url, file_path, status, feedback,
        submitted_at, reviewed_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, submissions)

    # 5. Create Certificate for Accepted Submission (Alex in HealthTech)
    health_sub_row = cursor.execute(
        "SELECT id FROM submissions WHERE hackathon_id = ? AND user_id = ? AND status = 'accepted';",
        (health_hack_id, alex_id)
    ).fetchone()

    if health_sub_row:
        cert_code = "HS-2026-HC98B2"
        pdf_filename = f"{cert_code}.pdf"
        pdf_path = os.path.join(os.path.dirname(__file__), "static", "certificates", pdf_filename)
        
        # Generate the physical PDF file
        generate_certificate_pdf(
            certificate_code=cert_code,
            participant_name="Alex Rivera",
            hackathon_title="Global HealthTech Innovation Challenge 2026",
            event_dates="Oct 26 - Oct 30, 2026",
            organizer_name="David Miller",
            project_name="PulseCare Telehealth Diagnostics",
            output_path=pdf_path,
            verify_url=f"https://hackathon-hub-kappa.vercel.app/verify-certificate/{cert_code}"
        )

        cursor.execute("""
        INSERT INTO certificates (
            certificate_code, hackathon_id, user_id, submission_id,
            participant_name, hackathon_title, event_dates, organizer_name,
            issued_at, pdf_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now', '-21 days'), ?);
        """, (
            cert_code,
            health_hack_id,
            alex_id,
            health_sub_row["id"],
            "Alex Rivera",
            "Global HealthTech Innovation Challenge 2026",
            "Oct 26 - Oct 30, 2026",
            "David Miller",
            pdf_path
        ))

    db.commit()
    db.close()
    print("Database successfully seeded with realistic hackathons, users, submissions, and verified certificate!")

if __name__ == "__main__":
    seed_database()
