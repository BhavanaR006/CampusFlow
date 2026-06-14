"""
CampusFlow Database Layer
SQLite setup with all 11 tables + complete sample data for demo
"""

import sqlite3
import os
import hashlib
from datetime import datetime, timedelta, date

DB_PATH = os.path.join(os.path.dirname(__file__), "campusflow.db")


def get_db():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def hash_password(password: str) -> str:
    """Simple SHA-256 hash for demo purposes."""
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    """Create all tables and seed sample data."""
    conn = get_db()
    cursor = conn.cursor()

    # ─── TABLE CREATION ───────────────────────────────────────────────────────

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            branch TEXT,
            year INTEGER,
            cgpa REAL,
            roll_no TEXT,
            email TEXT,
            phone TEXT,
            monthly_budget REAL DEFAULT 5000,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            title TEXT NOT NULL,
            type TEXT DEFAULT 'class',
            location TEXT,
            urgency TEXT DEFAULT 'normal',
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            raw_text TEXT,
            summary TEXT,
            category TEXT,
            urgency TEXT DEFAULT 'medium',
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deadline TEXT,
            is_read INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            due_date TEXT,
            category TEXT,
            priority TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            total_classes INTEGER DEFAULT 0,
            attended INTEGER DEFAULT 0,
            required_pct REAL DEFAULT 75.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS exam_timetable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            exam_date TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            venue TEXT,
            exam_type TEXT DEFAULT 'mid-sem',
            syllabus TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            body TEXT,
            alert_type TEXT DEFAULT 'info',
            trigger_at TIMESTAMP,
            is_sent INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS mood_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            mood INTEGER NOT NULL CHECK(mood >= 1 AND mood <= 5),
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS placement_apps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            company TEXT NOT NULL,
            role TEXT,
            status TEXT DEFAULT 'Applied',
            applied_date TEXT,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    # ─── CHECK IF DATA ALREADY SEEDED ─────────────────────────────────────────

    existing = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if existing > 0:
        conn.close()
        return

    # ─── SEED SAMPLE DATA ─────────────────────────────────────────────────────

    today = date.today()
    now = datetime.now()

    # Days of the week (college is Mon-Sat)
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    # If today is Sunday (weekday=6), show Monday as "today" for demo
    if today.weekday() >= 6:
        today_day = "Monday"
        tomorrow_day = "Tuesday"
    else:
        today_day = days[today.weekday()]
        tomorrow_day = days[(today.weekday() + 1) % 6] if today.weekday() < 5 else "Monday"

    # ── User: Arjun Sharma ──
    cursor.execute("""
        INSERT INTO users (name, password_hash, branch, year, cgpa, roll_no, email, phone, monthly_budget)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "Arjun Sharma",
        hash_password("demo123"),
        "CSE",
        3,
        8.4,
        "21CS042",
        "arjun@college.edu",
        "9876543210",
        5000.0
    ))
    user_id = cursor.lastrowid

    # ── Schedule (Today + Tomorrow) ──
    schedule_data = [
        # Today
        (user_id, today_day, "09:00", "10:00", "Operating Systems", "class", "LH3", "normal"),
        (user_id, today_day, "11:00", "12:00", "Database Management Systems", "class", "LH1", "normal"),
        (user_id, today_day, "12:00", "13:00", "Lunch Break", "break", "Mess", "normal"),
        (user_id, today_day, "14:00", "14:00", "DSA Assignment Deadline", "deadline", "Online", "high"),
        (user_id, today_day, "16:00", "17:30", "Coding Club Meeting", "club", "CS204", "normal"),
        (user_id, today_day, "17:45", "18:00", "Campus Shuttle", "transport", "Main Gate", "normal"),
        # Tomorrow
        (user_id, tomorrow_day, "09:00", "10:00", "OS Review Session", "class", "LH3", "normal"),
        (user_id, tomorrow_day, "10:00", "11:00", "Hostel Water Maintenance", "maintenance", "Hostel B", "medium"),
        (user_id, tomorrow_day, "14:00", "15:00", "DBMS Quiz", "exam", "LH1", "high"),
        (user_id, tomorrow_day, "15:30", "17:00", "CN Lab", "lab", "NW Lab2", "normal"),
    ]
    cursor.executemany("""
        INSERT INTO schedule (user_id, day, start_time, end_time, title, type, location, urgency)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, schedule_data)

    # ── Full Weekly Timetable ──
    weekly_schedule = [
        # Monday
        (user_id, "Monday", "09:00", "10:00", "Operating Systems", "class", "LH3", "normal"),
        (user_id, "Monday", "11:00", "12:00", "Data Structures & Algorithms", "class", "LH2", "normal"),
        (user_id, "Monday", "14:00", "15:00", "Computer Networks", "class", "LH1", "normal"),
        (user_id, "Monday", "15:30", "17:00", "SE Lab", "lab", "CS Lab1", "normal"),
        # Tuesday
        (user_id, "Tuesday", "09:00", "10:00", "Database Management Systems", "class", "LH1", "normal"),
        (user_id, "Tuesday", "11:00", "12:00", "Software Engineering", "class", "LH4", "normal"),
        (user_id, "Tuesday", "14:00", "15:30", "DSA Lab", "lab", "CS Lab2", "normal"),
        # Wednesday
        (user_id, "Wednesday", "09:00", "10:00", "Computer Networks", "class", "LH1", "normal"),
        (user_id, "Wednesday", "11:00", "12:00", "Operating Systems", "class", "LH3", "normal"),
        (user_id, "Wednesday", "14:00", "15:00", "Database Management Systems", "class", "LH1", "normal"),
        # Thursday
        (user_id, "Thursday", "09:00", "10:00", "Data Structures & Algorithms", "class", "LH2", "normal"),
        (user_id, "Thursday", "11:00", "12:00", "Software Engineering", "class", "LH4", "normal"),
        (user_id, "Thursday", "14:00", "15:30", "CN Lab", "lab", "NW Lab2", "normal"),
        # Friday
        (user_id, "Friday", "09:00", "10:00", "Operating Systems", "class", "LH3", "normal"),
        (user_id, "Friday", "11:00", "12:00", "Computer Networks", "class", "LH1", "normal"),
        (user_id, "Friday", "14:00", "15:00", "Data Structures & Algorithms", "class", "LH2", "normal"),
        # Saturday
        (user_id, "Saturday", "09:00", "10:00", "Software Engineering", "class", "LH4", "normal"),
        (user_id, "Saturday", "10:30", "12:00", "DBMS Lab", "lab", "CS Lab1", "normal"),
    ]

    # Only insert weekly schedule for days that aren't today/tomorrow (avoid duplicates)
    for entry in weekly_schedule:
        entry_day = entry[1]  # day is at index 1 in the tuple
        if entry_day != today_day and entry_day != tomorrow_day:
            cursor.execute("""
                INSERT INTO schedule (user_id, day, start_time, end_time, title, type, location, urgency)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, entry)

    # ── Notices (6 notices) ──
    notices_data = [
        (user_id, "TCS Pre-Placement Talk — Register Now",
         "TCS is conducting a pre-placement talk for all CSE and IT students. Registration is mandatory for placement eligibility. Venue: Main Auditorium. Register on the placement portal by tonight 11:59 PM. Carry your college ID.",
         "TCS pre-placement talk registration closes tonight at 11:59 PM. Register on placement portal to maintain placement eligibility.",
         "placement", "urgent", "Placement Cell Email",
         (now - timedelta(hours=6)).isoformat(), (today + timedelta(hours=23, minutes=59)).isoformat(), 0),

        (user_id, "Mid-Semester Exam Timetable Released",
         "The mid-semester examination timetable for Semester 5 has been released. Exams begin next Monday. Students can view the complete schedule on the academic portal. Any conflicts must be reported to the exam cell within 24 hours.",
         "Mid-sem exams start next Monday. Check academic portal for full schedule — report conflicts within 24 hours.",
         "academic", "urgent", "Academic Portal",
         (now - timedelta(hours=12)).isoformat(), (today + timedelta(days=7)).isoformat(), 0),

        (user_id, "Water Supply Shutdown Tomorrow",
         "Due to maintenance work on the main pipeline, water supply to Hostel B and C will be shut down tomorrow from 10 AM to 11 AM. Students are advised to store sufficient water beforehand.",
         "Water supply off tomorrow 10-11 AM in Hostel B & C. Store water tonight to avoid inconvenience.",
         "hostel", "medium", "Hostel WhatsApp Group",
         (now - timedelta(hours=3)).isoformat(), (today + timedelta(days=1, hours=10)).isoformat(), 0),

        (user_id, "Route 4 Shuttle Timing Change",
         "Please note that Route 4 campus shuttle will now depart at 5:45 PM instead of 5:30 PM effective immediately. This change is permanent due to traffic adjustments.",
         "Route 4 shuttle now departs at 5:45 PM (was 5:30 PM). Change is permanent starting today.",
         "transport", "medium", "Transport Office Notice Board",
         (now - timedelta(days=1)).isoformat(), None, 0),

        (user_id, "Robotics Club Recruitment Drive",
         "Robotics Club is recruiting new members! Open for all branches and years. Showcase your projects or just come to learn. This Friday, 5 PM at Innovation Lab. No prior experience needed.",
         "Robotics Club recruitment this Friday 5 PM at Innovation Lab. All branches welcome, no experience needed.",
         "club", "low", "Club WhatsApp Group",
         (now - timedelta(days=2)).isoformat(), (today + timedelta(days=4)).isoformat(), 0),

        (user_id, "Library Extended Hours During Exams",
         "The central library will remain open until midnight (12 AM) during the examination period starting next week. Regular hours resume after exams. Student ID required for entry after 9 PM.",
         "Library open till midnight during exam week starting Monday. Carry student ID for entry after 9 PM.",
         "academic", "low", "Library Portal",
         (now - timedelta(days=1)).isoformat(), None, 0),
    ]
    cursor.executemany("""
        INSERT INTO notices (user_id, title, raw_text, summary, category, urgency, source, created_at, deadline, is_read)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, notices_data)

    # ── Tasks (6 tasks, AI-prioritized) ──
    tasks_data = [
        (user_id, "DSA Assignment 4", (today.isoformat() + " 14:00"), "academic", "high", "pending"),
        (user_id, "Register for TCS Pre-Placement Talk", (today.isoformat() + " 23:59"), "placement", "high", "pending"),
        (user_id, "Revise OS Unit 3 for quiz", ((today + timedelta(days=1)).isoformat()), "academic", "high", "pending"),
        (user_id, "Store water for hostel maintenance", (today.isoformat() + " 22:00"), "personal", "medium", "pending"),
        (user_id, "Submit Robotics Club resume", ((today + timedelta(days=4)).isoformat()), "club", "low", "pending"),
        (user_id, "Solve 3 LeetCode problems", ((today + timedelta(days=2)).isoformat()), "academic", "medium", "pending"),
    ]
    cursor.executemany("""
        INSERT INTO tasks (user_id, title, due_date, category, priority, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, tasks_data)

    # ── Attendance ──
    attendance_data = [
        (user_id, "Data Structures & Algorithms", 30, 28, 75.0, now.isoformat()),
        (user_id, "Operating Systems", 28, 22, 75.0, now.isoformat()),
        (user_id, "Database Management Systems", 26, 24, 75.0, now.isoformat()),
        (user_id, "Computer Networks", 22, 15, 75.0, now.isoformat()),
        (user_id, "Software Engineering", 18, 16, 75.0, now.isoformat()),
    ]
    cursor.executemany("""
        INSERT INTO attendance (user_id, subject, total_classes, attended, required_pct, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, attendance_data)

    # ── Exam Timetable ──
    exam_data = [
        (user_id, "Operating Systems", (today + timedelta(days=7)).isoformat(), "10:00", "12:00", "Exam Hall A", "mid-sem", "Process Scheduling, Memory Management, Deadlocks, File Systems"),
        (user_id, "Database Management Systems", (today + timedelta(days=9)).isoformat(), "14:00", "16:00", "Exam Hall B", "mid-sem", "ER Diagrams, Normalization, SQL Queries, Transactions"),
        (user_id, "Computer Networks", (today + timedelta(days=11)).isoformat(), "10:00", "12:00", "Exam Hall A", "mid-sem", "OSI Model, TCP/IP, Routing Algorithms, Network Security"),
        (user_id, "Data Structures & Algorithms", (today + timedelta(days=14)).isoformat(), "14:00", "16:00", "Exam Hall C", "mid-sem", "Trees, Graphs, Dynamic Programming, Greedy Algorithms"),
        (user_id, "Software Engineering", (today + timedelta(days=16)).isoformat(), "10:00", "12:00", "Exam Hall B", "mid-sem", "SDLC Models, UML Diagrams, Testing, Agile Methodology"),
    ]
    cursor.executemany("""
        INSERT INTO exam_timetable (user_id, subject, exam_date, start_time, end_time, venue, exam_type, syllabus)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, exam_data)

    # ── Alerts (Proactive Nudges) ──
    alerts_data = [
        (user_id, "CN Attendance Critical", "Computer Networks attendance at 68% — minimum is 75%. Don't miss tomorrow's class!", "critical", (now + timedelta(hours=1)).isoformat(), 0, now.isoformat()),
        (user_id, "DSA Assignment Due Soon", "DSA Assignment 4 due today at 2 PM. You haven't submitted yet.", "warning", (now + timedelta(hours=2)).isoformat(), 0, now.isoformat()),
        (user_id, "TCS Registration Closing", "TCS pre-placement talk registration closes tonight at 11:59 PM.", "warning", (now + timedelta(hours=3)).isoformat(), 0, now.isoformat()),
        (user_id, "Mess Closing Soon", "Dinner mess closes in 30 minutes. Head to the mess now if you haven't eaten.", "info", (now + timedelta(hours=4)).isoformat(), 0, now.isoformat()),
        (user_id, "OS Attendance Warning", "OS attendance at 78% — one more miss drops you to 75%. Attend tomorrow's review session.", "warning", (now + timedelta(hours=5)).isoformat(), 0, now.isoformat()),
    ]
    cursor.executemany("""
        INSERT INTO alerts (user_id, title, body, alert_type, trigger_at, is_sent, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, alerts_data)

    # ── Expenses (This month) ──
    expenses_data = [
        (user_id, 450, "food", "Mess monthly subscription", (now - timedelta(days=25)).isoformat()),
        (user_id, 350, "food", "Swiggy orders (week 1)", (now - timedelta(days=20)).isoformat()),
        (user_id, 400, "transport", "Bus pass monthly", (now - timedelta(days=22)).isoformat()),
        (user_id, 300, "stationery", "Notebooks + pens", (now - timedelta(days=18)).isoformat()),
        (user_id, 200, "entertainment", "Movie night", (now - timedelta(days=15)).isoformat()),
        (user_id, 400, "entertainment", "Gaming subscription + snacks", (now - timedelta(days=12)).isoformat()),
        (user_id, 500, "food", "Restaurant dinner with friends", (now - timedelta(days=10)).isoformat()),
        (user_id, 500, "food", "Canteen + snacks (week 3)", (now - timedelta(days=7)).isoformat()),
        (user_id, 200, "food", "Tea + biscuits daily", (now - timedelta(days=5)).isoformat()),
        (user_id, 280, "food", "Swiggy this week", (now - timedelta(days=2)).isoformat()),
        (user_id, 120, "transport", "Auto rides this week", (now - timedelta(days=1)).isoformat()),
    ]
    cursor.executemany("""
        INSERT INTO expenses (user_id, amount, category, description, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, expenses_data)

    # ── Mood Check-ins ──
    mood_data = [
        (user_id, 2, "Stressed about mid-sems and assignments piling up", (now - timedelta(days=3)).isoformat()),
        (user_id, 2, "CN attendance worry, couldn't sleep well", (now - timedelta(days=2)).isoformat()),
        (user_id, 3, "Managed to finish one assignment, feeling slightly better", (now - timedelta(days=1)).isoformat()),
    ]
    cursor.executemany("""
        INSERT INTO mood_checkins (user_id, mood, note, created_at)
        VALUES (?, ?, ?, ?)
    """, mood_data)

    # ── Placement Applications ──
    placement_data = [
        (user_id, "TCS", "Software Engineer", "Applied", (today - timedelta(days=5)).isoformat(), "Applied through placement portal"),
        (user_id, "Infosys", "Systems Engineer", "Shortlisted", (today - timedelta(days=3)).isoformat(), "Shortlisted after aptitude test"),
        (user_id, "Amazon", "SDE-1", "Interview", (today + timedelta(days=7)).isoformat(), "Interview scheduled for next week — prepare DSA"),
    ]
    cursor.executemany("""
        INSERT INTO placement_apps (user_id, company, role, status, applied_date, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, placement_data)

    conn.commit()
    conn.close()
    print("✅ Database initialized with all tables and sample data for Arjun Sharma")


# ─── CAMPUS FAQ KNOWLEDGE BASE (for RAG) ────────────────────────────────────

CAMPUS_FAQ = [
    {"q": "What is the fee payment deadline?", "a": "Fee payment deadline is the 15th of every month. Late fee of ₹500 applies after that. Pay via the student portal or at the accounts office (Room 102, Admin Block)."},
    {"q": "What are the library hours?", "a": "Library is open Monday-Saturday 8 AM to 9 PM. During exams, extended hours till midnight. Sunday: 10 AM to 5 PM. Student ID required for entry."},
    {"q": "What is the mess menu today?", "a": "Today's mess menu — Breakfast: Poha, bread, tea. Lunch: Dal, rice, roti, paneer, salad. Dinner: Chole, rice, roti, raita, sweet. Timing: B 7:30-9:30, L 12-2, D 7:30-9:30."},
    {"q": "Who is the hostel warden?", "a": "Hostel B Warden: Dr. Ramesh Kumar, Room G-01, Hostel B. Contact: 9845012345. Office hours: 5-7 PM weekdays. For emergencies, call anytime."},
    {"q": "How are exam halls allocated?", "a": "Exam halls are allocated by roll number. 21CS001-21CS050: Exam Hall A. 21CS051-21CS100: Exam Hall B. Check notice board 1 day before exam for final seating."},
    {"q": "Who is the CSE HOD?", "a": "CSE HOD: Dr. Priya Venkatesh, Room 301, CSE Block. Email: hod.cse@college.edu. Office hours: 10 AM - 12 PM weekdays. Appointment required for non-urgent matters."},
    {"q": "How is CGPA calculated?", "a": "CGPA = Sum of (Credit × Grade Points) / Total Credits. Grade points: O=10, A+=9, A=8, B+=7, B=6, C=5, F=0. Minimum 5.0 CGPA required for placement eligibility."},
    {"q": "What is the attendance policy?", "a": "Minimum 75% attendance required in each subject. Below 75%: not eligible to write exam. Below 65%: detained. Medical leave with valid certificate can be adjusted."},
    {"q": "How to contact placement cell?", "a": "Placement Cell: Room 201, Admin Block. Coordinator: Prof. Anil Gupta. Email: placement@college.edu. Phone: 080-12345678. Office hours: 9 AM - 5 PM."},
    {"q": "What scholarships are available?", "a": "Merit scholarship: Top 5% get ₹25,000/year. Need-based: Family income <5L get 50% fee waiver. SC/ST scholarship: Full fee waiver. Apply at scholarship portal by August 31."},
    {"q": "How to apply for medical leave?", "a": "Submit medical certificate to class advisor within 3 days of returning. Fill leave form from academic office. Max 15 days medical leave per semester. HOD approval needed for >7 days."},
    {"q": "When are backlog exams held?", "a": "Backlog exams are held 2 weeks after regular end-sem exams. Registration opens 1 month before. Fee: ₹1000 per subject. Max 3 backlogs allowed per semester."},
    {"q": "What is the campus WiFi password?", "a": "WiFi network: CampusNet. Login with your roll number and DOB (DDMMYYYY) as password. Max 3 devices. Speed: 10 Mbps. Report issues at IT helpdesk, Room 105."},
    {"q": "Where is the printing facility?", "a": "Printing available at Library basement (₹2/page B&W, ₹10/page color) and CSE Lab (free for assignments, max 20 pages/day). Bring your own paper for bulk printing."},
    {"q": "What are the bus route timings?", "a": "Route 1: City Center, 7:30 AM & 5:30 PM. Route 2: Railway Station, 8 AM & 6 PM. Route 3: Suburban, 7:45 AM & 5:45 PM. Route 4: Tech Park, 8:15 AM & 5:45 PM."},
    {"q": "What are the gym hours?", "a": "Campus gym: 6-8 AM and 5-8 PM, Monday to Saturday. Closed Sunday. Registration: ₹500/semester at sports office. Carry sports shoes and towel. Trainer available 6-7 AM."},
    {"q": "How to reach counselling cell?", "a": "Counselling Cell: Room 108, Student Welfare Building. Dr. Meera (Psychologist): Mon/Wed/Fri 10-1. Confidential. Walk-in or book via email: counselling@college.edu. Emergency: 9876000111."},
    {"q": "Who is on the anti-ragging committee?", "a": "Anti-Ragging Committee Chair: Dr. Suresh Babu (Dean). Helpline: 1800-180-5522 (toll-free). WhatsApp: 9845099999. Anonymous complaints accepted. Zero tolerance policy."},
    {"q": "What are sports complex timings?", "a": "Sports complex: 6 AM - 8 PM daily. Cricket/Football ground: book 1 day in advance at sports office. Badminton/TT: first-come basis. Swimming pool: 6-8 AM only, ₹200/month."},
    {"q": "Where is the laundry service?", "a": "Laundry room: Hostel B basement. Self-service machines: ₹30/load wash, ₹20/load dry. Tokens from hostel office. Professional service: ₹80/kg, 24-hour delivery. Closed Sunday."},
    {"q": "What is the dress code?", "a": "Regular days: No strict dress code, but decent attire expected. Lab sessions: Closed shoes mandatory. Exams: College ID card must be worn. No sleeveless in admin block."},
    {"q": "How to get a bonafide certificate?", "a": "Apply at academic office with filled form + ₹50 fee. Processing: 2 working days. Urgent (same day): ₹200. Collect with ID proof. Online request available on student portal."},
    {"q": "What are canteen timings?", "a": "Main canteen: 8 AM - 9 PM. Coffee shop: 9 AM - 6 PM. Night canteen (hostel): 9 PM - 12 AM. Weekend: Main canteen opens at 9 AM. UPI and cash accepted."},
    {"q": "How to book seminar hall?", "a": "Submit booking request to admin office 1 week in advance. Form available online. Faculty advisor signature required. Max booking: 3 hours. AV equipment included. ₹500 deposit for external events."},
    {"q": "What is the grading system?", "a": "Marks to grade: 90+: O, 80-89: A+, 70-79: A, 60-69: B+, 50-59: B, 40-49: C, <40: F. Internal: 40%, External: 60%. Minimum 40% needed in both components to pass."},
    {"q": "How to apply for hostel?", "a": "Hostel allotment: Apply before June 30 on student portal. Priority: Outstation > Distance > CGPA. Fee: ₹45,000/year (includes mess). Room sharing: 2 per room (UG), single (PG)."},
    {"q": "What is the internship policy?", "a": "6th semester: Mandatory 6-week internship. Must be related to branch. Company approval from placement cell needed. Report + presentation required. 4 credits. Start applying by 5th sem."},
    {"q": "Where is the medical facility?", "a": "Health Center: Near main gate, open 24/7 for emergencies. OPD: 9 AM - 5 PM weekdays. Doctor on call after hours. Free consultation + basic medicines for students. Ambulance: 9845011111."},
    {"q": "How to get parking permit?", "a": "Two-wheeler parking: ₹1000/year. Apply at security office with RC copy + ID. Car parking: Not allowed for UG students. Bicycle parking: Free, register at hostel office."},
    {"q": "What clubs can I join?", "a": "Technical: Coding Club, Robotics, AI/ML, Cybersecurity. Cultural: Dance, Music, Drama, Photography. Sports: Cricket, Football, Badminton, Chess. Recruitment: August (odd sem) and January (even sem)."},
]


if __name__ == "__main__":
    # Remove existing DB for fresh start
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
