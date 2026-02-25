import streamlit as st
import anthropic
import sqlite3
from datetime import datetime

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Career Matching Agent",
    page_icon="🚀",
    layout="wide"
)

# ── DATABASE SETUP ────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("career_agent.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            job_title TEXT,
            match_score REAL,
            matched_skills TEXT,
            missing_skills TEXT,
            hiring_likelihood TEXT,
            action_plan TEXT,
            similar_roles TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_to_db(job_title, match_score, matched, missing, likelihood, action, similar):
    conn = sqlite3.connect("career_agent.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO analyses (
            timestamp, job_title, match_score, matched_skills,
            missing_skills, hiring_likelihood, action_plan, similar_roles
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        job_title, match_score, matched, missing, likelihood, action, similar
    ))
    conn.commit()
    conn.close()

# ── CLAUDE API CALL ───────────────────────────────────────────────────────────
def analyze(api_key, job_description, resume_text):
    client = anthropic.Anthropic(api_key=api_key)

    # Step 1 — Parse job
    job_prompt = f"""
    You are a job analysis expert. Extract the following from this job description.
    Be concise and structured.

    1. Job Title (one line)
    2. Required Skills (bullet list)
    3. Tools & Technologies (bullet list)
    4. Experience Level (one line)
    5. Industry/Domain (one line)

    Job Description:
    {job_description}
    """

    job_response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": job_prompt}]
    )
    job_analysis = job_response.content[0].text

    # Step 2 — Parse resume
    resume_prompt = f"""
    You are a resume analysis expert. Extract the following from this resume.
    Be concise and structured.

    1. Technical Skills (bullet list)
    2. Soft Skills (bullet list)
    3. Tools & Technologies (bullet list)
    4. Key Achievements with numbers (bullet list)

    Resume:
    {resume_text}
    """

    resume_response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": resume_prompt}]
    )
    resume_analysis = resume_response.content[0].text

    # Step 3 — Match
    match_prompt = f"""
    You are a career matching expert. Compare this job and resume.

    JOB ANALYSIS:
    {job_analysis}

    RESUME ANALYSIS:
    {resume_analysis}

    Return your response in this EXACT format, with these EXACT labels:

    MATCH SCORE: [number only, no % sign]

    MATCHED SKILLS:
    - [skill]

    MISSING SKILLS:
    - [skill]

    STRENGTHS:
    - [strength]

    ACTION PLAN:
    1. [action]
    2. [action]
    3. [action]
    4. [action]
    5. [action]

    SIMILAR ROLES:
    - [role]

    HIRING LIKELIHOOD: [Low / Medium / High]
    """

    match_response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{"role": "user", "content": match_prompt}]
    )

    return job_analysis, resume_analysis, match_response.content[0].text

# ── PARSE MATCH RESULT ────────────────────────────────────────────────────────
def parse_section(text, label):
    try:
        start = text.index(label) + len(label)
        next_labels = ["MATCHED SKILLS:", "MISSING SKILLS:", "STRENGTHS:",
                      "ACTION PLAN:", "SIMILAR ROLES:", "HIRING LIKELIHOOD:"]
        end = len(text)
        for nl in next_labels:
            if nl != label and nl in text:
                pos = text.index(nl)
                if pos > start:
                    end = min(end, pos)
        return text[start:end].strip()
    except:
        return "Not found"

# ── UI ────────────────────────────────────────────────────────────────────────
init_db()

st.title("🚀 AI Career Matching Agent")
st.markdown("*Paste a job description and your resume — get your match score, skill gaps, and action plan instantly.*")
st.divider()

# Sidebar for API key
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Claude API Key", type="password", placeholder="sk-ant-api03-...")
    st.caption("Your key is never stored. Get one at console.anthropic.com")
    st.divider()
    st.header("📊 About")
    st.markdown("""
    This agent:
    - Parses job descriptions
    - Analyzes your resume  
    - Calculates match score
    - Identifies skill gaps
    - Generates action plan
    """)

# Main inputs
col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 Job Description")
    job_input = st.text_area(
        "Paste the full job description here",
        height=300,
        placeholder="Paste job description here...",
        label_visibility="collapsed"
    )

with col2:
    st.subheader("📄 Your Resume")
    resume_input = st.text_area(
        "Paste your resume text here",
        height=300,
        placeholder="Paste your resume text here...",
        label_visibility="collapsed"
    )

# Analyze button
st.divider()
analyze_btn = st.button("🔍 Analyze My Match", type="primary", use_container_width=True)

if analyze_btn:
    if not api_key:
        st.error("Please enter your Claude API key in the sidebar.")
    elif not job_input:
        st.error("Please paste a job description.")
    elif not resume_input:
        st.error("Please paste your resume.")
    else:
        with st.spinner("🤖 Analyzing your match... this takes about 15 seconds..."):
            try:
                job_analysis, resume_analysis, match_result = analyze(api_key, job_input, resume_input)

                # Parse sections
                score_raw = parse_section(match_result, "MATCH SCORE:")
                matched   = parse_section(match_result, "MATCHED SKILLS:")
                missing   = parse_section(match_result, "MISSING SKILLS:")
                strengths = parse_section(match_result, "STRENGTHS:")
                actions   = parse_section(match_result, "ACTION PLAN:")
                similar   = parse_section(match_result, "SIMILAR ROLES:")
                likelihood = parse_section(match_result, "HIRING LIKELIHOOD:")

                # Extract score number
                try:
                    score = float(''.join(filter(lambda x: x.isdigit() or x == '.', score_raw)))
                except:
                    score = 0

                # Save to database
                save_to_db(
                    job_title=job_input[:50],
                    match_score=score,
                    matched=matched,
                    missing=missing,
                    likelihood=likelihood.strip(),
                    action=actions,
                    similar=similar
                )

                # ── RESULTS ──────────────────────────────────────────────
                st.divider()
                st.subheader("📊 Your Results")

                # Score + likelihood
                metric_col1, metric_col2, metric_col3 = st.columns(3)
                with metric_col1:
                    st.metric("Match Score", f"{score:.0f}%")
                with metric_col2:
                    st.metric("Hiring Likelihood", likelihood.strip())
                with metric_col3:
                    st.metric("Analysis Date", datetime.now().strftime("%b %d, %Y"))

                st.divider()

                # Skills columns
                skill_col1, skill_col2 = st.columns(2)
                with skill_col1:
                    st.subheader("✅ Matched Skills")
                    st.markdown(matched)

                with skill_col2:
                    st.subheader("❌ Missing Skills")
                    st.markdown(missing)

                st.divider()

                # Strengths + Action plan
                action_col1, action_col2 = st.columns(2)
                with action_col1:
                    st.subheader("💪 Your Strengths")
                    st.markdown(strengths)

                with action_col2:
                    st.subheader("🎯 Action Plan")
                    st.markdown(actions)

                st.divider()

                # Similar roles
                st.subheader("🔍 Similar Roles to Apply For")
                st.markdown(similar)

                st.success("✅ Analysis saved to your database!")

            except Exception as e:
                st.error(f"Something went wrong: {str(e)}")