# 🎬 CampusFlow Demo Video Script

**Total Duration:** 4 minutes  
**Format:** Screen recording + voiceover  
**Tip:** Speak slowly, confidently. Pause when the UI loads. Let the screenshots breathe.

---

## BEFORE RECORDING

```bash
cd /Users/bhavanar/Documents/campusflow/backend
rm -f campusflow.db
python database.py
python main.py
```

Open Chrome → http://localhost:8000 → Full screen (Cmd+Shift+F)  
Do one practice login first to warm up Bedrock, then reset DB and record.

**Recording:** QuickTime → File → New Screen Recording → Microphone ON → System audio OFF

---

## THE SCRIPT

---

### ⏱️ 0:00 – 0:30 | PROBLEM + INTRO

**[SCREEN: Login page visible — dark theme, CampusFlow logo]**

**SAY (slowly, with conviction):**

> "Every college student in India uses 8 to 10 different apps just to get through a single day.
>
> WhatsApp groups for notices. Emails for assignments. A portal for attendance. A spreadsheet for expenses. And they STILL miss deadlines — because a placement registration was buried between memes in a hostel group chat.
>
> 43 million students face this chaos every single day.
>
> We built CampusFlow — one AI assistant that replaces all of it. Built entirely on AWS. Let me show you how it works."

**[Don't click anything yet. Let the login screen sit there looking clean.]**

---

### ⏱️ 0:30 – 1:10 | LOGIN + DASHBOARD

**SAY:**

> "I'm logging in as Arjun — a third-year Computer Science student."

**CLICK:** Click the **"🚀 Demo Login (Arjun Sharma)"** button. Wait for dashboard to load.

**SAY (once dashboard appears):**

> "The moment Arjun opens CampusFlow, he sees everything that matters.
>
> At the top — an AI-generated morning digest, created by Amazon Bedrock. It says: 2 classes today, DSA assignment due at 2 PM, Computer Networks attendance is critically low at 68%.
>
> Below that — four stat cards. 2 classes. 3 tasks due. 6 unread notices. 2 attendance warnings. All at a glance.
>
> On the left — today's full schedule. OS at 9, DBMS at 11, DSA deadline at 2 PM, Coding Club at 4.
>
> On the right — urgent tasks ranked by priority. And below — proactive alerts warning him about things BEFORE they become problems.
>
> Arjun didn't search for any of this. The AI figured out what he needs and showed it to him."

**CLICK:** Scroll down slowly to show stat cards → schedule timeline → tasks → proactive alerts.

---

### ⏱️ 1:10 – 2:00 | CAMPUSBOT (AI CHAT)

**CLICK:** Click **"CampusBot"** in the sidebar.

**SAY:**

> "This is CampusBot — our AI assistant powered by Amazon Bedrock. It doesn't just search a FAQ. It has access to Arjun's real data — his attendance, his schedule, his tasks, and a 30-entry campus knowledge base. Let me show you."

**CLICK:** Click the suggestion bubble **"Can I skip CN today?"** — wait for the response to appear.

**SAY (after response loads):**

> "Look at this response. The AI checked Arjun's actual attendance — Computer Networks, 15 out of 22 classes attended, that's 68.2%. Already below the 75% minimum. It calculated that skipping one more class drops him to 65.2%.
>
> It's not just saying 'your attendance is low.' It's saying: 'Don't skip. You'll be debarred.' That's the difference — it PREDICTS the future impact of today's decision.
>
> This is RAG — Retrieval Augmented Generation. Real student data, fed into Amazon Bedrock, personalized answer in 2 seconds."

**CLICK:** Type **"What's the mess menu?"** and press Enter. Wait for response.

**SAY:**

> "And it handles everyday questions too. Mess menu — pulled from the campus knowledge base. Breakfast: Poha. Lunch: Dal, rice, paneer. Any campus question — instant, accurate answer."

---

### ⏱️ 2:00 – 2:25 | NOTICES

**CLICK:** Click **"Notices"** in the sidebar.

**SAY:**

> "Every notice is automatically summarized by Amazon Bedrock into exactly two lines. Line one — what you need to do. Line two — the deadline.
>
> TCS pre-placement talk — register by tonight 11:59 PM. Mid-sem exams start next Monday. Water shutdown tomorrow 10 to 11 AM — store water tonight.
>
> Each notice is color-coded by urgency — red for urgent, amber for medium, green for low. And tagged by category — Placement, Academic, Hostel, Transport, Club. No wall of text. Just what the student needs to know, in 5 seconds."

**CLICK:** Point at the urgency color bars. Click "Placement" filter to show filtering.

---

### ⏱️ 2:25 – 2:45 | SCHEDULE

**CLICK:** Click **"Schedule"** in the sidebar.

**SAY:**

> "Full weekly timetable — Monday through Saturday. Every event is color-coded. Blue for classes. Purple for labs. Red for deadlines. Amber for exams. Green for clubs.
>
> Today is highlighted. The system auto-detects scheduling clashes — if two events overlap, it flags them in red so the student can fix it before it's too late."

**CLICK:** Point at today's column (highlighted). Scroll to show all days.

---

### ⏱️ 2:45 – 3:05 | EXAMS

**CLICK:** Click **"Exams"** in the sidebar.

**SAY:**

> "Exam countdown. Operating Systems — 7 days left, Exam Hall A, 10 to 12. DBMS — 9 days. CN — 11 days. Each card shows the venue, timing, and syllabus topics to cover.
>
> The student always knows exactly what's coming and how many days they have to prepare. No surprises."

**CLICK:** Point at the countdown numbers and syllabus section.

---

### ⏱️ 3:05 – 3:25 | ATTENDANCE

**CLICK:** Click **"Attendance"** in the sidebar.

**SAY:**

> "Color-coded attendance tracker. Green means safe — DSA at 93%. Amber is a warning — Operating Systems at 78%, one miss away from trouble. And red — Computer Networks at 68%, already below the 75% minimum.
>
> Each card has a can-I-skip calculator. CN says: Cannot skip — would drop to 65.2% — need 7 more consecutive classes to recover. This single feature prevents exam debarment — the number one fear of every Indian college student."

**CLICK:** Scroll through cards. Pause on CN (red).

---

### ⏱️ 3:25 – 3:50 | PERSONAL LIFE

**CLICK:** Click **"Personal Life"** in the sidebar.

**SAY:**

> "Personal life management. Budget — Arjun has spent 3700 of his 5000 rupee monthly budget. The AI suggests: cut entertainment costs, use mess instead of Swiggy, save 200 rupees this week.
>
> Wellness — a daily mood check-in with 5 emojis. Based on 3 days of low mood combined with a dense schedule, the system has flagged high burnout risk. It suggests taking a break or talking to someone.
>
> And a placement tracker — TCS applied, Infosys shortlisted, Amazon interview scheduled next week. All in one kanban board."

**CLICK:** Point at budget bar → mood emojis → burnout card → placement columns.

---

### ⏱️ 3:50 – 4:00 | CLOSING

**CLICK:** Click **"Dashboard"** in the sidebar. Let it load.

**SAY (with finality):**

> "8 screens. 6 AI features. 7 AWS services. Zero servers to manage. Scales from 1 student to 10 million — all serverless.
>
> CampusFlow — because every student deserves an AI that works as hard as they do."

**[Hold on dashboard for 3 seconds. Stop recording.]**

---

## AFTER RECORDING

1. QuickTime → File → Export As → **1080p**
2. Upload to YouTube (unlisted) or Google Drive
3. Share link with me to update PRD + README

---

## KEY TIPS FOR MAXIMUM MARKS

- **Speak like you're explaining to a friend, not reading a script**
- **Pause for 2 seconds after every major statement** — let the jury read the screen
- **Move mouse slowly** — point at what you're talking about
- **The Bedrock response is your wow moment** — pause dramatically after "Can I skip CN?"
- **End strong** — the closing line should feel like a mic drop
- **Don't rush** — 4 minutes is enough. Confidence > speed
