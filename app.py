import streamlit as st
import groq
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

st.set_page_config(
    page_title="AI Career Matching Agent",
    page_icon="🚀",
    layout="wide"
)

def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_url(st.secrets["sheets"]["url"])
    return sheet.sheet1

def save_to_sheet(company, job_title, match_score, status, likelihood):
    try:
        sheet = get_sheet()
        existing = sheet.get_all_values()
        if not existing:
            sheet.append_row([
                "ID", "Timestamp", "Company", "Job Title",
                "Match Score", "Status", "Hiring Likelihood"
            ])
        row_id = len(sheet.get_all_values())
        sheet.append_row([
            row_id,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            company, job_title, match_score, status, likelihood
        ])
        return True
    except Exception as e:
        st.warning(f"Could not save to sheet: {str(e)}")
        return False

def ask_groq(api_key, prompt):
    client = groq.Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000
    )
    return response.choices[0].message.content

def analyze(api_key, job_description, resume_text, company_name):

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
    job_analysis = ask_groq(api_key, job_prompt)

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
    resume_analysis = ask_groq(api_key, resume_prompt)

    match_prompt = f"""
    You are a career matching expert. Compare this job and resume for a candidate
    applying to {company_name}.

    JOB ANALYSIS:
    {job_analysis}

    RESUME ANALYSIS:
    {resume_analysis}

    Return your response in this EXACT format with these EXACT labels:

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

    SKILL RECOMMENDATIONS - SOFT SKILLS:
    - [specific soft skill to develop with one line explanation]

    SKILL RECOMMENDATIONS - AI SKILLS:
    - [specific AI skill to develop with one line explanation]

    SKILL RECOMMENDATIONS - HARD SKILLS:
    - [specific hard skill to develop with one line explanation]

    SKILL RECOMMENDATIONS - TECH & SOFTWARE:
    - [specific tool or software to learn with one line explanation]

    RESUME IMPROVEMENTS:
    - [specific actionable improvement for this resume for this role]

    INTERNATIONAL HIRING:
    [2-3 sentences about {company_name}'s known history of hiring international
    students, H1B sponsorship track record, and whether they sponsor visas.]
    """

    match_result = ask_groq(api_key, match_prompt)
    return job_analysis, resume_analysis, match_result

def parse_section(text, label):
    try:
        start = text.index(label) + len(label)
        all_labels = [
            "MATCHED SKILLS:", "MISSING SKILLS:", "STRENGTHS:",
            "ACTION PLAN:", "SIMILAR ROLES:", "HIRING LIKELIHOOD:",
            "SKILL RECOMMENDATIONS - SOFT SKILLS:",
            "SKILL RECOMMENDATIONS - AI SKILLS:",
            "SKILL RECOMMENDATIONS - HARD SKILLS:",
            "SKILL RECOMMENDATIONS - TECH & SOFTWARE:",
            "RESUME IMPROVEMENTS:", "INTERNATIONAL HIRING:"
        ]
        end = len(text)
        for nl in all_labels:
            if nl != label and nl in text:
                pos = text.index(nl)
                if pos > start:
                    end = min(end, pos)
        return text[start:end].strip()
    except:
        return "Not found"

STATUS_COLORS = {
    "Submitted":    "#78909C",
    "Call":         "#42A5F5",
    "Interview 1":  "#1565C0",
    "Interview 2":  "#1976D2",
    "HR Interview": "#1E88E5",
    "Accepted":     "#2E7D32",
    "Offer Letter": "#6A1B9A",
    "Rejected":     "#D32F2F",
}

def status_badge(status):
    color = STATUS_COLORS.get(status, "#78909C")
    return f'<span style="background-color:{color};color:white;padding:4px 12px;border-radius:12px;font-size:13px;font-weight:bold;">{status}</span>'

def likelihood_badge(likelihood):
    colors = {"Low": "#D32F2F", "Medium": "#F57C00", "High": "#2E7D32"}
    color = colors.get(likelihood.strip(), "#78909C")
    return f'<span style="background-color:{color};color:white;padding:4px 12px;border-radius:12px;font-size:13px;font-weight:bold;">{likelihood.strip()}</span>'

# ── UI ────────────────────────────────────────────────────────────────────────
st.title("🚀 AI Career Matching Agent")
st.markdown("*Paste a job description and your resume — get your match score, skill gaps, and action plan instantly.*")
st.divider()

with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.secrets.get("groq_api_key", "") or st.text_input(
        "Groq API Key", type="password", placeholder="gsk_..."
    )
    st.caption("Free API key at console.groq.com")
    st.divider()
    st.header("🎨 Status Legend")
    for status, color in STATUS_COLORS.items():
        st.markdown(
            f'<span style="background-color:{color};color:white;padding:3px 10px;'
            f'border-radius:10px;font-size:12px;font-weight:bold;">{status}</span>',
            unsafe_allow_html=True
        )
        st.write("")
    st.divider()
    st.header("📊 About")
    st.markdown("""
    This agent:
    - Parses job descriptions
    - Analyzes your resume
    - Calculates match score
    - Identifies skill gaps
    - Categorized skill recommendations
    - Resume improvement tips
    - Company visa/international hiring info
    - Saves results to Google Sheets
    """)

company_input = st.text_input("🏢 Company Name", placeholder="e.g. Stripe, Google, DoorDash")

col1, col2 = st.columns(2)
with col1:
    st.subheader("📋 Job Description")
    job_input = st.text_area(
        "Job description",
        height=300,
        placeholder="Paste job description here...",
        label_visibility="collapsed"
    )
with col2:
    st.subheader("📄 Your Resume")
    resume_input = st.text_area(
        "Resume text",
        height=300,
        placeholder="Paste your resume text here...",
        label_visibility="collapsed"
    )

st.subheader("📌 Application Status")
selected_status = st.selectbox("Select your current status for this role", list(STATUS_COLORS.keys()))
st.markdown(status_badge(selected_status), unsafe_allow_html=True)

st.divider()
analyze_btn = st.button("🔍 Analyze My Match", type="primary", use_container_width=True)

if analyze_btn:
    if not api_key:
        st.error("Please enter your Groq API key in the sidebar.")
    elif not job_input:
        st.error("Please paste a job description.")
    elif not resume_input:
        st.error("Please paste your resume.")
    elif not company_input:
        st.error("Please enter the company name.")
    else:
        with st.spinner("🤖 Analyzing your match... this takes about 15 seconds..."):
            try:
                job_analysis, resume_analysis, match_result = analyze(
                    api_key, job_input, resume_input, company_input
                )

                score_raw   = parse_section(match_result, "MATCH SCORE:")
                matched     = parse_section(match_result, "MATCHED SKILLS:")
                missing     = parse_section(match_result, "MISSING SKILLS:")
                strengths   = parse_section(match_result, "STRENGTHS:")
                actions     = parse_section(match_result, "ACTION PLAN:")
                similar     = parse_section(match_result, "SIMILAR ROLES:")
                likelihood  = parse_section(match_result, "HIRING LIKELIHOOD:")
                soft_skills = parse_section(match_result, "SKILL RECOMMENDATIONS - SOFT SKILLS:")
                ai_skills   = parse_section(match_result, "SKILL RECOMMENDATIONS - AI SKILLS:")
                hard_skills = parse_section(match_result, "SKILL RECOMMENDATIONS - HARD SKILLS:")
                tech_skills = parse_section(match_result, "SKILL RECOMMENDATIONS - TECH & SOFTWARE:")
                resume_tips = parse_section(match_result, "RESUME IMPROVEMENTS:")
                intl_hiring = parse_section(match_result, "INTERNATIONAL HIRING:")

                try:
                    score = float(''.join(filter(lambda x: x.isdigit() or x == '.', score_raw)))
                except:
                    score = 0

                saved = save_to_sheet(
                    company=company_input,
                    job_title=job_input[:50],
                    match_score=score,
                    status=selected_status,
                    likelihood=likelihood.strip()
                )

                st.divider()
                st.subheader("📊 Your Results")

                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.metric("Match Score", f"{score:.0f}%")
                with m2:
                    st.markdown("**Hiring Likelihood**")
                    st.markdown(likelihood_badge(likelihood), unsafe_allow_html=True)
                with m3:
                    st.markdown("**Application Status**")
                    st.markdown(status_badge(selected_status), unsafe_allow_html=True)
                with m4:
                    st.metric("Company", company_input)

                st.divider()

                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("✅ Matched Skills")
                    st.markdown(matched)
                with c2:
                    st.subheader("❌ Missing Skills")
                    st.markdown(missing)

                st.divider()

                c3, c4 = st.columns(2)
                with c3:
                    st.subheader("💪 Your Strengths")
                    st.markdown(strengths)
                with c4:
                    st.subheader("🎯 Action Plan")
                    st.markdown(actions)

                st.divider()

                st.subheader("📚 Skill Recommendations")
                sk1, sk2, sk3, sk4 = st.columns(4)
                with sk1:
                    st.markdown("**🤝 Soft Skills**")
                    st.markdown(soft_skills)
                with sk2:
                    st.markdown("**🤖 AI Skills**")
                    st.markdown(ai_skills)
                with sk3:
                    st.markdown("**🔧 Hard Skills**")
                    st.markdown(hard_skills)
                with sk4:
                    st.markdown("**💻 Tech & Software**")
                    st.markdown(tech_skills)

                st.divider()

                c5, c6 = st.columns(2)
                with c5:
                    st.subheader("📝 Resume Improvements")
                    st.markdown(resume_tips)
                with c6:
                    st.subheader("🔍 Similar Roles to Apply For")
                    st.markdown(similar)

                st.divider()

                st.subheader("🌍 International Hiring & Visa Sponsorship")
                st.info(intl_hiring)

                if saved:
                    st.success("✅ Analysis saved to Google Sheets!")
                else:
                    st.info("Analysis complete!")

            except Exception as e:
                st.error(f"Something went wrong: {str(e)}")
