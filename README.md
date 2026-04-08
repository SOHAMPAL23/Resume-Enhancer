Yes SPALL — here is your **complete, clean, single Markdown file** ready to paste directly into `README.md` ✅
(No extra formatting, no broken blocks, GitHub-ready)

---

# 🚀 Multi-Agent Resume Analyzer (LangGraph + Streamlit)

An intelligent **AI-powered Resume Analyzer** that compares a resume against a job description using a **multi-agent system built with LangGraph**.

The system simulates a real-world hiring pipeline by breaking the task into specialized agents that collaborate through a shared state to produce structured insights.

---

## 🎯 Key Features

- 🤖 **Multi-Agent Architecture (LangGraph)**
  - Modular agents for JD parsing, resume analysis, scoring, and recommendations

- 📊 **ATS Score & Skill Gap Analysis**
  - Matching skills, missing skills, and alignment score

- ✍️ **Resume Improvement Suggestions**
  - Actionable recommendations to improve ATS compatibility

- 🧠 **Project Recommendations**
  - Personalized project ideas to fill skill gaps

- 🌐 **Streamlit UI**
  - Clean, modern dashboard (glassmorphism style)

- 🔁 **LLM Provider Flexibility**
  - OpenAI / OpenRouter / Groq with automatic fallback

---

## 🧠 System Architecture

The system follows a **multi-agent workflow orchestrated using LangGraph**, where each agent performs a specialized task and passes results via shared state.

### 🔗 Workflow Diagram

```

User Input (JD + Resume)
│
▼
┌───────────────────────┐
│  JD Analyzer Agent    │
│  (Extract requirements)│
└───────────────────────┘
│
▼
┌───────────────────────┐
│ Resume Analyzer Agent │
│ (Extract skills/data) │
└───────────────────────┘
│
▼
┌───────────────────────┐
│  Scoring Agent        │
│ (ATS score + gaps)    │
└───────────────────────┘
│
▼
┌───────────────────────┐
│ Improvement Agent     │
│ (Resume suggestions)  │
└───────────────────────┘
│
▼
┌───────────────────────┐
│ Project Agent         │
│ (Skill-gap projects)  │
└───────────────────────┘
│
▼
Final Output

````
## 🧩 Agents Overview

### 1. 📄 JD Analyzer Agent
- Extracts:
  - Required skills
  - Responsibilities
  - Keywords

---

### 2. 📑 Resume Analyzer Agent
- Extracts:
  - Skills
  - Tools
  - Experience
  - Keywords

---

### 3. 📊 Scoring Agent
- Calculates:
  - ATS match score
  - Matching skills
  - Missing skills

---

### 4. ⚡ Improvement Agent
- Suggests:
  - Resume improvements
  - Better phrasing
  - Missing keywords

---

### 5. 🚀 Project Recommendation Agent
- Recommends:
  - Projects to build missing skills
  - Real-world portfolio ideas

---

## 🔁 Shared State Design

All agents communicate via a shared state object:

```python
{
  "job_description": str,
  "resume_text": str,
  "jd_skills": list,
  "resume_skills": list,
  "match_score": int,
  "missing_skills": list,
  "improvements": str,
  "projects": list
}
````

---

## ⚙️ Tech Stack

* 🐍 Python
* ⚡ Streamlit
* 🔗 LangGraph
* 🧠 LangChain
* 🤖 OpenAI / OpenRouter / Groq
* 📄 PyPDF
* 🔐 python-dotenv

---

## 📁 Project Structure

```
.
├── app.py                  # Streamlit UI
├── multi_agent_system.py  # LangGraph workflow + agents
├── README.md
├── requirements.txt
├── .env
```

---

## 🚀 Setup Instructions

### 1️⃣ Create Virtual Environment

```bash
python -m venv .venv
.venv\Scripts\activate
```

---

### 2️⃣ Install Dependencies

```bash
pip install streamlit langgraph langchain-openai python-dotenv pypdf openai
```

---

### 3️⃣ Configure Environment Variables

Create a `.env` file:

```env
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini

OPENROUTER_API_KEY=your_key
OPENROUTER_MODEL=meta-llama/llama-3-8b-instruct:free

GROQ_API_KEY=your_key
GROQ_MODEL=llama-3.1-8b-instant

LLM_PROVIDER=openai
LLM_TRUST_ENV=false
```

---

### 4️⃣ Run the App

```bash
streamlit run app.py
```

---

## 🔄 Provider Logic

* Uses selected provider (`LLM_PROVIDER`)
* Auto-detects OpenAI keys in OpenRouter field
* Falls back to **Groq** on rate limits
* Optional proxy support via `LLM_TRUST_ENV`

---

## 📌 Notes

* Works best with **text-based PDFs**
* Scanned resumes may reduce accuracy
* Designed for **modular extensibility**

---

## 🎯 Why This Project Stands Out

* ✅ Real-world AI system design
* ✅ Multi-agent orchestration (LangGraph)
* ✅ Clean UI + strong backend
* ✅ Practical use case
* ✅ Scalable architecture

---

## 👨‍💻 Author

**Soham Pal**
AI & Full Stack Developer

