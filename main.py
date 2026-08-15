from __future__ import annotations

import html
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

BASE_DIR = Path(__file__).resolve().parent
RESUME_PATH = BASE_DIR / "resume.txt"
TEMPLATE_PATH = BASE_DIR / "template.html"
CSS_PATH = BASE_DIR / "style.css"
OUTPUT_PATH = BASE_DIR / "index.html"
PHOTO_PATH = BASE_DIR / "photo.jpg"

MIN_RESUME_CHARS = 80
ALLOWED_THEMES = {"vivid", "bold", "editorial", "dark"}
DEFAULT_MODEL = "gemini-2.5-flash"

PORTFOLIO_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "headline": {"type": "string"},
        "summary": {"type": "string"},
        "skills": {"type": "array", "items": {"type": "string"}},
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "degree": {"type": "string"},
                    "institution": {"type": "string"},
                    "dates": {"type": "string"},
                    "details": {"type": "string"},
                },
                "required": ["degree", "institution", "dates", "details"],
            },
        },
        "experience": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "role": {"type": "string"},
                    "company": {"type": "string"},
                    "dates": {"type": "string"},
                    "details": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["role", "company", "dates", "details"],
            },
        },
        "projects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "technologies": {"type": "array", "items": {"type": "string"}},
                    "link": {"type": "string"},
                },
                "required": ["title", "description", "technologies", "link"],
            },
        },
        "achievements": {"type": "array", "items": {"type": "string"}},
        "contact": {
            "type": "object",
            "properties": {
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "linkedin": {"type": "string"},
                "github": {"type": "string"},
                "links": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["email", "phone", "linkedin", "github", "links"],
        },
        "availability": {"type": "string"},
    },
    "required": [
        "name", "headline", "summary", "skills", "education", "experience",
        "projects", "achievements", "contact", "availability",
    ],
}


def clean_resume(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def load_resume() -> str:
    if not RESUME_PATH.exists():
        raise RuntimeError("resume.txt is missing. Add your resume text and run again.")
    try:
        raw = RESUME_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Could not read resume.txt: {exc}") from exc
    cleaned = clean_resume(raw)
    if not cleaned:
        raise RuntimeError("resume.txt is empty. Add resume content and run again.")
    if len(cleaned) < MIN_RESUME_CHARS:
        raise RuntimeError(
            f"resume.txt is too short ({len(cleaned)} characters). "
            f"Please provide at least {MIN_RESUME_CHARS} characters."
        )
    return cleaned


def build_prompt(resume_text: str) -> str:
    return f"""You are a careful resume-to-portfolio extraction assistant.

Use ONLY information explicitly present in the resume below. Do not invent, infer, embellish,
or add skills, experience, projects, achievements, companies, dates, education, links, contact
information, job titles, metrics, awards, or availability that are not supported by the resume.
Do not use generic filler. If a field is not present, return an empty string or empty array.
Keep the professional summary concise and factual, based only on the resume.

Return JSON ONLY matching the supplied schema. No Markdown fences, commentary, or explanation.

Resume:
---
{resume_text}
---
"""


def _strip_json_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def parse_json_safely(raw: str) -> dict[str, Any]:
    if not isinstance(raw, str) or not raw.strip():
        raise RuntimeError("Gemini returned an empty JSON response.")
    cleaned = _strip_json_fences(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON response from Gemini: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError("Gemini JSON must be a top-level object.")
    return normalize_portfolio(data)


def _string(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def normalize_portfolio(data: dict[str, Any]) -> dict[str, Any]:
    contact_raw = data.get("contact") if isinstance(data.get("contact"), dict) else {}
    education = []
    for item in data.get("education", []) if isinstance(data.get("education"), list) else []:
        if not isinstance(item, dict):
            continue
        education.append({
            "degree": _string(item.get("degree")),
            "institution": _string(item.get("institution")),
            "dates": _string(item.get("dates")),
            "details": _string(item.get("details")),
        })

    experience = []
    for item in data.get("experience", []) if isinstance(data.get("experience"), list) else []:
        if not isinstance(item, dict):
            continue
        experience.append({
            "role": _string(item.get("role")),
            "company": _string(item.get("company")),
            "dates": _string(item.get("dates")),
            "details": _string_list(item.get("details")),
        })

    projects = []
    for item in data.get("projects", []) if isinstance(data.get("projects"), list) else []:
        if not isinstance(item, dict):
            continue
        projects.append({
            "title": _string(item.get("title")),
            "description": _string(item.get("description")),
            "technologies": _string_list(item.get("technologies")),
            "link": _string(item.get("link")),
        })

    return {
        "name": _string(data.get("name")),
        "headline": _string(data.get("headline")),
        "summary": _string(data.get("summary")),
        "skills": _string_list(data.get("skills")),
        "education": education,
        "experience": experience,
        "projects": projects,
        "achievements": _string_list(data.get("achievements")),
        "contact": {
            "email": _string(contact_raw.get("email")),
            "phone": _string(contact_raw.get("phone")),
            "linkedin": _string(contact_raw.get("linkedin")),
            "github": _string(contact_raw.get("github")),
            "links": _string_list(contact_raw.get("links")),
        },
        "availability": _string(data.get("availability")),
    }


def infer_theme(data: dict[str, Any]) -> str:
    manual = os.getenv("THEME", "").strip().lower()
    if manual in ALLOWED_THEMES:
        return manual

    searchable = " ".join([
        data.get("headline", ""),
        " ".join(data.get("skills", [])),
        data.get("summary", ""),
    ]).lower()
    if re.search(r"\b(designer|design|artist|illustrator|photographer|creative|typograph|art director)\b", searchable):
        return "bold"
    if re.search(r"\b(developer|engineer|software|backend|frontend|full[- ]stack|data engineer|devops|programmer|cybersecurity)\b", searchable):
        return "dark"
    if re.search(r"\b(writer|editor|researcher|architect|journalist|author)\b", searchable):
        return "editorial"
    return "vivid"


def call_gemini(prompt: str) -> dict[str, Any]:
    if genai is None or types is None:
        raise RuntimeError("Missing Gemini SDK. Install dependencies with: pip install -r requirements.txt")

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured. Copy .env.example to .env and add your key.")

    model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=PORTFOLIO_SCHEMA,
                temperature=0.2,
            ),
        )
        return parse_json_safely(response.text or "")
    except Exception as exc:
        raise RuntimeError(f"Gemini API request failed: {exc}") from exc


def esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def safe_href(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if re.match(r"^(https?://|mailto:|tel:|#)", value, re.IGNORECASE):
        return esc(value)
    return ""


def icon(kind: str) -> str:
    icons = {
        "mail": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>',
        "phone": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>',
        "linkedin": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 8.76a1.65 1.65 0 1 0 0-3.3 1.65 1.65 0 0 0 0 3.3m1.4 9.74v-8.37H5.06v8.37z"/></svg>',
        "github": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0 0 22 12.017C22 6.484 17.522 2 12 2z"/></svg>',
        "link": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>',
    }
    return icons.get(kind, icons["link"])


def render_nav(data: dict[str, Any]) -> str:
    sections = [("home", "Home", True)]
    if data["summary"] or data["skills"]:
        sections.append(("profile", "Profile", False))
    if data["experience"]:
        sections.append(("experience", "Experience", False))
    if data["projects"]:
        sections.append(("projects", "Projects", False))
    if data["education"]:
        sections.append(("education", "Education", False))
    if data["achievements"]:
        sections.append(("achievements", "Achievements", False))
    if any(data["contact"].values()):
        sections.append(("contact", "Contact", False))
    links = []
    for sid, label, first in sections:
        active = "is-active" if first else ""
        links.append(f'<a href="#{sid}" data-nav="{sid}" class="{active}">{label}</a>')
    return "".join(links)


def render_sections(data: dict[str, Any]) -> str:
    parts: list[str] = []
    if data["summary"] or data["skills"]:
        summary_html = f'<p class="summary">{esc(data["summary"])}</p>' if data["summary"] else ""
        skill_html = "".join(f'<span class="chip">{esc(skill)}</span>' for skill in data["skills"])
        skills_html = f'<div class="skill-stack">{skill_html}</div>' if skill_html else ""
        parts.append(f'''<section id="profile" class="section section-profile" data-section="profile">
          <h2 class="section-title">Profile</h2>
          <div class="profile-grid">{summary_html}{skills_html}</div>
        </section>''')

    if data["experience"]:
        items = []
        for item in data["experience"]:
            body = "".join(f"<li>{esc(point)}</li>" for point in item["details"])
            items.append(f'''<article class="timeline-item">
              <div class="timeline-date">{esc(item["dates"])}</div>
              <div><h3>{esc(item["role"])}</h3>{f'<p class="muted">{esc(item["company"])}</p>' if item["company"] else ''}{f'<ul>{body}</ul>' if body else ''}</div>
            </article>''')
        parts.append(f'''<section id="experience" class="section" data-section="experience">
          <h2 class="section-title">Experience</h2>
          <div class="timeline">{"".join(items)}</div>
        </section>''')

    if data["projects"]:
        cards = []
        for item in data["projects"]:
            tags = "".join(f'<span class="project-chip">{esc(t)}</span>' for t in item["technologies"])
            href = safe_href(item["link"])
            title = f'<a href="{href}" target="_blank" rel="noopener">{esc(item["title"])} ↗</a>' if href else esc(item["title"])
            cards.append(f'''<article class="project-card" data-project-tags="{esc("|".join(item["technologies"]).lower())}">
              <h3>{title}</h3>
              {f'<p>{esc(item["description"])}</p>' if item["description"] else ''}
              {f'<div class="project-tags">{tags}</div>' if tags else ''}
            </article>''')
        all_tags = sorted({t for p in data["projects"] for t in p["technologies"] if t})
        filters = '<button class="filter-btn is-active" type="button" data-filter="all">All</button>' + "".join(
            f'<button class="filter-btn" type="button" data-filter="{esc(tag.lower())}">{esc(tag)}</button>' for tag in all_tags
        )
        parts.append(f'''<section id="projects" class="section" data-section="projects">
          <h2 class="section-title">Projects</h2>
          <div class="project-toolbar"><div class="project-filter" aria-label="Filter projects by technology">{filters}</div></div>
          <div class="projects-grid">{"".join(cards)}</div>
          <p class="empty-filter" hidden>No projects match this filter.</p>
        </section>''')

    if data["education"]:
        cards = "".join(f'''<article class="education-card"><div><h3>{esc(i["degree"])}</h3>
          {f'<p class="muted">{esc(i["institution"])}</p>' if i["institution"] else ''}
          {f'<p class="date-line">{esc(i["dates"])}</p>' if i["dates"] else ''}</div>
          {f'<p>{esc(i["details"])}</p>' if i["details"] else ''}</article>''' for i in data["education"])
        parts.append(f'<section id="education" class="section" data-section="education"><h2 class="section-title">Education</h2><div class="education-grid">{cards}</div></section>')

    if data["achievements"]:
        items = "".join(f'<li><span class="achievement-mark">+</span>{esc(a)}</li>' for a in data["achievements"])
        parts.append(f'<section id="achievements" class="section" data-section="achievements"><h2 class="section-title">Achievements</h2><ul class="achievement-list">{items}</ul></section>')

    contact = data["contact"]
    if any(contact.values()):
        links: list[str] = []
        if contact["email"]:
            href = safe_href("mailto:" + contact["email"])
            links.append(f'<a class="contact-link" href="{href}">{icon("mail")}<span>{esc(contact["email"])}</span></a>')
        if contact["phone"]:
            href = safe_href("tel:" + re.sub(r"[^+\d]", "", contact["phone"]))
            links.append(f'<a class="contact-link" href="{href}">{icon("phone")}<span>{esc(contact["phone"])}</span></a>')
        if contact.get("linkedin"):
            href = safe_href(contact["linkedin"])
            if href:
                links.append(f'<a class="contact-link" href="{href}" target="_blank" rel="noopener">{icon("linkedin")}<span>LinkedIn Profile</span></a>')
        if contact.get("github"):
            href = safe_href(contact["github"])
            if href:
                links.append(f'<a class="contact-link" href="{href}" target="_blank" rel="noopener">{icon("github")}<span>GitHub Profile</span></a>')
        for link in contact.get("links", []):
            href = safe_href(link)
            if href:
                links.append(f'<a class="contact-link" href="{href}" target="_blank" rel="noopener">{icon("link")}<span>{esc(link)}</span></a>')

        parts.append(f'''<section id="contact" class="section section-contact" data-section="contact">
          <div class="contact-wrap">
            <div>
              <h2 class="section-title">Get In Touch</h2>
              <p class="contact-desc">Feel free to reach out for collaborations, questions, or internship opportunities.</p>
            </div>
            <div class="contact-links">{"".join(links)}</div>
          </div>
        </section>''')
    return "".join(parts)


def render_portfolio(data: dict[str, Any], theme: str, template: str, css: str) -> str:
    name = data["name"] or "Portfolio"
    headline = data["headline"]
    availability = data["availability"]
    badge = f'<span class="availability-badge">{esc(availability)}</span>' if availability else ''
    photo = "photo.jpg" if PHOTO_PATH.exists() else ""
    hero_visual = f'<img class="hero-photo" src="{photo}" alt="" loading="eager">' if photo else '<div class="hero-art" aria-hidden="true"><span></span><span></span><span></span><i></i></div>'
    replacements = {
        "{{THEME}}": esc(theme),
        "{{NAME}}": esc(name),
        "{{HEADLINE}}": esc(headline),
        "{{BADGE}}": badge,
        "{{HERO_VISUAL}}": hero_visual,
        "{{NAV}}": render_nav(data),
        "{{SECTIONS}}": render_sections(data),
        "{{YEAR}}": "2026",
    }
    output = template
    for key, value in replacements.items():
        output = output.replace(key, value)
    return output.replace("{{STYLE}}", css)


def mock_data() -> dict[str, Any]:
    return normalize_portfolio({
        "name": "Aarav Mehta",
        "headline": "Python Developer & Data Engineering Student",
        "summary": "Computer science student focused on Python, databases and practical data engineering projects.",
        "skills": ["Python", "SQL", "DBMS", "HTML", "JavaScript", "Git"],
        "education": [{"degree": "B.Tech", "institution": "GLA University", "dates": "2024–2028", "details": ""}],
        "experience": [],
        "projects": [
            {"title": "Resume Portfolio Generator", "description": "A Python application that converts resume text into a structured portfolio.", "technologies": ["Python", "Gemini API", "HTML", "CSS"], "link": ""},
            {"title": "Database Practice Suite", "description": "SQL and DBMS practice work covering joins and normalization.", "technologies": ["SQL", "DBMS"], "link": ""},
        ],
        "achievements": [],
        "contact": {
            "email": "aarav@example.com",
            "phone": "+91 98765 43210",
            "linkedin": "https://linkedin.com/in/aaravmehta",
            "github": "https://github.com/aaravmehta",
            "links": []
        },
        "availability": "Open to internships",
    })


def main() -> int:
    if load_dotenv:
        load_dotenv(BASE_DIR / ".env")
    try:
        resume = load_resume()
        if not TEMPLATE_PATH.exists() or not CSS_PATH.exists():
            raise RuntimeError("template.html and style.css must exist beside main.py.")

        if "--mock" in sys.argv:
            data = mock_data()
            print("Running local mock mode; no Gemini API request was made.")
        else:
            data = call_gemini(build_prompt(resume))

        theme = infer_theme(data)
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        css = CSS_PATH.read_text(encoding="utf-8")
        OUTPUT_PATH.write_text(render_portfolio(data, theme, template, css), encoding="utf-8")

        print(f"Generated: {OUTPUT_PATH.name}")
        print(f"Theme: {theme}")
        if PHOTO_PATH.exists():
            print("Hero photo: photo.jpg")
        else:
            print("Hero photo: not found; using CSS-generated art.")
        return 0
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"File error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())