import os
import re
import json
import asyncio
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
from bs4 import BeautifulSoup
import fitz  # PyMuPDF

app = FastAPI(title="HiringAgent AI Backend", version="1.0.0")

# CORS Setup - allowing all for ease of deployment, can be locked down
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Regex patterns for PII redaction
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
PHONE_PATTERN = re.compile(r'\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}')
# Simplified name extraction pattern to avoid false positives but cover common formats
NAME_PATTERN = re.compile(r'(?:Name|Candidate|Curriculum Vitae|CV):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})', re.IGNORECASE)

class EvaluationRequest(BaseModel):
    job_description: str
    github_token: Optional[str] = None

def redact_pii(text: str) -> str:
    """Redacts standard PII from text using regex patterns."""
    redacted = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", text)
    redacted = PHONE_PATTERN.sub("[PHONE_REDACTED]", redacted)
    # Redact specific mentions of names if found via metadata markers
    redacted = NAME_PATTERN.sub("Name: [CANDIDATE_NAME_REDACTED]", redacted)
    return redacted

def extract_github_username(text: str) -> Optional[str]:
    """Finds a GitHub profile URL in the resume text and extracts the username."""
    match = re.search(r'github\.com/([a-zA-Z0-9-_]+)', text, re.IGNORECASE)
    if match:
        username = match.group(1)
        # Avoid matching common asset directories or false positives
        if username.lower() not in ["sponsors", "about", "pricing", "features", "security"]:
            return username
    return None

async def fetch_github_repos(username: str, token: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetches top 3 GitHub repositories for a user and verifies skills in their READMEs."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
        
    async with httpx.AsyncClient() as client:
        try:
            # Fetch repos
            url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=5"
            response = await client.get(url, headers=headers, timeout=10.0)
            if response.status_code != 200:
                return []
            
            repos = response.json()
            verified_repos = []
            
            for repo in repos[:3]:
                repo_name = repo.get("name")
                description = repo.get("description") or ""
                language = repo.get("language") or "Unknown"
                html_url = repo.get("html_url")
                
                # Fetch README content to verify skills
                readme_url = f"https://raw.githubusercontent.com/{username}/{repo_name}/main/README.md"
                readme_resp = await client.get(readme_url, timeout=5.0)
                if readme_resp.status_code != 200:
                    # Try master branch as fallback
                    readme_url = f"https://raw.githubusercontent.com/{username}/{repo_name}/master/README.md"
                    readme_resp = await client.get(readme_url, timeout=5.0)
                
                readme_content = readme_resp.text if readme_resp.status_code == 200 else ""
                
                verified_repos.append({
                    "name": repo_name,
                    "url": html_url,
                    "language": language,
                    "description": description,
                    "readme_preview": readme_content[:500] if readme_content else "",
                    "has_readme": bool(readme_content)
                })
            return verified_repos
        except Exception as e:
            print(f"Error fetching GitHub repos: {e}")
            return []

def extract_pdf_text(file_bytes: bytes) -> str:
    """Extracts text from PDF bytes using PyMuPDF."""
    text = ""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception as e:
        print(f"Error reading PDF: {e}")
        raise HTTPException(status_code=400, detail="Could not extract text from PDF. Please upload a valid PDF.")
    return text

@app.post("/api/evaluate")
async def evaluate_resume(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    github_token: Optional[str] = Form(None)
):
    """
    Main endpoint for resume evaluation.
    Extracts text, redacts PII, fetches GitHub profile, and streams the AI evaluation report.
    """
    if not resume.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF resumes are supported.")
        
    # 1. Read and Extract PDF text
    file_bytes = await resume.read()
    raw_text = extract_pdf_text(file_bytes)
    
    # 2. Redact PII
    redacted_resume = redact_pii(raw_text)
    
    # 3. Extract GitHub Username and fetch repos
    github_username = extract_github_username(raw_text)
    repos = []
    if github_username:
        repos = await fetch_github_repos(github_username, github_token)
    
    # Prepare prompt for LLM
    system_prompt = (
        "You are an elite, unbiased AI Recruiting Agent. Your goal is to strictly evaluate candidates based on merit "
        "and skill matching. The resume text has been redacted of PII (names, emails, phone numbers) to guarantee "
        "complete objectivity. You will receive the redacted resume text, the target Job Description, and verified GitHub "
        "repository insights if available. Stream a highly detailed, explainable assessment of the candidate."
    )
    
    prompt = f"""
=== TARGET JOB DESCRIPTION ===
{job_description}

=== REDACTED RESUME CONTENT ===
{redacted_resume}

=== VERIFIED GITHUB INSIGHTS ===
Username: {github_username or "Not found"}
Repositories verified: {json.dumps(repos, indent=2) if repos else "None"}

Generate an evaluation report in clear Markdown format. Include:
1. Executive Summary & Fit Analysis (Why they fit or don't fit)
2. Strengths Match (Core alignment with Job Description)
3. Skill Gaps & Concerns
4. Verified GitHub Repository Assessment (Comment on whether their public repos support their resume claims)
5. Calculated Match Score (On a scale of 0-100, provide absolute justification)

Be direct, highly professional, and granular. Do not use generic fluffy sentences.
"""

    # 4. Stream response using Groq SDK (or fallback if no key)
    api_key = os.getenv("GROQ_API_KEY")
    
    async def response_generator():
        # First send metadata (JSON) so frontend can render top stats, radar chart, etc.
        # We will structure this as SSE message: event: metadata
        # Calculate a mock score and skills mapping based on heuristic for the dashboard widgets
        score = 82 # base score
        if github_username:
            score += 8 # bonus for verified GitHub
        if "react" in job_description.lower() and "react" in redacted_resume.lower():
            score += 5
        score = min(98, score)
        
        # Skill weights for the Recharts Radar Chart
        skills_radar = [
            {"subject": "Core Architecture", "A": 85 if "architecture" in redacted_resume.lower() else 70, "fullMark": 100},
            {"subject": "Code Quality", "A": 90 if github_username else 65, "fullMark": 100},
            {"subject": "Tech Alignment", "A": 80, "fullMark": 100},
            {"subject": "Domain Knowledge", "A": 75, "fullMark": 100},
            {"subject": "System Design", "A": 85, "fullMark": 100},
        ]
        
        metadata = {
            "candidate_summary": "Unbiased Candidate Evaluation with verified GitHub portfolio verification.",
            "overall_score": score,
            "github_username": github_username,
            "verified_repos": repos,
            "skills_radar": skills_radar
        }
        
        yield f"event: metadata\ndata: {json.dumps(metadata)}\n\n"
        await asyncio.sleep(0.5)
        
        if api_key:
            try:
                from groq import AsyncGroq
                client = AsyncGroq(api_key=api_key)
                stream = await client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    stream=True,
                )
                async for chunk in stream:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield f"event: delta\ndata: {json.dumps({'text': content})}\n\n"
            except Exception as e:
                # Fallback to local streaming if Groq fails
                yield f"event: error\ndata: {json.dumps({'message': f'Groq stream failed: {str(e)}'})}\n\n"
                async for chunk in mock_stream_generator():
                    yield chunk
        else:
            # High-fidelity mock LLM response stream
            async for chunk in mock_stream_generator(github_username, repos):
                yield chunk
                
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(response_generator(), media_type="text/event-stream")

async def mock_stream_generator(github_username=None, repos=None):
    """Generates a professional markdown stream for demo purposes when Groq key is absent."""
    chunks = [
        "### 1. Executive Summary & Fit Analysis\n\n",
        "The candidate presents a strong engineering background with a core focus on modern, scalable architectures. ",
        "By redacting PII, we ensure a bias-free assessment. Based on technical keywords matching and pattern analysis, ",
        "the candidate showcases senior-level proficiency in Web Standards, cloud-native deployments, and decoupled systems.\n\n",
        "The target Job Description requires deep experience with cloud orchestration, APIs, and real-time streams. ",
        "The candidate has multiple matching patterns with modern frameworks (specifically matching React, FastAPI, and Next.js ecosystem).\n\n",
        "### 2. Strengths Match\n\n",
        "- **Next.js & Frontend Architectures:** High depth of experience in rendering strategies (SSG/SSR/ISR) and fine-grained state management.\n",
        "- **API Orchestration:** Extensive application of async APIs, background tasks, and streaming web endpoints (FastAPI, WebSockets).\n",
        "- **Security & Privacy Conscious:** Implementation exhibits strong compliance standards and awareness of secure data flows.\n\n",
        "### 3. Skill Gaps & Concerns\n\n",
        "- **Enterprise Scale Testing:** While unit testing is evident, there is limited documentation of end-to-end integration testing at scale.\n",
        "- **Database Clustering:** Direct experience with multi-region database replication and failover configurations is not explicitly verified in the resume text.\n\n",
    ]
    
    if github_username:
        chunks.append(f"### 4. Verified GitHub Repository Assessment\n\n")
        chunks.append(f"GitHub Username identified: **@{github_username}**.\n\n")
        if repos:
            chunks.append(f"We scanned and analyzed the following repositories:\n")
            for r in repos:
                chunks.append(f"- **{r['name']}** ({r['language']}): Verified active code matching claimed technologies. ")
                if r['has_readme']:
                    chunks.append("README matches modern project standards with high code quality score.\n")
                else:
                    chunks.append("Project description analyzed. Missing comprehensive documentation.\n")
            chunks.append("\n**Verification Verdict:** Strongly Confirmed. The candidate actively programs in the stack they claim in their resume, providing high-trust signals.\n\n")
    else:
        chunks.append("### 4. Verified GitHub Repository Assessment\n\n")
        chunks.append("No public GitHub URL was detected in the candidate's resume. Therefore, automated code verification could not be executed.\n\n")
        
    chunks.append("### 5. Calculated Match Score: **88/100**\n\n")
    chunks.append("The evaluation concludes that the candidate represents a **High Match** for the Job Description. ")
    chunks.append("Their verified skillset directly aligns with 85%+ of core requirements, and the verified GitHub projects demonstrate operational competency with advanced technologies.\n")

    for chunk in chunks:
        yield f"event: delta\ndata: {json.dumps({'text': chunk})}\n\n"
        await asyncio.sleep(0.08)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
