from pathlib import Path
import os
from typing import Optional, TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from openai import APIConnectionError, AuthenticationError, NotFoundError, RateLimitError


ENV_PATH = Path(__file__).with_name(".env")
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_OPENROUTER_MODEL = "meta-llama/llama-3-8b-instruct:free"
DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"
PROXY_ENV_VARS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)

load_dotenv(dotenv_path=ENV_PATH)

OUTPUT_STYLE_GUIDE = """
You are an expert resume reviewer.

Generate structured output with clear emphasis on important terms.

FORMATTING RULES:
- DO NOT use markdown symbols like ** or *
- DO NOT use asterisks for emphasis
- Use ALL CAPS labels for sections
- Keep the output clean, professional, and UI-friendly
- Use short plain-text numbered lines when a list is needed
- Keep each section concise and easy to scan in a web UI
""".strip()


class ResumeAnalyzerError(RuntimeError):
    """Raised when the LLM provider is misconfigured or unavailable."""


class State(TypedDict):
    job_description: str
    resume: str
    jd_skills: str
    resume_skills: str
    score: str
    suggestions: str
    project_suggestions: str


_llm_clients: dict[tuple[str, str, str, str], ChatOpenAI] = {}
_network_note: Optional[str] = None
_rate_limited_providers: set[str] = set()


def _reload_env() -> None:
    load_dotenv(dotenv_path=ENV_PATH, override=True)


def _read_env(name: str) -> Optional[str]:
    _reload_env()
    value = os.getenv(name)
    if value is None:
        return None

    cleaned = value.strip().strip("\"'")
    return cleaned or None


def _looks_like_openrouter_key(key: str) -> bool:
    return key.startswith("sk-or-")


def _looks_like_openai_key(key: str) -> bool:
    return key.startswith("sk-proj-") or key.startswith("sk-")


def _env_flag(name: str, default: bool = False) -> bool:
    value = _read_env(name)
    if value is None:
        return default

    return value.lower() in {"1", "true", "yes", "on"}


def _prepare_network_environment() -> None:
    global _network_note

    if _env_flag("LLM_TRUST_ENV", default=False):
        return

    removed_vars = [name for name in PROXY_ENV_VARS if os.getenv(name)]
    for name in removed_vars:
        os.environ.pop(name, None)

    if removed_vars:
        _network_note = (
            "Ignoring system proxy environment variables by default. "
            "Set LLM_TRUST_ENV=true in .env if you need to use a proxy."
        )


def _resolve_provider_config(provider: str) -> dict:
    if provider == "openai":
        openai_key = _read_env("OPENAI_API_KEY")
        if not openai_key:
            raise ResumeAnalyzerError(
                "OPENAI_API_KEY is missing in .env."
            )
        return {
            "provider": "openai",
            "api_key": openai_key,
            "model": _read_env("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL,
            "source": "OPENAI_API_KEY",
        }

    if provider == "openrouter":
        openrouter_key = _read_env("OPENROUTER_API_KEY")
        if not openrouter_key:
            raise ResumeAnalyzerError(
                "OPENROUTER_API_KEY is missing in .env."
            )
        return {
            "provider": "openrouter",
            "api_key": openrouter_key,
            "model": _read_env("OPENROUTER_MODEL") or DEFAULT_OPENROUTER_MODEL,
            "source": "OPENROUTER_API_KEY",
        }

    if provider == "groq":
        groq_key = _read_env("GROQ_API_KEY")
        if not groq_key:
            raise ResumeAnalyzerError(
                "GROQ_API_KEY is missing in .env."
            )
        return {
            "provider": "groq",
            "api_key": groq_key,
            "model": _read_env("GROQ_MODEL") or DEFAULT_GROQ_MODEL,
            "source": "GROQ_API_KEY",
        }

    raise ResumeAnalyzerError(
        "LLM_PROVIDER must be one of 'openai', 'openrouter', or 'groq'."
    )


def _resolve_primary_llm_config() -> dict:
    provider_override = (_read_env("LLM_PROVIDER") or "").lower()
    openai_key = _read_env("OPENAI_API_KEY")
    openrouter_key = _read_env("OPENROUTER_API_KEY")
    groq_key = _read_env("GROQ_API_KEY")

    if provider_override:
        return _resolve_provider_config(provider_override)

    if openai_key:
        return _resolve_provider_config("openai")

    if openrouter_key and _looks_like_openrouter_key(openrouter_key):
        return _resolve_provider_config("openrouter")

    if openrouter_key and _looks_like_openai_key(openrouter_key):
        config = {
            "provider": "openai",
            "api_key": openrouter_key,
            "model": _read_env("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL,
            "source": "OPENROUTER_API_KEY",
            "note": (
                "Detected an OpenAI-style key stored in OPENROUTER_API_KEY, "
                "so the app will use the OpenAI endpoint automatically."
            ),
        }
        return config

    if openrouter_key:
        return _resolve_provider_config("openrouter")

    if groq_key:
        return _resolve_provider_config("groq")

    raise ResumeAnalyzerError(
        "No API key found. Add OPENAI_API_KEY, OPENROUTER_API_KEY, or GROQ_API_KEY to .env."
    )


def _resolve_fallback_llm_config(primary_config: dict) -> Optional[dict]:
    groq_key = _read_env("GROQ_API_KEY")
    if not groq_key or primary_config["provider"] == "groq":
        return None

    config = _resolve_provider_config("groq")
    config["note"] = "Groq fallback is enabled for quota and rate-limit errors."
    return config


def _build_llm(config: dict) -> ChatOpenAI:
    _prepare_network_environment()

    if config["provider"] == "openrouter":
        return ChatOpenAI(
            model=config["model"],
            base_url="https://openrouter.ai/api/v1",
            api_key=config["api_key"],
            default_headers={
                "HTTP-Referer": "http://localhost:8503",
                "X-Title": "AI Resume Analyzer",
            },
        )

    if config["provider"] == "groq":
        return ChatOpenAI(
            model=config["model"],
            base_url="https://api.groq.com/openai/v1",
            api_key=config["api_key"],
        )

    return ChatOpenAI(
        model=config["model"],
        api_key=config["api_key"],
    )


def _llm_cache_key(config: dict) -> tuple[str, str, str, str]:
    return (
        config["provider"],
        config["model"],
        config["source"],
        config["api_key"],
    )


def get_llm(config: Optional[dict] = None) -> ChatOpenAI:
    if config is None:
        config = _resolve_primary_llm_config()

    cache_key = _llm_cache_key(config)
    if cache_key not in _llm_clients:
        _llm_clients[cache_key] = _build_llm(config)

    return _llm_clients[cache_key]


def get_llm_summary() -> str:
    _prepare_network_environment()
    primary_config = _resolve_primary_llm_config()
    fallback_config = _resolve_fallback_llm_config(primary_config)
    notes = []
    parts = [f"Primary: {primary_config['provider']} | {primary_config['model']}"]

    if primary_config.get("note"):
        notes.append(primary_config["note"])
    if fallback_config:
        parts.append(f"Fallback: {fallback_config['provider']} | {fallback_config['model']}")
        if fallback_config.get("note"):
            notes.append(fallback_config["note"])
    if _network_note:
        notes.append(_network_note)

    if notes:
        parts.append(" | ".join(notes))

    return " | ".join(parts)


def _invoke_llm(prompt: str):
    primary_config = _resolve_primary_llm_config()
    fallback_config = _resolve_fallback_llm_config(primary_config)

    if (
        primary_config["provider"] in _rate_limited_providers
        and fallback_config is not None
    ):
        return get_llm(fallback_config).invoke(prompt)

    try:
        return get_llm(primary_config).invoke(prompt)
    except RateLimitError:
        if not fallback_config:
            raise

        _rate_limited_providers.add(primary_config["provider"])
        print(
            f"\n[Primary provider '{primary_config['provider']}' hit a quota/rate limit. Falling back to Groq...]"
        )
        try:
            return get_llm(fallback_config).invoke(prompt)
        except Exception as exc:
            raise ResumeAnalyzerError(
                "The primary provider hit a quota/rate limit and the Groq fallback also failed."
            ) from exc


def jd_analyzer(state: State):
    print("\n[JD Analyzer Started to work ...]")

    prompt = f"""
    {OUTPUT_STYLE_GUIDE}

    Extract the core requirements from this job description.

    Return the result in this plain-text structure:

    REQUIRED SKILLS: item1, item2, item3
    TOOLS AND TECHNOLOGIES: item1, item2, item3
    RESPONSIBILITIES:
    1. item
    2. item
    EXPERIENCE EXPECTATIONS:
    1. item
    2. item

    Job Description:

    {state['job_description']}
    """

    response = _invoke_llm(prompt)
    state["jd_skills"] = response.content
    return state


def resume_analyzer(state: State):
    print("\n[Resume Analyzer Started to work...]")

    prompt = f"""
    {OUTPUT_STYLE_GUIDE}

    Analyze the following resume and extract the strongest signals.

    Return the result in this plain-text structure:

    TECHNICAL SKILLS: item1, item2, item3
    TOOLS AND PLATFORMS: item1, item2, item3
    EXPERIENCE AREAS:
    1. item
    2. item
    STRENGTH SIGNALS:
    1. item
    2. item

    Resume:
    {state['resume']}
    """

    response = _invoke_llm(prompt)
    state["resume_skills"] = response.content
    return state


def scoring_agent(state: State):
    print("\n[Scoring Agent Started to work...]")

    prompt = f"""
{OUTPUT_STYLE_GUIDE}

You are an ATS scoring system.

Return output STRICTLY in this format:

ATS SCORE: <number>/100

MATCHING SKILLS: skill1, skill2, skill3

MISSING SKILLS: skill1, skill2, skill3

SUMMARY:
2 to 3 short sentences only

TOP PRIORITY:
1 short sentence only

JD Skills:
{state['jd_skills']}

Resume Skills:
{state['resume_skills']}
"""

    response = _invoke_llm(prompt)
    state["score"] = response.content
    return state


def improvement_agent(state: State):
    print("\n[Review Agent Started to work...]")

    prompt = f"""
    {OUTPUT_STYLE_GUIDE}

    Based on the gap between the job description and the resume, provide resume-specific guidance.

    Return the result in this plain-text structure:

    PRIORITY IMPROVEMENTS:
    1. item
    2. item
    3. item

    SKILLS TO SURFACE: item1, item2, item3

    ATS KEYWORDS: item1, item2, item3

    PROJECTS TO MENTION:
    1. item
    2. item

    SECTION REWRITE FOCUS:
    1. item
    2. item

    JD Skills:
    {state['jd_skills']}

    Resume Skills:
    {state['resume_skills']}
    """

    response = _invoke_llm(prompt)
    state["suggestions"] = response.content
    return state


def project_suggestion_agent(state: State):
    print("\n[Suggestion Agent Started to work...]")

    prompt = f"""
{OUTPUT_STYLE_GUIDE}

Suggest 2 strong, resume-ready projects based on the missing skills.

Return output STRICTLY in this structure:

PROJECT 1 TITLE: <title>
PROJECT 1 TECH STACK: item1, item2, item3
PROJECT 1 KEY FEATURES:
1. item
2. item
3. item
PROJECT 1 WHY IT HELPS:
1. item
2. item

PROJECT 2 TITLE: <title>
PROJECT 2 TECH STACK: item1, item2, item3
PROJECT 2 KEY FEATURES:
1. item
2. item
3. item
PROJECT 2 WHY IT HELPS:
1. item
2. item

Job Description:
{state['job_description']}

Resume Skills:
{state['resume_skills']}
"""

    response = _invoke_llm(prompt)
    state["project_suggestions"] = response.content
    return state


builder = StateGraph(State)

builder.add_node("jd_analyzer", jd_analyzer)
builder.add_node("resume_analyzer", resume_analyzer)
builder.add_node("scoring", scoring_agent)
builder.add_node("improvement", improvement_agent)
builder.add_node("project_suggestion", project_suggestion_agent)

builder.set_entry_point("jd_analyzer")

builder.add_edge("jd_analyzer", "resume_analyzer")
builder.add_edge("resume_analyzer", "scoring")
builder.add_edge("scoring", "improvement")
builder.add_edge("improvement", "project_suggestion")
builder.add_edge("project_suggestion", END)

graph = builder.compile()


def _build_state(jd: str, resume_text: str) -> State:
    return {
        "job_description": jd,
        "resume": resume_text,
        "jd_skills": "",
        "resume_skills": "",
        "score": "",
        "suggestions": "",
        "project_suggestions": "",
    }


def run_resume_analysis(jd: str, resume_text: str):
    state = _build_state(jd, resume_text)

    try:
        return graph.invoke(state)
    except ResumeAnalyzerError:
        raise
    except AuthenticationError as exc:
        config = _resolve_primary_llm_config()
        raise ResumeAnalyzerError(
            f"Authentication failed for {config['provider']} using {config['source']}. "
            "Check that the key in .env matches the selected provider."
        ) from exc
    except NotFoundError as exc:
        config = _resolve_primary_llm_config()
        raise ResumeAnalyzerError(
            f"Model '{config['model']}' is not available for {config['provider']}. "
            "Set OPENAI_MODEL, OPENROUTER_MODEL, or GROQ_MODEL in .env to a valid model."
        ) from exc
    except APIConnectionError as exc:
        config = _resolve_primary_llm_config()
        raise ResumeAnalyzerError(
            f"Could not reach the {config['provider']} API. "
            "Check your internet connection, firewall, or proxy settings. "
            "If you need system proxy variables, set LLM_TRUST_ENV=true in .env."
        ) from exc
    except RateLimitError as exc:
        config = _resolve_primary_llm_config()
        raise ResumeAnalyzerError(
            f"The {config['provider']} key in {config['source']} is out of quota or rate-limited, and no fallback provider was available. "
            "Add billing to that account, add GROQ_API_KEY, or switch to a funded provider key."
        ) from exc


def main():
    print("=== Resume Analyzer ===")
    print(f"Using LLM: {get_llm_summary()}")

    jd = input("\nEnter Job Description:\n")
    resume = input("\nEnter Resume:\n")

    result = run_resume_analysis(jd, resume)

    print("\n=== FINAL OUTPUT ===")
    print("\nScore:\n", result["score"])
    print("\nSuggestions:\n", result["suggestions"])
    print("\nProject Suggestions:\n", result["project_suggestions"])


if __name__ == "__main__":
    main()
