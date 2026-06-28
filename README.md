# HiringAgent AI — Premium, Unbiased Resume Screening & Portfolio Verification Pipeline

**HiringAgent AI** is a state-of-the-art, merit-first recruiting pipeline designed to screen candidates without bias, while cross-verifying active skills against real public code repositories.

By utilizing a high-performance **decoupled architecture**, this system guarantees smooth real-time AI evaluation streamed token-by-token directly to a sleek, dark-mode dashboard.

---

## 🚀 Product Vision & Features

1. **Strict PII Redaction:** Strips all names, emails, and phone numbers before feeding resumes to the AI engine to guarantee absolute meritocracy and zero hiring bias.
2. **GitHub Enrichment & Cross-Verification:** Automatically extracts the candidate's GitHub URL from their PDF, scrapes their top repositories, and analyzes their READMEs to verify that they actually possess the technical skills they claim in their resume.
3. **SSE Real-Time Streaming:** Streams Llama-3-70b-8192 analysis from FastAPI to Next.js in real time via Server-Sent Events (SSE).
4. **Bento Grid Evaluation Suite:**
   - **Top Left:** Unbiased Summary & Overall Match Score (dynamic glowing arc indicator).
   - **Top Right:** Skills Match Radar Vector Chart (Recharts rendering structural strength).
   - **Bottom Left:** Scanned GitHub Repositories (active validation indicators).
   - **Bottom Right:** Streaming AI Explainability logs in a sleek terminal layout.

---

## 🏗️ Technical Stack & Architecture

We use a decoupled system to bypass serverless limitations:
- **Frontend (Next.js 14+):** Configured for fast page load, state transitions, and responsive rendering on **Vercel**.
- **Backend (FastAPI):** Configured for multi-minute asynchronous AI evaluations on **Render.com** (solving serverless timeouts).
- **Core Libraries:** PyMuPDF (`fitz`), Groq SDK (Llama-3-70b), Framer Motion, Tailwind CSS, Recharts.

---

## 🎨 Design System: Qount Dark Minimal

We strictly adhere to the professional **Qount Dark Minimal** design philosophy:
- **Palette:** Ultra-dark charcoal backgrounds (`#09090b` and `#1a1a1a`) with an energetic neon lime primary accent (`#d9ff42`).
- **Typography:** Stark 'Inter' sans-serif typographic scale with tight letter tracking for an editorial feel.
- **Micro-interactions:** Flat style utilizing high contrast 1px borders, square action controls (0px button radius), and subtle hover glowing transitions.

---

## 📦 Project Directory Structure

```text
├── backend/
│   ├── main.py             # FastAPI App, PII filters, GitHub scraper, LLM streamer
│   └── requirements.txt    # Python Dependencies
├── frontend/
│   ├── package.json        # Node.js Dependencies
│   ├── tsconfig.json       # TypeScript compiler settings
│   ├── tailwind.config.js  # Qount Dark Minimal custom colors & fonts
│   ├── src/
│   │   └── app/
│   │       ├── globals.css # Global scrollbars, glow text, animations
│   │       ├── layout.tsx  # NextJS layout root
│   │       └── page.tsx    # Primary UI dashboard & streaming SSE client
└── README.md               # Deployment & System documentation
```

---

## 🛠️ Step-by-Step Deployment Instructions

### 1. Backend Deployment (Render.com)
1. Sign up/Log in to [Render.com](https://render.com).
2. Click **New +** and select **Web Service**.
3. Link your GitHub repository `KeshavCracks/HiringAgent-AI`.
4. Configure these fields:
   - **Root Directory:** `backend`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Set Environment Variables:
   - `GROQ_API_KEY`: Your Groq platform access key.
6. Click **Deploy**. Copy the public Render URL (e.g., `https://hiringagent-api.onrender.com`).

### 2. Frontend Deployment (Vercel)
1. Sign up/Log in to [Vercel](https://vercel.com).
2. Click **Add New** -> **Project**.
3. Import your GitHub repository `KeshavCracks/HiringAgent-AI`.
4. In **Framework Preset**, select **Next.js**.
5. In **Root Directory**, click edit and select `frontend`.
6. Leave other defaults, then click **Deploy**.
7. Once deployed, launch the URL, input your PDF resume and job description, then click evaluate to watch the pipeline execute in real time!

---

*This elite project is automatically initialized and configured for @KeshavCracks.*
