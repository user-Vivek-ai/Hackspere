# ⚡ HackSphere — Platform for Discovering & Hosting Hackathons

**HackSphere** is a professional, responsive full-stack web platform designed for discovering, competing in, and hosting hackathons. It provides dedicated portals for **Participants** and **Organizers/Admins**, persistent SQLite database storage, cryptographic certificate generation, and server-side role enforcement.

---

## 🌟 Key Features

### 🔐 Authentication & Security
- **Secure Sign Up & Log In**: Requires full name, valid email address, password, and role (`Participant` or `Organizer`).
- **Cryptographic Password Storage**: Passwords are never stored as plain text. Every password is encrypted using **PBKDF2-HMAC-SHA256** with cryptographically secure 16-byte random salts and 200,000 hashing rounds, verified with timing-attack resistant comparisons (`secrets.compare_digest`).
- **Password UX**: Password visibility toggles (eye icons) and live validation requirements (minimum 8 characters with letters and numbers).
- **Forgot Password Flow**: Generates unique, time-limited reset tokens with a direct testing helper for local development environments.
- **Server-Side Role Protection**: Decorators (`@login_required`, `@role_required('organizer')`, `@role_required('participant')`) guarantee that unauthorized users cannot execute privileged actions (creating events, reviewing submissions, or accessing certificates) regardless of client-side manipulations.

### 👩‍💻 Participant Features
- **Discovery & Search**: Full-text search by title, description, and technology tags.
- **Multi-Facet Filters**: Filter hackathons by **Format** (*Online, In-Person, Hybrid*), **Topic/Theme** (*AI, Web3, Climate Tech, Healthcare, etc.*), and **Status** (*Ongoing, Upcoming, Ended*).
- **Comprehensive Detail View**: Countdown timers, event schedule, tracks, rules, eligibility, team size constraints, and judging criteria.
- **One-Click Registration**: Register with the account's verified email address; prevents duplicate registrations and respects deadlines.
- **Project Submissions**: Submit project name, thorough description, team members, live demo URL, repository URL, and optional screenshots/decks (PNG, JPG, WEBP, PDF, ZIP).
- **Status Tracking**: Participant dashboard displays real-time submission review status:
  - 🟡 **Pending**: Under evaluation by organizers.
  - 🟢 **Accepted**: Congratulatory banner with organizer feedback notes and the unlocked PDF certificate button.
  - 🔴 **Rejected**: Constructive organizer feedback explaining the decision.
- **Downloadable PDF Certificates**: Official participation certificates are unlocked **only** after an organizer formally accepts the submitted project.

### 🏆 Organizer & Admin Features
- **Host & Edit Hackathons**: Create and edit event listings with title, tagline, description, theme, dates, registration & submission deadlines, team size constraints, location/virtual links, rules, schedule, judging criteria, and prize pools.
- **Organizer Hub & Analytics**: Track registered builders, total submissions, pending reviews, and certificates awarded.
- **Participant Roster**: View all registered participants and their verified email addresses.
- **Project Submissions Review**: Examine project descriptions, test live demo URLs, review GitHub repositories, and inspect uploaded attachments.
- **Decision & Feedback Engine**: Mark projects as **Accepted** or **Rejected** with an optional personalized feedback message.
- **Automated Certificate Issuance**: When an organizer marks a submission as **Accepted**, the system automatically mints a unique certificate code (e.g., `HS-2026-HC98B2`), generates a high-resolution vector PDF, and attaches it to the participant's account.
- **Public Credential Registry**: Anyone can verify issued certificate IDs at `/verify-certificate/<certificate_code>`.

---

## 🛠️ Architecture & Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend** | Python 3, Flask 3.1, Werkzeug | REST APIs, route controllers, session security |
| **Database** | SQLite 3 | Relational schema with Foreign Keys and cascade rules |
| **PDF Engine** | ReportLab 5.1 | Vector certificate generation with custom seals and borders |
| **Frontend** | HTML5, Modern CSS3, JavaScript (ES6) | Responsive layout, accessible forms, tabs, modals |
| **Security** | `hashlib.pbkdf2_hmac`, `secrets` | NIST-grade password hashing and token generation |

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+ installed on your system.

### 2. Installation
Clone or navigate to the workspace directory:
```bash
cd "c:\Users\VIVEK AKULA\OneDrive\Desktop\Website"
```

Install the dependencies:
```bash
pip install -r requirements.txt
```

### 3. Initialize & Seed Database
The platform includes a realistic seed script that populates the database with sample hackathons, participants, submissions, and an accepted certificate:
```bash
python seed.py
```

### 4. Run the Application
Start the local server:
```bash
python run.py
```
Open your browser and navigate to:
👉 **`http://127.0.0.1:5000`**

---

## 👥 Demo Accounts

The login page includes a convenient **1-Click Demo Credential Quick-Fill** component:

| Role | Name | Email Address | Password | Details |
|---|---|---|---|---|
| **Participant** | Alex Rivera | `alex.dev@example.com` | `Password123!` | Has an **Accepted project** & ready-to-download certificate (`HS-2026-HC98B2`) |
| **Participant** | Priya Patel | `priya.patel@example.com` | `Password123!` | Has a **Pending project** in AI Hackathon & a rejected project in HealthTech |
| **Organizer** | Sarah Chen | `sarah.organizer@example.com` | `Password123!` | Hosts AI Agents & ClimateHack events; reviews submissions |
| **Organizer** | David Miller | `david.host@example.com` | `Password123!` | Hosts Web3 & HealthTech summits |

---

## 🧪 Verification of the 3 Main User Journeys

The platform includes an automated end-to-end test suite (`test_platform.py`) that validates the 3 core journeys:

### Journey 1: Participant Flow
1. Sign up as a new participant (`Jordan Lee`, `test.participant@example.com`, `SecurePass2026!`).
2. Log in with the newly created account.
3. Browse hackathons and register for the **AI Agents & Autonomous Systems Global Hackathon**.
4. Submit a project with project title, description, team members, and live demo URL.
5. Confirm the submission status appears as **Pending**.

### Journey 2: Organizer Flow
1. Log in as organizer `sarah.organizer@example.com`.
2. Open the **Organizer Hub** and create a new hackathon (*Quantum Computing & Cryptography Sprint*).
3. Open the **AI Agents Hackathon** management dashboard.
4. Review Priya Patel's pending project (*CogniFlow Voice Assistant*).
5. Mark the project as **Accepted** with a congratulatory feedback note.
6. The system automatically mints certificate code `HS-2026-XXXXXX` and generates the vector PDF.

### Journey 3: Certificate Download & Verification Flow
1. Log in as accepted participant `priya.patel@example.com` (or `alex.dev@example.com`).
2. Go to **My Dashboard** &rarr; **Earned Certificates** tab.
3. Observe the acceptance badge and organizer feedback.
4. Click **Download PDF** to download the personalized vector certificate.
5. Click **Verify Registry** or visit `/verify-certificate/<certificate_code>` to confirm the public validity.

To run the automated test suite at any time:
```bash
python test_platform.py
```
