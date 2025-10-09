🧩 Overview
App Name: Reppy

Platform: React Native (using Expo)

Architecture:

Express API server (public)

FastAPI AI server (private, LangChain-powered)

Database:

PostgreSQL for relational data

Vector DB (planned for routine personalization & future dietary modules)

Core Concept:
An AI-powered personal trainer that generates, adjusts, and tracks fitness routines tailored to each user.

🧑‍💻 User-Facing Features (Mobile App)
1. Authentication
Sign up via email + password or social login (Google/Apple)

Token-based session management

Preference storage (unit system, notifications, etc.)

2. Onboarding & Profile Setup
Collects:

Experience level (beginner | intermediate | advanced)

Fitness goal (bulking, cutting, endurance, etc.)

Weekly availability

Age, sex, height, weight

Available gym equipment

Auto-generates a personalized AI routine

3. Routine Generation
LangChain + OpenAI-powered generation based on:

User profile

Equipment availability

Weekly schedule

Training goal

Historical achievement rate (adherence score)

Output is a structured JSON (parsed into a visual UI)

4. Routine Execution UI
Calendar-based routine viewer

Workout details with:

Set type (e.g., pyramid, drop, superset)

Reps/weight/duration

Embedded YouTube or GIF demos

Completion tracking

5. Interactive AI Coach
Long polling chat interface (user ↔ AI)

AI proactively messages users to check in (e.g., “Ready for leg day?”)

Users can say:

"Too tired today" → AI adjusts difficulty

"Add more cardio next week" → routine regenerates with constraints

Realtime RAG (retrieval-augmented generation) planned

6. Push Notifications
Daily workout reminders

Streak encouragement

Check-in messages from the AI

🧠 AI Server (FastAPI: ai-router)
1. Prompt Orchestration
Receives user data via Express proxy

Constructs structured prompts using:

User metadata

Contextual history

Domain knowledge (equipment → exercises)

Calls OpenAI via LangChain

2. Routine Generator
Converts high-level user goals into:

Weekly routine

Daily schedules

Set-level instructions

Embeds AI domain logic (e.g., push/pull splits, progressive overload)

3. Routine Replanner (RAG-based, in progress)
Adjusts future workouts based on:

Missed workouts

User complaints (“too hard” / “too boring”)

Preference changes

Will use vector search against prior AI decisions

🗃️ Backend Features (Express: server)
1. User & Auth APIs
CRUD for user info, preferences, and login

Token verification & refresh

2. Routine Management APIs
Create/read/update/delete routines

Log workout results

Update achievement score

3. Schedule & Notification APIs
User-specific training calendar

Scheduler triggers AI check-ins

SES integration (if email needed in future)
