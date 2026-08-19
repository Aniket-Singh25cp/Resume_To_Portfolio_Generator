from http.server import BaseHTTPRequestHandler
import json
import os
import re
import html
from pathlib import Path
from typing import Any

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

BASE_DIR = Path(__file__).resolve().parent.parent
RESUME_PATH = BASE_DIR / "resume.txt"
TEMPLATE_PATH = BASE_DIR / "template.html"
CSS_PATH = BASE_DIR / "style.css"

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

def normalize_portfolio(data: dict[str, Any]) -> dict[str, Any]:
    def _s(v): return v.strip() if isinstance(v, str) else ""
    def _l(v): return [i.strip() for i in v if isinstance(i, str) and i.strip()] if isinstance(v, list) else []
    contact_raw = data.get("contact") if isinstance(data.get("contact"), dict) else {}
    return {
        "name": _s(data.get("name")),
        "headline": _s(data.get("headline")),
        "summary": _s(data.get("summary")),
        "skills": _l(data.get("skills")),
        "education": [{"degree": _s(i.get("degree")), "institution": _s(i.get("institution")), "dates": _s(i.get("dates")), "details": _s(i.get("details"))} for i in data.get("education", []) if isinstance(i, dict)],
        "experience": [{"role": _s(i.get("role")), "company": _s(i.get("company")), "dates": _s(i.get("dates")), "details": _l(i.get("details"))} for i in data.get("experience", []) if isinstance(i, dict)],
        "projects": [{"title": _s(i.get("title")), "description": _s(i.get("description")), "technologies": _l(i.get("technologies")), "link": _s(i.get("link"))} for i in data.get("projects", []) if isinstance(i, dict)],
        "achievements": _l(data.get("achievements")),
        "contact": {
            "email": _s(contact_raw.get("email")),
            "phone": _s(contact_raw.get("phone")),
            "linkedin": _s(contact_raw.get("linkedin")),
            "github": _s(contact_raw.get("github")),
            "links": _l(contact_raw.get("links")),
        },
        "availability": _s(data.get("availability")),
    }

def esc(v: Any) -> str: return html.escape(str(v or ""), quote=True)
def safe_href(v: str) -> str: return esc(v.strip()) if re.match(r"^(https?://|mailto:|tel:|#)", v.strip(), re.I) else ""

def icon(kind: str) -> str:
    icons = {
        "mail": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>',
        "phone": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>',
        "linkedin": '<svg viewBox="0 0 24 24"><path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 8.76a1.65 1.65 0 1 0 0-3.3 1.65 1.65 0 0 0 0 3.3m1.4 9.74v-8.37H5.06v8.37z"/></svg>',
        "github": '<svg viewBox="0 0 24 24"><path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/></svg>',
        "link": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>',
    }
    return icons.get(kind, icons["link"])

def render_html(data: dict[str, Any], template: str, css: str) -> str:
    # Navigation
    sections = [("home", "Home", True)]
    if data["summary"] or data["skills"]: sections.append(("profile", "Profile", False))
    if data["experience"]: sections.append(("experience", "Experience", False))
    if data["projects"]: sections.append(("projects", "Projects", False))
    if data["education"]: sections.append(("education", "Education", False))
    if data["achievements"]: sections.append(("achievements", "Achievements", False))
    if any(data["contact"].values()): sections.append(("contact", "Contact", False))
    nav = "".join(f'<a href="#{sid}" data-nav="{sid}" class="{"is-active" if first else ""}">{label}</a>' for sid, label, first in sections)

    # Sections
    parts = []
    if data["summary"] or data["skills"]:
        s_html = f'<p class="summary">{esc(data["summary"])}</p>' if data["summary"] else ""
        k_html = f'<div class="skill-stack">{"".join(f"<span class=\'chip\'>{esc(s)}</span>" for s in data["skills"])}</div>' if data["skills"] else ""
        parts.append(f'<section id="profile" class="section section-profile" data-section="profile"><h2 class="section-title">Profile</h2><div class="profile-grid">{s_html}{k_html}</div></section>')

    if data["experience"]:
        items = "".join(f'<article class="timeline-item"><div class="timeline-date">{esc(i["dates"])}</div><div><h3>{esc(i["role"])}</h3><p class="muted">{esc(i["company"])}</p><ul>{"".join(f"<li>{esc(d)}</li>" for d in i["details"])}</ul></div></article>' for i in data["experience"])
        parts.append(f'<section id="experience" class="section" data-section="experience"><h2 class="section-title">Experience</h2><div class="timeline">{items}</div></section>')

    if data["projects"]:
        cards = []
        for item in data["projects"]:
            tags = "".join(f'<span class="project-chip">{esc(t)}</span>' for t in item["technologies"])
            h = safe_href(item["link"])
            t = f'<a href="{h}" target="_blank" rel="noopener">{esc(item["title"])} ↗</a>' if h else esc(item["title"])
            cards.append(f'<article class="project-card" data-project-tags="{esc("|".join(item["technologies"]).lower())}"><h3>{t}</h3><p>{esc(item["description"])}</p><div class="project-tags">{tags}</div></article>')
        all_tags = sorted({t for p in data["projects"] for t in p["technologies"] if t})
        filters = '<button class="filter-btn is-active" type="button" data-filter="all">All</button>' + "".join(f'<button class="filter-btn" type="button" data-filter="{esc(t.lower())}">{esc(t)}</button>' for t in all_tags)
        parts.append(f'<section id="projects" class="section" data-section="projects"><h2 class="section-title">Projects</h2><div class="project-toolbar"><div class="project-filter">{filters}</div></div><div class="projects-grid">{"".join(cards)}</div><p class="empty-filter" hidden>No projects match this filter.</p></section>')

    if data["education"]:
        cards = "".join(f'<article class="education-card"><div><h3>{esc(i["degree"])}</h3><p class="muted">{esc(i["institution"])}</p><p class="date-line">{esc(i["dates"])}</p></div><p>{esc(i["details"])}</p></article>' for i in data["education"])
        parts.append(f'<section id="education" class="section" data-section="education"><h2 class="section-title">Education</h2><div class="education-grid">{cards}</div></section>')

    if data["achievements"]:
        items = "".join(f'<li><span class="achievement-mark">+</span>{esc(a)}</li>' for a in data["achievements"])
        parts.append(f'<section id="achievements" class="section" data-section="achievements"><h2 class="section-title">Achievements</h2><ul class="achievement-list">{items}</ul></section>')

    contact = data["contact"]
    if any(contact.values()):
        links = []
        if contact["email"]: links.append(f'<a class="contact-link" href="{safe_href("mailto:" + contact["email"])}">{icon("mail")}<span>{esc(contact["email"])}</span></a>')
        if contact["phone"]: links.append(f'<a class="contact-link" href="{safe_href("tel:" + re.sub(r"[^\d+]", "", contact["phone"]))}">{icon("phone")}<span>{esc(contact["phone"])}</span></a>')
        if contact["linkedin"]: links.append(f'<a class="contact-link" href="{safe_href(contact["linkedin"])}" target="_blank" rel="noopener">{icon("linkedin")}<span>LinkedIn</span></a>')
        if contact["github"]: links.append(f'<a class="contact-link" href="{safe_href(contact["github"])}" target="_blank" rel="noopener">{icon("github")}<span>GitHub</span></a>')
        for l in contact["links"]: links.append(f'<a class="contact-link" href="{safe_href(l)}" target="_blank" rel="noopener">{icon("link")}<span>{esc(l)}</span></a>')
        parts.append(f'<section id="contact" class="section section-contact" data-section="contact"><div class="contact-wrap"><div><h2 class="section-title">Get In Touch</h2><p class="contact-desc">Feel free to reach out for collaborations or opportunities.</p></div><div class="contact-links">{"".join(links)}</div></div></section>')

    # Embed CSS inline for self-contained iframe rendering
    inlined_template = template.replace('<link rel="stylesheet" href="style.css">', f'<style>{css}</style>')
    badge = f'<span class="availability-badge">{esc(data["availability"])}</span>' if data["availability"] else ''
    hero_art = '<div class="hero-art" aria-hidden="true"><span></span><span></span><span></span><i></i></div>'

    replacements = {
        "{{THEME}}": "vivid",
        "{{NAME}}": esc(data["name"] or "Portfolio"),
        "{{HEADLINE}}": esc(data["headline"]),
        "{{BADGE}}": badge,
        "{{HERO_VISUAL}}": hero_art,
        "{{NAV}}": nav,
        "{{SECTIONS}}": "".join(parts),
        "{{YEAR}}": "2026",
    }
    res = inlined_template
    for k, v in replacements.items():
        res = res.replace(k, v)
    return res

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("content-length", 0))
            body = json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}
            
            use_default = body.get("use_default", False)
            resume_text = ""
            if use_default:
                if RESUME_PATH.exists():
                    resume_text = RESUME_PATH.read_text(encoding="utf-8")
                else:
                    raise RuntimeError("Default resume.txt not found on server.")
            else:
                resume_text = body.get("resume_text", "")

            cleaned = clean_resume(resume_text)
            if len(cleaned) < 50:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Resume text is too short. Please provide at least 50 characters."}).encode())
                return

            api_key = os.environ.get("GEMINI_API_KEY", "").strip()
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY is not configured in Vercel environment.")

            client = genai.Client(api_key=api_key)
            prompt = f"Extract resume fields into JSON based ONLY on this text:\n---\n{cleaned}\n---"
            response = client.models.generate_content(
                model=os.environ.get("GEMINI_MODEL", DEFAULT_MODEL),
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=PORTFOLIO_SCHEMA,
                    temperature=0.2,
                ),
            )

            raw_json = response.text.strip()
            if raw_json.startswith("```"):
                raw_json = re.sub(r"^```(?:json)?\s*", "", raw_json, flags=re.I)
                raw_json = re.sub(r"\s*```$", "", raw_json)
            
            parsed = normalize_portfolio(json.loads(raw_json))
            template = TEMPLATE_PATH.read_text(encoding="utf-8")
            css = CSS_PATH.read_text(encoding="utf-8")
            html_output = render_html(parsed, template, css)

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"html": html_output, "data": parsed}).encode())

        except Exception as exc:
            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(exc)}).encode())