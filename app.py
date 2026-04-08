import html
from pathlib import Path
import re
import sys
from typing import Optional

import streamlit as st
from pypdf import PdfReader

# Keep sibling imports working even if this app is launched from another folder
# or copied into a directory whose parent name is not a valid Python package name.
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from multi_agent_system import ResumeAnalyzerError, get_llm_summary, run_resume_analysis

st.set_page_config(page_title="Resume Analyzer", layout="wide", initial_sidebar_state="collapsed")


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Manrope:wght@400;500;700;800&display=swap');
        :root{--bg1:#020913;--bg2:#0b2032;--panel:rgba(255,255,255,.08);--stroke:rgba(255,255,255,.09);--stroke-soft:rgba(255,255,255,.05);--text:#edf6ff;--muted:#a6bfd4;--sky:#8fd8ff;--mint:#9bf0d5;--gold:#ffd28d;--shadow:0 24px 60px rgba(0,0,0,.22);}
        html,body,[class*="css"]{font-family:"Manrope","Segoe UI",sans-serif;}
        [data-testid="stAppViewContainer"]{background:radial-gradient(circle at 12% 15%,rgba(74,186,255,.16),transparent 24%),radial-gradient(circle at 88% 18%,rgba(155,240,213,.12),transparent 22%),linear-gradient(145deg,var(--bg1) 0%,#07131f 38%,var(--bg2) 100%);color:var(--text);}
        [data-testid="stHeader"]{background:transparent;}
        .block-container{max-width:1140px;padding-top:1.45rem;padding-bottom:3.4rem;}
        .hero,.panel,.metric,.card,.group,.sidebox,.meta-item{position:relative;border:1px solid var(--stroke);box-shadow:var(--shadow);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);}
        .hero::before,.panel::before,.metric::before,.card::before,.group::before,.sidebox::before,.meta-item::before{content:"";position:absolute;inset:1px;border-radius:inherit;border:1px solid var(--stroke-soft);pointer-events:none;}
        .hero,.panel,.metric,.card,.group{background:linear-gradient(180deg,rgba(255,255,255,.10),rgba(255,255,255,.045));}
        .hero{border-radius:34px;padding:1.45rem 1.45rem 1.3rem;margin-bottom:1.35rem;}
        .hero-grid{display:grid;grid-template-columns:1.35fr .9fr;gap:1.15rem;align-items:stretch;}
        .kicker,.label{margin:0 0 .45rem;color:var(--sky);font-size:.78rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase;}
        .hero h1{margin:0;max-width:11ch;color:#f9fcff;font-family:"Space Grotesk",sans-serif;font-size:clamp(2rem,4vw,3.4rem);line-height:1;letter-spacing:-.05em;}
        .hero p{color:var(--muted);line-height:1.7;}
        .pill-row{display:flex;flex-wrap:wrap;gap:.65rem;margin-top:1.05rem;}
        .pill{border-radius:999px;padding:.54rem .82rem;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.09);color:#f2f8ff;font-size:.87rem;font-weight:600;}
        .sidebox,.panel,.card,.group{border-radius:28px;padding:1.1rem 1.1rem 1rem;margin-bottom:1.05rem;}
        .sidebox{background:rgba(255,255,255,.055);}
        .sidebox p:last-child,.panel p:last-child,.card p:last-child{margin-bottom:0;}
        .title{margin:0;color:#f8fcff;font-family:"Space Grotesk",sans-serif;font-size:1.12rem;}
        .copy{margin:.3rem 0 0;color:var(--muted);line-height:1.65;font-size:.94rem;}
        [data-testid="stTextArea"],[data-testid="stFileUploader"]{margin-top:.78rem!important;margin-bottom:.95rem!important;}
        [data-testid="stTextArea"] textarea{min-height:320px!important;padding:1rem 1.05rem!important;border-radius:26px!important;border:1px solid rgba(255,255,255,.10)!important;background:rgba(255,255,255,.06)!important;color:var(--text)!important;line-height:1.7!important;box-shadow:inset 0 1px 0 rgba(255,255,255,.04);}
        [data-testid="stFileUploaderDropzone"]{padding:1rem .95rem!important;border:1px dashed rgba(143,216,255,.28)!important;border-radius:26px!important;background:rgba(255,255,255,.05)!important;}
        .stButton>button,.stFormSubmitButton>button{width:100%;min-height:3.25rem;border:none;border-radius:999px;background:linear-gradient(135deg,#98dfff 0%,#72caff 42%,#97f0d5 100%);color:#05131f;font-family:"Space Grotesk",sans-serif;font-weight:800;box-shadow:0 16px 32px rgba(94,197,255,.24);}
        .results-head{margin:1.5rem 0 1.1rem;}
        .results-head h2{margin:.2rem 0 0;color:#f9fcff;font-family:"Space Grotesk",sans-serif;font-size:clamp(1.7rem,3vw,2.3rem);}
        .metric{min-height:158px;border-radius:30px;padding:1.15rem 1.1rem 1rem;}
        .metric .value{margin:.45rem 0 0;color:#f9fcff;font-family:"Space Grotesk",sans-serif;font-size:clamp(1.9rem,3vw,2.8rem);line-height:1;}
        .card-head{display:flex;align-items:center;gap:.65rem;margin-bottom:.7rem;}
        .dot{width:.68rem;height:.68rem;border-radius:999px;box-shadow:0 0 0 6px rgba(255,255,255,.04);flex-shrink:0;}
        .sky{color:var(--sky)} .mint{color:var(--mint)} .gold{color:var(--gold)}
        .result p,.result li{color:var(--text);line-height:1.75;font-size:.97rem;}
        .result ul{margin:.35rem 0 .85rem 1.1rem;padding:0;}
        .sub{margin:.18rem 0 0;color:var(--muted);font-size:.92rem;}
        .smallcaps{color:var(--muted)!important;font-size:.75rem!important;font-weight:800;letter-spacing:.08em;text-transform:uppercase;}
        .group p{margin:0;}
        .group-copy{margin:.22rem 0 .8rem;color:var(--muted);font-size:.92rem;line-height:1.6;}
        .skills{display:flex;flex-wrap:wrap;gap:.5rem;}
        .skill{border-radius:999px;padding:.46rem .76rem;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.09);color:#f2f8ff;font-size:.87rem;font-weight:600;}
        .meta{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.9rem;}
        .meta-item{border-radius:22px;padding:.92rem;background:rgba(255,255,255,.05);}
        .meta-item p{margin:0;}
        [data-baseweb="tab-list"]{gap:.5rem;padding:.28rem;margin:.25rem 0 1rem;border-radius:999px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);}
        button[data-baseweb="tab"]{height:auto!important;padding:.62rem .95rem!important;border-radius:999px!important;background:transparent!important;color:var(--muted)!important;font-family:"Space Grotesk",sans-serif!important;font-size:.93rem!important;font-weight:700!important;}
        button[data-baseweb="tab"][aria-selected="true"]{background:linear-gradient(135deg,rgba(143,216,255,.22),rgba(155,240,213,.16))!important;color:#f8fcff!important;}
        .footer{margin-top:1.2rem;text-align:center;color:rgba(237,246,255,.58);font-size:.88rem;}
        @media (max-width:980px){.hero-grid,.meta{grid-template-columns:1fr;} .hero h1{max-width:none;} [data-testid="stTextArea"] textarea{min-height:240px!important;}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def extract_text_from_pdf(file) -> tuple[str, int]:
    reader = PdfReader(file)
    text = "".join(page.extract_text() or "" for page in reader.pages).strip()
    return text, len(reader.pages)


def get_provider_status() -> tuple[str, str, str]:
    try:
        summary = get_llm_summary()
    except ResumeAnalyzerError as exc:
        return (
            "Setup needed",
            "Add at least one provider key in `.env` before running analysis.",
            str(exc),
        )
    except Exception as exc:
        return (
            "Config check failed",
            "The app loaded, but provider details could not be resolved yet.",
            str(exc),
        )

    return (
        summary,
        "Provider configuration looks ready for analysis.",
        "You can switch providers or models in `.env` without changing the UI.",
    )


def parse_score_value(score_text: str) -> Optional[int]:
    match = re.search(r"(?:ATS\s+)?Score:\s*(\d+)", score_text, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def normalize_output_text(text: str) -> str:
    cleaned_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.replace("\u2022", "- ").strip()
        line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
        line = re.sub(r"__(.*?)__", r"\1", line)
        line = re.sub(r"`([^`]*)`", r"\1", line)
        line = re.sub(r"^\*+\s*(.+?)\s*\*+$", r"\1", line)
        line = re.sub(r"^\*\s+", "- ", line)
        line = re.sub(r"^-\s*\*\s*", "- ", line)
        line = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", line)
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def extract_section_text(text: str, section_name: str) -> str:
    lines = normalize_output_text(text).splitlines()
    collected, collecting = [], False
    for raw in lines:
        line = raw.strip()
        if not collecting:
            collecting = line.lower().startswith(f"{section_name.lower()}:")
            if collecting:
                _, _, remainder = line.partition(":")
                if remainder.strip():
                    collected.append(remainder.strip())
            continue
        if re.match(r"^[A-Z][A-Z0-9 /&()-]+:\s*", line):
            break
        if line:
            collected.append(line)
    return "\n".join(collected).strip()


def extract_list_section(text: str, section_name: str) -> list[str]:
    raw = extract_section_text(text, section_name)
    if not raw:
        return []

    items: list[str] = []
    for line in raw.splitlines():
        cleaned = re.sub(r"^\d+\.\s*", "", line).strip()
        cleaned = re.sub(r"^-\s*", "", cleaned).strip()
        if not cleaned:
            continue
        if "," in cleaned and not re.match(r"^[A-Z][A-Z0-9 /&()-]+:\s*", cleaned):
            parts = [part.strip() for part in cleaned.split(",") if part.strip()]
            items.extend(parts)
        else:
            items.append(cleaned)

    deduped: list[str] = []
    seen: set[str] = set()
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def extract_explanation(score_text: str) -> str:
    summary = extract_section_text(score_text, "SUMMARY")
    top_priority = extract_section_text(score_text, "TOP PRIORITY")
    combined = " ".join(part for part in [summary, top_priority] if part).strip()
    if not combined:
        return "Structured scoring generated from the job description and resume comparison."
    return combined


def describe_score(score_value: Optional[int]) -> tuple[str, str]:
    if score_value is None:
        return ("Awaiting analysis", "Run the workflow to generate an ATS-style fit score.")
    if score_value >= 85:
        return ("Strong Match", "Your resume appears tightly aligned with the role requirements.")
    if score_value >= 70:
        return ("Competitive Match", "The fit is solid, with a few gaps worth tightening.")
    if score_value >= 55:
        return ("Needs Reinforcement", "Relevant experience exists, but the signal can be sharpened.")
    return ("Gap Heavy", "Focus on missing skills, stronger phrasing, and targeted projects.")


def rich_text_to_html(text: str) -> str:
    text = normalize_output_text(text)
    parts, items, numbered_items = [], [], []

    def flush_lists() -> None:
        nonlocal items, numbered_items
        if items:
            parts.append("<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>")
            items = []
        if numbered_items:
            parts.append("<ol>" + "".join(f"<li>{html.escape(item)}</li>" for item in numbered_items) + "</ol>")
            numbered_items = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            flush_lists()
        elif re.match(r"^\d+\.\s+", line):
            numbered_items.append(re.sub(r"^\d+\.\s*", "", line))
        elif line.startswith("- "):
            items.append(line[2:].strip())
        elif re.match(r"^[A-Z][A-Z0-9 /&()-]+:\s*.+$", line):
            flush_lists()
            label, _, value = line.partition(":")
            parts.append(
                f"<p><span class='field-label'>{html.escape(label)}:</span> {html.escape(value.strip())}</p>"
            )
        elif line.endswith(":") and len(line) <= 48:
            flush_lists()
            parts.append(f"<p class='smallcaps'>{html.escape(line[:-1])}</p>")
        else:
            flush_lists()
            parts.append(f"<p>{html.escape(line)}</p>")
    flush_lists()
    return "".join(parts) or "<p>No content available yet.</p>"


def box(title: str, subtitle: str, body: str, tone: str) -> None:
    st.markdown(f"<section class='card'><div class='card-head'><span class='dot {tone}'></span><div><h3 class='title'>{html.escape(title)}</h3><p class='sub'>{html.escape(subtitle)}</p></div></div><div class='result'>{rich_text_to_html(body)}</div></section>", unsafe_allow_html=True)


def metric(label: str, value: str, text: str, tone: str) -> None:
    st.markdown(f"<section class='metric'><p class='label {tone}'>{html.escape(label)}</p><p class='value'>{html.escape(value)}</p><p class='copy'>{html.escape(text)}</p></section>", unsafe_allow_html=True)


def skill_group(title: str, text: str, items: list[str], tone: str) -> None:
    pills = "".join(f"<span class='skill'>{html.escape(item)}</span>" for item in items) or "<span class='skill'>No extracted items</span>"
    st.markdown(f"<section class='group'><p class='label {tone}'>{html.escape(title)}</p><p class='group-copy'>{html.escape(text)}</p><div class='skills'>{pills}</div></section>", unsafe_allow_html=True)


inject_styles()
provider_summary, provider_status, provider_note = get_provider_status()
st.session_state.setdefault("analysis_result", None)
st.session_state.setdefault("resume_name", "")
st.session_state.setdefault("resume_pages", 0)
st.session_state.setdefault("resume_chars", 0)
st.session_state.setdefault("jd_chars", 0)

st.markdown(
    f"""
    <section class='hero'>
        <div class='hero-grid'>
            <div>
                <p class='kicker'>Resume Command Center</p>
                <h1>Make resume analysis feel crisp, not chaotic.</h1>
                <p>Paste a job description, upload a resume PDF, and get a cleaner ATS-style score, stronger improvement guidance, and focused project ideas.</p>
                <div class='pill-row'>
                    <span class='pill'>ATS fit scoring</span>
                    <span class='pill'>Multi-agent review</span>
                    <span class='pill'>Project recommendations</span>
                </div>
            </div>
            <div>
                <div class='sidebox'>
                    <p class='label'>Provider Stack</p>
                    <p>{html.escape(provider_summary)}</p>
                    <p class='copy' style='margin-top:.55rem;'>{html.escape(provider_status)}</p>
                </div>
                <div class='sidebox' style='margin-top:.75rem;'>
                    <p class='label'>Workflow</p>
                    <p>JD extraction, resume extraction, scoring, improvement review, and project suggestions in one organized flow.</p>
                    <p class='copy' style='margin-top:.55rem;'>{html.escape(provider_note)}</p>
                </div>
            </div>
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)

with st.form("analysis_form"):
    left, right = st.columns([1.35, 0.9], gap="large")
    with left:
        st.markdown("<section class='panel'><p class='label'>Job Description</p><h3 class='title'>Paste the role requirements</h3><p class='copy'>Include responsibilities, tools, and expected experience for a sharper comparison.</p></section>", unsafe_allow_html=True)
        jd = st.text_area("Job Description", placeholder="Paste the full job description here...", label_visibility="collapsed")
    with right:
        st.markdown("<section class='panel'><p class='label'>Resume Input</p><h3 class='title'>Upload the PDF</h3><p class='copy'>Text-based PDFs work best. Scanned image-only resumes may extract poorly.</p></section>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"], label_visibility="collapsed")
        file_name = html.escape(uploaded_file.name) if uploaded_file else "No file uploaded yet"
        file_note = f"{max(1, round(uploaded_file.size / 1024))} KB ready for parsing." if uploaded_file else "Drop a resume to unlock analysis."
    analyze = st.form_submit_button("Analyze Resume")

if analyze:
    if not jd or not uploaded_file:
        st.warning("Please provide both the job description and a resume PDF.")
    else:
        try:
            resume_text, page_count = extract_text_from_pdf(uploaded_file)
        except Exception as exc:
            st.error(f"Could not read the uploaded PDF: {exc}")
        else:
            if not resume_text:
                st.error("No readable text was found in the uploaded PDF.")
            else:
                try:
                    with st.spinner("Running the multi-agent analysis pipeline..."):
                        result = run_resume_analysis(jd, resume_text)
                except ResumeAnalyzerError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error(f"Unexpected error while analyzing the resume: {exc}")
                else:
                    st.session_state.analysis_result = result
                    st.session_state.resume_name = uploaded_file.name
                    st.session_state.resume_pages = page_count
                    st.session_state.resume_chars = len(resume_text)
                    st.session_state.jd_chars = len(jd)

result = st.session_state.analysis_result
if result:
    score_text = result["score"]
    score_value = parse_score_value(score_text)
    score_label, score_blurb = describe_score(score_value)
    matching = extract_list_section(score_text, "Matching Skills")
    missing = extract_list_section(score_text, "Missing Skills")
    explanation = extract_explanation(score_text) or "Structured scoring generated from the comparison."
    st.markdown("<section class='results-head'><p class='kicker' style='color:var(--mint);'>Results</p><h2>A cleaner decision board for the resume review.</h2><p class='copy'>Start with the summary row, then move through the tabs for scoring, improvements, and project direction.</p></section>", unsafe_allow_html=True)
    cols = st.columns(4, gap="large")
    with cols[0]:
        metric("ATS Match", f"{score_value}/100" if score_value is not None else "Ready", score_blurb, "sky")
    with cols[1]:
        metric("Matching Skills", str(len(matching)), "Signals already aligned with the role.", "mint")
    with cols[2]:
        metric("Missing Skills", str(len(missing)), "Gaps to address with stronger wording or projects.", "gold")
    with cols[3]:
        metric("Resume Scan", f"{st.session_state.resume_pages} pages", f"{st.session_state.resume_chars} characters extracted from the uploaded PDF.", "sky")
    overview, improvements, projects = st.tabs(["Overview", "Improvements", "Projects"])
    with overview:
        c1, c2 = st.columns([1.04, 0.96], gap="large")
        with c1:
            box("ATS Snapshot", f"{score_label}. {explanation}", result["score"], "sky")
        with c2:
            skill_group("Matching Skills", "These skills are already showing up well against the role.", matching, "mint")
            skill_group("Missing Skills", "These areas likely need clearer experience signals or stronger projects.", missing, "gold")
            st.markdown(f"<section class='panel'><p class='label'>Analysis Meta</p><div class='meta'><div class='meta-item'><p class='smallcaps'>Resume</p><p>{html.escape(st.session_state.resume_name)}</p></div><div class='meta-item'><p class='smallcaps'>Pages</p><p>{st.session_state.resume_pages}</p></div><div class='meta-item'><p class='smallcaps'>Resume Characters</p><p>{st.session_state.resume_chars}</p></div><div class='meta-item'><p class='smallcaps'>JD Characters</p><p>{st.session_state.jd_chars}</p></div></div></section>", unsafe_allow_html=True)
    with improvements:
        box("Resume Improvement Plan", "Actionable guidance to tighten wording, coverage, and ATS alignment.", result["suggestions"], "gold")
    with projects:
        box("Project Suggestions", "Resume-ready project directions built around the identified gaps.", result["project_suggestions"], "mint")
else:
    st.markdown(
        """
        <section class='panel' style='margin-top:1.15rem;'>
            <p class='label'>Before You Run</p>
            <div class='meta'>
                <div class='meta-item'>
                    <p class='smallcaps'>1. Job Description</p>
                    <p>Paste the full role text, especially responsibilities, tools, and expected years of experience.</p>
                </div>
                <div class='meta-item'>
                    <p class='smallcaps'>2. Resume PDF</p>
                    <p>Upload a text-based PDF so the parser can extract your experience and skills accurately.</p>
                </div>
                <div class='meta-item'>
                    <p class='smallcaps'>3. Provider Setup</p>
                    <p>Add an API key in <code>.env</code>. The app can use OpenAI, OpenRouter, or Groq.</p>
                </div>
                <div class='meta-item'>
                    <p class='smallcaps'>What You Get</p>
                    <p>An ATS-style score, skill-gap summary, resume improvement notes, and project ideas to close the gaps.</p>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

