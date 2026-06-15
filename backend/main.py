"""
CampusFlow — FastAPI Backend
All endpoints with AWS Bedrock integration + rule-based fallback
"""

import os
import json
from datetime import datetime, date, timedelta
from typing import Optional

from dotenv import load_dotenv
# Only load .env on localhost, not on Lambda
if not os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from database import get_db, init_db, hash_password, CAMPUS_FAQ

# ─── APP SETUP ────────────────────────────────────────────────────────────────

app = FastAPI(title="CampusFlow", description="AI Operating System for College Students")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
init_db()

# ─── BEDROCK CLIENT ───────────────────────────────────────────────────────────

bedrock_client = None

try:
    import boto3
    region = os.getenv("AWS_REGION", os.getenv("BEDROCK_REGION", "ap-south-1"))
    
    # On localhost: .env provides AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY
    # On Lambda: no .env loaded, no explicit keys — use IAM role automatically
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    if access_key and secret_key:
        # Localhost — use explicit credentials from .env
        bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
    else:
        # Lambda — use IAM role credentials (automatic)
        bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=region,
        )
    
    # Test connection
    bedrock_client.meta.region_name
    print("✅ AWS Bedrock client initialized")
except Exception as e:
    bedrock_client = None
    print(f"⚠️  Bedrock unavailable ({e}). Using rule-based fallback.")


def call_bedrock(system_prompt: str, user_message: str, max_tokens: int = 500) -> Optional[str]:
    """Call AWS Bedrock Claude Sonnet. Returns None if unavailable."""
    if not bedrock_client:
        return None

    # Try models in order of preference (using inference profile IDs for region compatibility)
    model_ids = [
        "anthropic.claude-3-haiku-20240307-v1:0",
        "apac.anthropic.claude-3-haiku-20240307-v1:0",
        "apac.anthropic.claude-3-5-sonnet-20241022-v2:0",
    ]

    import time
    for model_id in model_ids:
        for attempt in range(2):
            try:
                response = bedrock_client.invoke_model(
                    modelId=model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": max_tokens,
                        "system": system_prompt,
                        "messages": [{"role": "user", "content": user_message}]
                    })
                )
                result = json.loads(response["body"].read())
                return result["content"][0]["text"]
            except Exception as e:
                error_msg = str(e)
                # If throttled, wait and retry once
                if "throttl" in error_msg.lower() or "Too many requests" in error_msg:
                    if attempt == 0:
                        time.sleep(1)
                        continue
                    # Second attempt also throttled, try next model
                    break
                # If it's a model not found/invalid error, try next model
                if "model identifier is invalid" in error_msg or "not found" in error_msg or "not authorized" in error_msg.lower() or "access" in error_msg.lower():
                    break
                # For other errors, return None
                print(f"Bedrock error with {model_id}: {e}")
                return None

    print("Bedrock: All models unavailable, using fallback")
    return None


# ─── PYDANTIC MODELS ──────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    name: str
    password: str

class RegisterRequest(BaseModel):
    name: str
    password: str
    branch: str = "CSE"
    year: int = 3
    roll_no: str = ""
    email: str = ""

class ChatRequest(BaseModel):
    user_id: int
    message: str

class NoticeCreate(BaseModel):
    user_id: int
    title: str
    raw_text: str
    category: str = "academic"
    urgency: str = "medium"
    source: str = "manual"
    deadline: Optional[str] = None

class TaskCreate(BaseModel):
    user_id: int
    title: str
    due_date: Optional[str] = None
    category: str = "academic"
    priority: str = "medium"

class TaskUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    title: Optional[str] = None

class ExpenseCreate(BaseModel):
    user_id: int
    amount: float
    category: str
    description: str = ""

class MoodCreate(BaseModel):
    user_id: int
    mood: int
    note: str = ""

class PlacementCreate(BaseModel):
    user_id: int
    company: str
    role: str
    status: str = "Applied"
    notes: str = ""

class ExamCreate(BaseModel):
    user_id: int
    subject: str
    exam_date: str
    start_time: str = ""
    end_time: str = ""
    venue: str = ""
    exam_type: str = "mid-sem"
    syllabus: str = ""


# ─── AUTH ENDPOINTS ───────────────────────────────────────────────────────────

@app.post("/api/auth/login")
def login(req: LoginRequest):
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE name = ? AND password_hash = ?",
        (req.name, hash_password(req.password))
    ).fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {
        "user_id": user["id"],
        "name": user["name"],
        "branch": user["branch"],
        "year": user["year"],
        "cgpa": user["cgpa"],
        "roll_no": user["roll_no"],
        "email": user["email"],
        "monthly_budget": user["monthly_budget"]
    }


@app.post("/api/auth/register")
def register(req: RegisterRequest):
    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE name = ?", (req.name,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="User already exists")

    cursor = conn.execute(
        "INSERT INTO users (name, password_hash, branch, year, roll_no, email) VALUES (?, ?, ?, ?, ?, ?)",
        (req.name, hash_password(req.password), req.branch, req.year, req.roll_no, req.email)
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return {"user_id": user_id, "name": req.name}


# ─── DASHBOARD ENDPOINT ──────────────────────────────────────────────────────

@app.get("/api/dashboard")
def get_dashboard(user_id: int):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    today = date.today()
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    today_day = days[today.weekday()] if today.weekday() < 6 else "Monday"

    # Today's schedule
    schedule = conn.execute(
        "SELECT * FROM schedule WHERE user_id = ? AND day = ? ORDER BY start_time",
        (user_id, today_day)
    ).fetchall()

    # Classes count (class, lab, or exam — academic events the student needs to attend)
    classes_today = len([s for s in schedule if s["type"] in ("class", "lab", "exam")])

    # Urgent tasks (due today or overdue)
    tasks = conn.execute(
        "SELECT * FROM tasks WHERE user_id = ? AND status = 'pending' ORDER BY priority DESC, due_date ASC",
        (user_id,)
    ).fetchall()
    tasks_due_today = [t for t in tasks if t["due_date"] and t["due_date"].split(" ")[0] <= today.isoformat()]

    # Unread notices
    unread_notices = conn.execute(
        "SELECT COUNT(*) FROM notices WHERE user_id = ? AND is_read = 0", (user_id,)
    ).fetchone()[0]

    # Attendance warnings
    attendance = conn.execute("SELECT * FROM attendance WHERE user_id = ?", (user_id,)).fetchall()
    warnings = []
    for a in attendance:
        pct = round(a["attended"] / a["total_classes"] * 100, 1) if a["total_classes"] > 0 else 100
        if pct < 80:
            status = "critical" if pct < 75 else "warning"
            warnings.append({"subject": a["subject"], "percentage": pct, "status": status})

    # Exams countdown
    exams = conn.execute(
        "SELECT * FROM exam_timetable WHERE user_id = ? AND exam_date >= ? ORDER BY exam_date LIMIT 3",
        (user_id, today.isoformat())
    ).fetchall()
    exam_countdown = []
    for e in exams:
        days_left = (datetime.strptime(e["exam_date"], "%Y-%m-%d").date() - today).days
        exam_countdown.append({"subject": e["subject"], "days_left": days_left, "venue": e["venue"]})

    # AI Morning Digest
    digest = generate_digest(user, schedule, tasks_due_today, warnings, exam_countdown)

    conn.close()

    return {
        "user": {
            "name": user["name"],
            "branch": user["branch"],
            "year": user["year"],
            "cgpa": user["cgpa"],
        },
        "stats": {
            "classes_today": classes_today,
            "tasks_due": len(tasks_due_today),
            "unread_notices": unread_notices,
            "attendance_warnings": len(warnings),
        },
        "schedule_today": [dict(s) for s in schedule],
        "urgent_tasks": [dict(t) for t in tasks_due_today[:5]],
        "attendance_warnings": warnings,
        "exam_countdown": exam_countdown,
        "digest": digest,
    }


def generate_digest(user, schedule, urgent_tasks, warnings, exams):
    """Generate morning digest using Bedrock or fallback."""
    context = f"""
Student: {user['name']}, {user['branch']} Year {user['year']}
Today's classes: {len([s for s in schedule if s['type'] in ('class', 'lab')])}
Urgent tasks: {len(urgent_tasks)} — {', '.join(t['title'] for t in urgent_tasks[:3]) if urgent_tasks else 'None'}
Attendance warnings: {', '.join(f"{w['subject']} ({w['percentage']}%)" for w in warnings) if warnings else 'None'}
Next exam: {exams[0]['subject'] + ' in ' + str(exams[0]['days_left']) + ' days' if exams else 'None upcoming'}
"""

    system_prompt = "Generate a friendly morning digest for this student in under 80 words. Include: most urgent task, attendance warning if any, and one motivating line. Use 1-2 emojis max."

    ai_digest = call_bedrock(system_prompt, context)
    if ai_digest:
        return ai_digest

    # Rule-based fallback
    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
    classes_count = len([s for s in schedule if s["type"] in ("class", "lab")])

    parts = [f"{greeting} {user['name']}! 📚"]
    parts.append(f"You have {classes_count} classes today.")

    if urgent_tasks:
        parts.append(f"Priority: {urgent_tasks[0]['title']} — due today!")

    if warnings:
        w = warnings[0]
        parts.append(f"⚠️ {w['subject']} attendance at {w['percentage']}% — needs attention.")

    if exams:
        parts.append(f"Mid-sem in {exams[0]['days_left']} days — keep revising!")

    parts.append("You've got this. One task at a time. 💪")

    return " ".join(parts)


# ─── CHAT ENDPOINT (CampusBot with RAG) ──────────────────────────────────────

@app.post("/api/chat")
def chat(req: ChatRequest):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (req.user_id,)).fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    # Gather context for RAG
    attendance = conn.execute("SELECT * FROM attendance WHERE user_id = ?", (req.user_id,)).fetchall()
    tasks = conn.execute("SELECT * FROM tasks WHERE user_id = ? AND status = 'pending'", (req.user_id,)).fetchall()
    schedule_today = get_today_schedule(conn, req.user_id)
    notices = conn.execute("SELECT title, summary, urgency FROM notices WHERE user_id = ? ORDER BY created_at DESC LIMIT 5", (req.user_id,)).fetchall()
    exams = conn.execute("SELECT subject, exam_date FROM exam_timetable WHERE user_id = ? ORDER BY exam_date LIMIT 5", (req.user_id,)).fetchall()

    # Get chat history for multi-turn
    history = conn.execute(
        "SELECT role, content FROM chat_history WHERE user_id = ? ORDER BY created_at DESC LIMIT 10",
        (req.user_id,)
    ).fetchall()
    history = list(reversed(history))

    # Build context
    att_info = "\n".join(f"- {a['subject']}: {a['attended']}/{a['total_classes']} = {round(a['attended']/a['total_classes']*100,1)}%" for a in attendance)
    task_info = "\n".join(f"- {t['title']} (due: {t['due_date']}, priority: {t['priority']})" for t in tasks)
    schedule_info = "\n".join(f"- {s['start_time']}-{s['end_time']} {s['title']} at {s['location']}" for s in schedule_today)
    notice_info = "\n".join(f"- [{n['urgency']}] {n['title']}: {n['summary']}" for n in notices)
    exam_info = "\n".join(f"- {e['subject']}: {e['exam_date']}" for e in exams)

    # Find relevant FAQ
    faq_context = find_relevant_faq(req.message)

    context = f"""
STUDENT DATA:
Name: {user['name']}, Branch: {user['branch']}, Year: {user['year']}, CGPA: {user['cgpa']}

ATTENDANCE:
{att_info}

PENDING TASKS:
{task_info}

TODAY'S SCHEDULE:
{schedule_info}

RECENT NOTICES:
{notice_info}

UPCOMING EXAMS:
{exam_info}

CAMPUS FAQ:
{faq_context}
"""

    system_prompt = """You are CampusFlow, an AI assistant for college students. You have access to the student's schedule, attendance, tasks, notices, and campus FAQ. Be friendly, concise, and proactive. If attendance is below 75%, warn the student clearly. Never make up information. Always prioritize the student's wellbeing. Keep responses under 100 words unless the question needs more detail."""

    # Try Bedrock first
    full_message = f"Student context:\n{context}\n\nStudent's question: {req.message}"
    ai_response = call_bedrock(system_prompt, full_message, max_tokens=300)

    if not ai_response:
        # Rule-based fallback
        ai_response = rule_based_chat(req.message, attendance, tasks, schedule_today, notices, exams)

    # Save to chat history
    conn.execute("INSERT INTO chat_history (user_id, role, content) VALUES (?, 'user', ?)", (req.user_id, req.message))
    conn.execute("INSERT INTO chat_history (user_id, role, content) VALUES (?, 'assistant', ?)", (req.user_id, ai_response))
    conn.commit()
    conn.close()

    return {"response": ai_response}


def find_relevant_faq(query: str) -> str:
    """Find relevant FAQ entries using keyword matching."""
    query_lower = query.lower()
    relevant = []
    for faq in CAMPUS_FAQ:
        # Check if any words from the FAQ question appear in the user query
        faq_words = set(faq["q"].lower().split())
        query_words = set(query_lower.split())
        overlap = faq_words & query_words
        if len(overlap) >= 2 or any(word in query_lower for word in ["fee", "library", "mess", "menu", "hostel", "warden", "exam", "hall", "hod", "cgpa", "gpa", "attendance", "placement", "scholarship", "medical", "leave", "backlog", "wifi", "password", "printing", "bus", "route", "gym", "counselling", "ragging", "sports", "laundry", "canteen", "parking", "club"]):
            if any(keyword in query_lower for keyword in faq["q"].lower().split()):
                relevant.append(f"Q: {faq['q']}\nA: {faq['a']}")
    return "\n\n".join(relevant[:3]) if relevant else "No specific FAQ match found."


def rule_based_chat(message: str, attendance, tasks, schedule_today, notices, exams) -> str:
    """Rule-based chat fallback when Bedrock is unavailable."""
    msg = message.lower()

    # Attendance questions
    if "skip" in msg or "attendance" in msg or "absent" in msg or "miss" in msg:
        for a in attendance:
            subject_lower = a["subject"].lower()
            # Check if subject mentioned
            subject_keywords = subject_lower.split()
            if any(kw in msg for kw in subject_keywords) or any(abbr in msg for abbr in get_abbreviations(a["subject"])):
                total = a["total_classes"]
                attended = a["attended"]
                pct = round(attended / total * 100, 1)
                new_pct = round(attended / (total + 1) * 100, 1)

                if pct < 75:
                    return f"🚨 No! Your {a['subject']} attendance is already at {pct}% — below the 75% minimum. Missing another class drops it to {new_pct}%. You need to attend every remaining class. Don't skip this one!"
                elif new_pct < 75:
                    return f"⚠️ Risky! Your {a['subject']} attendance is {pct}%. If you skip, it drops to {new_pct}% — below the 75% minimum. I'd recommend attending today."
                else:
                    return f"✅ Yes, you can skip {a['subject']} today. Your attendance is {pct}%, and it'll drop to {new_pct}% which is still safe (minimum 75%). But don't make it a habit!"

        # General attendance query
        warnings = []
        for a in attendance:
            pct = round(a["attended"] / a["total_classes"] * 100, 1)
            if pct < 80:
                status = "🚨 CRITICAL" if pct < 75 else "⚠️ Warning"
                warnings.append(f"{status}: {a['subject']} — {pct}%")
        if warnings:
            return "Here's your attendance status:\n" + "\n".join(warnings) + "\n\nFocus on attending classes below 80%!"
        return "Your attendance is looking good across all subjects! Keep it up. 💪"

    # Task/assignment questions
    if "due" in msg or "task" in msg or "assignment" in msg or "pending" in msg or "what's due" in msg:
        if tasks:
            task_list = "\n".join(f"• {t['title']} — due {t['due_date']} [{t['priority'].upper()}]" for t in tasks[:5])
            return f"Here's what's pending:\n{task_list}\n\nStart with the HIGH priority ones!"
        return "No pending tasks right now. Great time to get ahead on revision! 📖"

    # Schedule questions
    if "schedule" in msg or "class" in msg or "today" in msg or "timetable" in msg:
        if schedule_today:
            sched = "\n".join(f"• {s['start_time']}-{s['end_time']} — {s['title']} ({s['location']})" for s in schedule_today)
            return f"Today's schedule:\n{sched}"
        return "No classes scheduled for today! Use this time to study or relax. 🎉"

    # Notice questions
    if "notice" in msg or "announcement" in msg or "update" in msg:
        if notices:
            notice_list = "\n".join(f"• [{n['urgency'].upper()}] {n['title']}" for n in notices[:4])
            return f"Recent notices:\n{notice_list}\n\nCheck the Notices tab for full details."
        return "No new notices at the moment."

    # Exam questions
    if "exam" in msg or "mid-sem" in msg or "midsem" in msg:
        if exams:
            today_date = date.today()
            exam_list = []
            for e in exams:
                days_left = (datetime.strptime(e["exam_date"], "%Y-%m-%d").date() - today_date).days
                exam_list.append(f"• {e['subject']} — in {days_left} days")
            return f"Upcoming exams:\n" + "\n".join(exam_list) + "\n\nStart with the nearest one. You've got this! 📝"
        return "No upcoming exams found in the system."

    # FAQ keyword matching
    faq_response = search_faq(msg)
    if faq_response:
        return faq_response

    # Default
    return "I'm here to help with your campus life! You can ask me about attendance, assignments, schedule, notices, exams, or any campus info. What do you need? 😊"


def get_abbreviations(subject: str) -> list:
    """Get common abbreviations for subjects."""
    abbr_map = {
        "Data Structures & Algorithms": ["dsa", "ds", "algo"],
        "Operating Systems": ["os"],
        "Database Management Systems": ["dbms", "database"],
        "Computer Networks": ["cn", "networks", "networking"],
        "Software Engineering": ["se", "software"],
    }
    return abbr_map.get(subject, [])


def search_faq(query: str) -> Optional[str]:
    """Search FAQ knowledge base."""
    for faq in CAMPUS_FAQ:
        q_words = faq["q"].lower().split()
        important_words = [w for w in q_words if len(w) > 3]
        matches = sum(1 for w in important_words if w in query)
        if matches >= 2:
            return f"{faq['a']}"
    return None


def get_today_schedule(conn, user_id: int) -> list:
    """Get today's schedule."""
    today = date.today()
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    today_day = days[today.weekday()] if today.weekday() < 6 else "Monday"
    return conn.execute(
        "SELECT * FROM schedule WHERE user_id = ? AND day = ? ORDER BY start_time",
        (user_id, today_day)
    ).fetchall()


# ─── NOTICES ENDPOINTS ────────────────────────────────────────────────────────

@app.get("/api/notices")
def get_notices(user_id: int):
    conn = get_db()
    notices = conn.execute(
        "SELECT * FROM notices WHERE user_id = ? ORDER BY CASE urgency WHEN 'urgent' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, created_at DESC",
        (user_id,)
    ).fetchall()

    # Auto-summarize notices that don't have a summary yet
    results = []
    for n in notices:
        n_dict = dict(n)
        if not n_dict.get("summary") and n_dict.get("raw_text"):
            summary = summarize_notice(n_dict["raw_text"])
            n_dict["summary"] = summary
            # Save generated summary to DB
            conn.execute("UPDATE notices SET summary = ? WHERE id = ?", (summary, n_dict["id"]))
            conn.commit()
        results.append(n_dict)

    conn.close()
    return {"notices": results}


@app.post("/api/notices")
def create_notice(req: NoticeCreate):
    conn = get_db()

    # Generate summary using Bedrock or fallback
    summary = summarize_notice(req.raw_text)

    cursor = conn.execute(
        "INSERT INTO notices (user_id, title, raw_text, summary, category, urgency, source, deadline) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (req.user_id, req.title, req.raw_text, summary, req.category, req.urgency, req.source, req.deadline)
    )
    conn.commit()
    notice_id = cursor.lastrowid
    conn.close()
    return {"id": notice_id, "summary": summary}


def summarize_notice(raw_text: str) -> str:
    """Summarize notice using Bedrock or fallback."""
    system_prompt = "Summarize this campus notice in exactly 2 lines. Line 1: the key action or information. Line 2: deadline or impact on the student. Be direct and student-friendly. No bullet points."

    ai_summary = call_bedrock(system_prompt, raw_text, max_tokens=100)
    if ai_summary:
        return ai_summary

    # Rule-based fallback: take first two sentences
    sentences = raw_text.replace("\n", " ").split(".")
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) >= 2:
        return f"{sentences[0]}. {sentences[1]}."
    return sentences[0] + "." if sentences else raw_text[:100]


@app.patch("/api/notices/{notice_id}/read")
def mark_notice_read(notice_id: int):
    conn = get_db()
    conn.execute("UPDATE notices SET is_read = 1 WHERE id = ?", (notice_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


# ─── SCHEDULE ENDPOINTS ──────────────────────────────────────────────────────

@app.get("/api/schedule")
def get_schedule(user_id: int):
    conn = get_db()
    schedule = conn.execute(
        "SELECT * FROM schedule WHERE user_id = ? ORDER BY CASE day WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 END, start_time",
        (user_id,)
    ).fetchall()
    conn.close()

    # Group by day
    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    grouped = {day: [] for day in days_order}
    for s in schedule:
        if s["day"] in grouped:
            grouped[s["day"]].append(dict(s))

    # Detect clashes
    clashes = detect_clashes(schedule)

    return {"schedule": grouped, "clashes": clashes}


def detect_clashes(schedule) -> list:
    """Detect scheduling conflicts."""
    clashes = []
    by_day = {}
    for s in schedule:
        by_day.setdefault(s["day"], []).append(s)

    for day, events in by_day.items():
        for i in range(len(events)):
            for j in range(i + 1, len(events)):
                e1, e2 = events[i], events[j]
                # Check overlap
                if e1["start_time"] < e2["end_time"] and e2["start_time"] < e1["end_time"]:
                    clashes.append({
                        "day": day,
                        "event1": e1["title"],
                        "event2": e2["title"],
                        "time": f"{e1['start_time']}-{e1['end_time']} vs {e2['start_time']}-{e2['end_time']}"
                    })
    return clashes


# ─── ATTENDANCE ENDPOINTS ─────────────────────────────────────────────────────

@app.get("/api/attendance")
def get_attendance(user_id: int):
    conn = get_db()
    attendance = conn.execute("SELECT * FROM attendance WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()

    result = []
    for a in attendance:
        pct = round(a["attended"] / a["total_classes"] * 100, 1) if a["total_classes"] > 0 else 100
        status = "critical" if pct < 75 else "warning" if pct < 80 else "safe"

        # Can-I-Skip calculator
        new_pct = round(a["attended"] / (a["total_classes"] + 1) * 100, 1)
        can_skip = new_pct >= 75

        # Classes needed to reach 75%
        classes_needed = 0
        if pct < 75:
            # Need: (attended + x) / (total + x) >= 0.75
            # attended + x >= 0.75 * total + 0.75 * x
            # 0.25x >= 0.75*total - attended
            needed = (0.75 * a["total_classes"] - a["attended"]) / 0.25
            classes_needed = max(0, int(needed) + 1)

        result.append({
            "id": a["id"],
            "subject": a["subject"],
            "total_classes": a["total_classes"],
            "attended": a["attended"],
            "percentage": pct,
            "status": status,
            "can_skip": can_skip,
            "if_skip_pct": new_pct,
            "classes_needed_for_75": classes_needed,
        })

    return {"attendance": result}


@app.post("/api/attendance/{att_id}/mark")
def mark_attendance(att_id: int, attended: bool = True):
    conn = get_db()
    if attended:
        conn.execute("UPDATE attendance SET total_classes = total_classes + 1, attended = attended + 1, updated_at = ? WHERE id = ?", (datetime.now().isoformat(), att_id))
    else:
        conn.execute("UPDATE attendance SET total_classes = total_classes + 1, updated_at = ? WHERE id = ?", (datetime.now().isoformat(), att_id))
    conn.commit()
    conn.close()
    return {"status": "ok"}


# ─── TASKS ENDPOINTS ─────────────────────────────────────────────────────────

@app.get("/api/tasks")
def get_tasks(user_id: int):
    conn = get_db()
    tasks = conn.execute(
        "SELECT * FROM tasks WHERE user_id = ? ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, due_date ASC",
        (user_id,)
    ).fetchall()
    conn.close()
    return {"tasks": [dict(t) for t in tasks]}


@app.post("/api/tasks")
def create_task(req: TaskCreate):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO tasks (user_id, title, due_date, category, priority) VALUES (?, ?, ?, ?, ?)",
        (req.user_id, req.title, req.due_date, req.category, req.priority)
    )
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    return {"id": task_id}


@app.patch("/api/tasks/{task_id}")
def update_task(task_id: int, req: TaskUpdate):
    conn = get_db()
    updates = []
    params = []
    if req.status:
        updates.append("status = ?")
        params.append(req.status)
    if req.priority:
        updates.append("priority = ?")
        params.append(req.priority)
    if req.title:
        updates.append("title = ?")
        params.append(req.title)

    if updates:
        params.append(task_id)
        conn.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    conn.close()
    return {"status": "ok"}


# ─── EXAMS ENDPOINTS ─────────────────────────────────────────────────────────

@app.get("/api/exams")
def get_exams(user_id: int):
    conn = get_db()
    exams = conn.execute(
        "SELECT * FROM exam_timetable WHERE user_id = ? ORDER BY exam_date",
        (user_id,)
    ).fetchall()
    conn.close()

    today = date.today()
    result = []
    for e in exams:
        days_left = (datetime.strptime(e["exam_date"], "%Y-%m-%d").date() - today).days
        result.append({**dict(e), "days_left": days_left})

    return {"exams": result}


@app.post("/api/exams")
def create_exam(req: ExamCreate):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO exam_timetable (user_id, subject, exam_date, start_time, end_time, venue, exam_type, syllabus) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (req.user_id, req.subject, req.exam_date, req.start_time, req.end_time, req.venue, req.exam_type, req.syllabus)
    )
    conn.commit()
    exam_id = cursor.lastrowid
    conn.close()
    return {"id": exam_id}


# ─── NUDGES/ALERTS ENDPOINT ──────────────────────────────────────────────────

@app.get("/api/nudges")
def get_nudges(user_id: int):
    conn = get_db()

    # Get existing alerts
    alerts = conn.execute(
        "SELECT * FROM alerts WHERE user_id = ? ORDER BY CASE alert_type WHEN 'critical' THEN 1 WHEN 'warning' THEN 2 ELSE 3 END, trigger_at ASC",
        (user_id,)
    ).fetchall()

    # Generate dynamic nudges based on current data
    dynamic_nudges = generate_nudges(conn, user_id)

    conn.close()

    return {
        "alerts": [dict(a) for a in alerts],
        "dynamic_nudges": dynamic_nudges
    }


def generate_nudges(conn, user_id: int) -> list:
    """Generate proactive nudges based on student data."""
    nudges = []
    today = date.today()

    # Attendance nudges
    attendance = conn.execute("SELECT * FROM attendance WHERE user_id = ?", (user_id,)).fetchall()
    for a in attendance:
        pct = round(a["attended"] / a["total_classes"] * 100, 1) if a["total_classes"] > 0 else 100
        if pct < 75:
            nudges.append({
                "title": f"{a['subject']} Attendance Critical",
                "body": f"Attendance at {pct}% — below 75% minimum. Attend every remaining class!",
                "type": "critical",
                "category": "attendance"
            })
        elif pct < 80:
            new_pct = round(a["attended"] / (a["total_classes"] + 1) * 100, 1)
            nudges.append({
                "title": f"{a['subject']} Attendance Warning",
                "body": f"Attendance at {pct}%. Missing one more drops to {new_pct}%.",
                "type": "warning",
                "category": "attendance"
            })

    # Task deadline nudges
    tasks = conn.execute(
        "SELECT * FROM tasks WHERE user_id = ? AND status = 'pending'", (user_id,)
    ).fetchall()
    for t in tasks:
        if t["due_date"]:
            due_str = t["due_date"].split(" ")[0]
            try:
                due_date = datetime.strptime(due_str, "%Y-%m-%d").date()
                days_until = (due_date - today).days
                if days_until == 0:
                    nudges.append({
                        "title": f"{t['title']} Due Today!",
                        "body": f"Due today — submit before the deadline!",
                        "type": "critical",
                        "category": "deadline"
                    })
                elif days_until == 1:
                    nudges.append({
                        "title": f"{t['title']} Due Tomorrow",
                        "body": f"Due tomorrow. Start now if you haven't already.",
                        "type": "warning",
                        "category": "deadline"
                    })
            except ValueError:
                pass

    # Budget nudge
    expenses = conn.execute(
        "SELECT SUM(amount) as total FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchone()
    user = conn.execute("SELECT monthly_budget FROM users WHERE id = ?", (user_id,)).fetchone()
    if expenses and user and expenses["total"]:
        spent = expenses["total"]
        budget = user["monthly_budget"]
        if spent > budget * 0.8:
            remaining = budget - spent
            nudges.append({
                "title": "Budget Alert",
                "body": f"Spent ₹{int(spent)} of ₹{int(budget)}. Only ₹{int(remaining)} left — try mess this week!",
                "type": "warning",
                "category": "budget"
            })

    return nudges


# ─── PERSONAL LIFE ENDPOINTS ─────────────────────────────────────────────────

@app.get("/api/personal/overview")
def personal_overview(user_id: int):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    # Budget
    expenses_total = conn.execute(
        "SELECT SUM(amount) as total FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchone()
    total_spent = expenses_total["total"] or 0
    budget = user["monthly_budget"] or 5000

    # This week expenses
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    week_expenses = conn.execute(
        "SELECT SUM(amount) as total FROM expenses WHERE user_id = ? AND created_at >= ?",
        (user_id, week_ago)
    ).fetchone()
    this_week = week_expenses["total"] or 0

    # Category breakdown
    categories = conn.execute(
        "SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ? GROUP BY category",
        (user_id,)
    ).fetchall()

    # Mood
    recent_moods = conn.execute(
        "SELECT * FROM mood_checkins WHERE user_id = ? ORDER BY created_at DESC LIMIT 7",
        (user_id,)
    ).fetchall()
    avg_mood = sum(m["mood"] for m in recent_moods) / len(recent_moods) if recent_moods else 3

    # Burnout detection
    today = date.today()
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    today_day = days[today.weekday()] if today.weekday() < 6 else "Monday"
    today_events = conn.execute(
        "SELECT COUNT(*) as cnt FROM schedule WHERE user_id = ? AND day = ?",
        (user_id, today_day)
    ).fetchone()
    schedule_density = today_events["cnt"] if today_events else 0
    burnout_risk = "high" if schedule_density >= 6 and avg_mood < 3 else "medium" if avg_mood < 3 or schedule_density >= 5 else "low"

    # Placements
    placements = conn.execute(
        "SELECT * FROM placement_apps WHERE user_id = ? ORDER BY applied_date DESC",
        (user_id,)
    ).fetchall()

    # Budget tip
    budget_tip = generate_budget_tip(total_spent, budget, categories)

    conn.close()

    return {
        "budget": {
            "monthly_budget": budget,
            "total_spent": total_spent,
            "remaining": budget - total_spent,
            "this_week": this_week,
            "percentage_used": round(total_spent / budget * 100, 1),
            "categories": [{"category": c["category"], "amount": c["total"]} for c in categories],
            "tip": budget_tip,
        },
        "wellness": {
            "recent_moods": [dict(m) for m in recent_moods],
            "avg_mood": round(avg_mood, 1),
            "burnout_risk": burnout_risk,
            "schedule_density": schedule_density,
        },
        "placements": [dict(p) for p in placements],
    }


def generate_budget_tip(spent: float, budget: float, categories) -> str:
    """Generate budget tip using Bedrock or fallback."""
    cat_str = ", ".join(f"{c['category']}=₹{int(c['total'])}" for c in categories)
    context = f"Monthly budget: ₹{int(budget)}. Spent: ₹{int(spent)}. Remaining: ₹{int(budget-spent)}. Categories: {cat_str}."

    system_prompt = "Give one specific, actionable budget tip for this college student in under 25 words. Be friendly and practical. Reference specific numbers."

    ai_tip = call_bedrock(system_prompt, context, max_tokens=50)
    if ai_tip:
        return ai_tip

    # Fallback
    remaining = budget - spent
    pct = spent / budget * 100
    if pct > 80:
        return f"Spent ₹{int(spent)} of ₹{int(budget)} — try mess this week instead of Swiggy, saves ₹200+!"
    elif pct > 60:
        return f"₹{int(remaining)} left this month. You're on track — keep food expenses in check."
    else:
        return f"Great budgeting! ₹{int(remaining)} remaining. You've got room for a treat this weekend. 🎉"


@app.post("/api/personal/expense")
def add_expense(req: ExpenseCreate):
    conn = get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, description) VALUES (?, ?, ?, ?)",
        (req.user_id, req.amount, req.category, req.description)
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.get("/api/personal/expenses")
def get_expenses(user_id: int):
    conn = get_db()
    expenses = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return {"expenses": [dict(e) for e in expenses]}


@app.post("/api/personal/mood")
def add_mood(req: MoodCreate):
    conn = get_db()
    conn.execute(
        "INSERT INTO mood_checkins (user_id, mood, note) VALUES (?, ?, ?)",
        (req.user_id, req.mood, req.note)
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.get("/api/personal/wellness")
def get_wellness(user_id: int):
    conn = get_db()
    moods = conn.execute(
        "SELECT * FROM mood_checkins WHERE user_id = ? ORDER BY created_at DESC LIMIT 14",
        (user_id,)
    ).fetchall()
    conn.close()

    avg_mood = sum(m["mood"] for m in moods) / len(moods) if moods else 3
    return {
        "moods": [dict(m) for m in moods],
        "avg_mood": round(avg_mood, 1),
        "total_checkins": len(moods),
    }


@app.get("/api/personal/placement")
def get_placements(user_id: int):
    conn = get_db()
    placements = conn.execute(
        "SELECT * FROM placement_apps WHERE user_id = ? ORDER BY applied_date DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return {"placements": [dict(p) for p in placements]}


@app.post("/api/personal/placement")
def add_placement(req: PlacementCreate):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO placement_apps (user_id, company, role, status, applied_date, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (req.user_id, req.company, req.role, req.status, date.today().isoformat(), req.notes)
    )
    conn.commit()
    placement_id = cursor.lastrowid
    conn.close()
    return {"id": placement_id}


# ─── SUMMARY ENDPOINT ────────────────────────────────────────────────────────

@app.get("/api/summary")
def get_summary(user_id: int):
    """AI-generated summary of student's overall status."""
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    attendance = conn.execute("SELECT * FROM attendance WHERE user_id = ?", (user_id,)).fetchall()
    tasks = conn.execute("SELECT * FROM tasks WHERE user_id = ? AND status = 'pending'", (user_id,)).fetchall()
    exams = conn.execute("SELECT * FROM exam_timetable WHERE user_id = ? ORDER BY exam_date LIMIT 3", (user_id,)).fetchall()
    conn.close()

    context = f"""
Student: {user['name']}, CGPA: {user['cgpa']}
Attendance: {', '.join(f"{a['subject']}: {round(a['attended']/a['total_classes']*100,1)}%" for a in attendance)}
Pending tasks: {len(tasks)}
Next exam: {exams[0]['subject'] if exams else 'None'} in {(datetime.strptime(exams[0]['exam_date'], '%Y-%m-%d').date() - date.today()).days if exams else 'N/A'} days
"""

    system_prompt = "Give a brief 3-sentence status summary for this student. Mention the most critical issue, one positive thing, and one actionable advice. Be warm and motivating."

    ai_summary = call_bedrock(system_prompt, context, max_tokens=150)
    if ai_summary:
        return {"summary": ai_summary}

    # Fallback
    critical_subjects = [a["subject"] for a in attendance if a["attended"] / a["total_classes"] * 100 < 75]
    summary = f"Hey {user['name']}! "
    if critical_subjects:
        summary += f"Priority: {critical_subjects[0]} attendance needs immediate attention. "
    summary += f"You have {len(tasks)} pending tasks. "
    if exams:
        days_left = (datetime.strptime(exams[0]["exam_date"], "%Y-%m-%d").date() - date.today()).days
        summary += f"First exam ({exams[0]['subject']}) in {days_left} days — start revising! "
    summary += "Take it one step at a time. You're doing better than you think! 💪"

    return {"summary": summary}


# ─── SERVE FRONTEND ──────────────────────────────────────────────────────────

frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")

@app.get("/")
def serve_frontend():
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "CampusFlow API is running. Frontend not found at ../frontend/index.html"}


# Serve static files from frontend directory
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


# ─── RUN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("🚀 CampusFlow starting on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
