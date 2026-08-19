import json
import os
import re
import html
from pathlib import Path
from http.server import BaseHTTPRequestHandler

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = BASE_DIR / "template.html"
CSS_PATH = BASE_DIR / "style.css"
RESUME_PATH = BASE_DIR / "resume.txt"

def esc(v): return html.escape(str(v or ""), quote=True)

def safe_href(v):
    v = str(v or "").strip()
    if re.match(r"^(https?://|mailto:|tel:|#)", v, re.I): return esc(v)
    return ""

def infer_theme(data):
    searchable = f"{data.get('headline', '')} {' '.join(data.get('skills', []))} {data.get('summary', '')}".lower()
    if any(k in searchable for k in ["design", "artist", "creative", "ui", "ux"]): return "bold"
    if any(k in searchable for k in ["developer", "engineer", "data", "python", "software", "tech"]): return "dark"
    if any(k in searchable for k in ["writer", "author", "editor", "research"]): return "editorial"
    return "vivid"

def get_icon(kind):
    icons = {
        "mail": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>',
        "linkedin": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 8.76a1.65 1.65 0 1 0 0-3.3 1.65 1.65 0 0 0 0 3.3m1.4 9.74v-8.37H5.06v8.37z"/></svg>',
        "github": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/></svg>'
    }
    return icons.get(kind, '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="12" y1="2" x2="12" y2="22"/></svg>')

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length).decode('utf-8'))
            
            resume_text = body.get("resume_text", "")
            if body.get("use_default") and RESUME_PATH.exists():
                resume_text = RESUME_PATH.read_text(encoding="utf-8")
            
            # API Call
            client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
            prompt = f"Extract resume into JSON. Fields: name, headline, summary, availability, skills[], education[degree, institution, dates], experience[role, company, dates, details[]], projects[title, description, technologies[], link], contact{{email, linkedin, github}}. Text:\n{resume_text}"
            
            response = client.models.generate_content(
                model=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"),
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            data = json.loads(response.text)
            theme = infer_theme(data)

            # Build HTML Pieces
            nav = '<a href="#home" data-nav="home" class="is-active">Home</a>'
            sections = ""
            
            # Profile
            if data.get("summary") or data.get("skills"):
                nav += '<a href="#profile" data-nav="profile">Profile</a>'
                chips = "".join(f'<span class="chip">{esc(s)}</span>' for s in data.get("skills", []))
                sections += f'<section id="profile" class="section" data-section="profile"><h2 class="section-title">Profile</h2><div class="profile-grid"><p class="summary">{esc(data.get("summary"))}</p><div class="skill-stack">{chips}</div></div></section>'

            # Projects
            if data.get("projects"):
                nav += '<a href="#projects" data-nav="projects">Projects</a>'
                proj_cards = "".join(f'<article class="project-card"><h3>{esc(p["title"])}</h3><p>{esc(p["description"])}</p><div class="project-tags">{" ".join(f"<span class=\'project-chip\'>{esc(t)}</span>" for t in p.get("technologies", []))}</div></article>' for p in data["projects"])
                sections += f'<section id="projects" class="section" data-section="projects"><h2 class="section-title">Projects</h2><div class="projects-grid">{proj_cards}</div></section>'

            # Experience
            if data.get("experience"):
                nav += '<a href="#experience" data-nav="experience">Experience</a>'
                items = "".join(f'<article class="timeline-item"><div class="timeline-date">{esc(exp["dates"])}</div><div><h3>{esc(exp["role"])}</h3><p class="muted">{esc(exp["company"])}</p><ul>{" ".join(f"<li>{esc(d)}</li>" for d in exp.get("details", []))}</ul></div></article>' for exp in data["experience"])
                sections += f'<section id="experience" class="section" data-section="experience"><h2 class="section-title">Experience</h2><div class="timeline">{items}</div></section>'

            # Contact
            nav += '<a href="#contact" data-nav="contact">Contact</a>'
            contact = data.get("contact", {})
            c_links = ""
            if contact.get("email"): c_links += f'<a class="contact-link" href="mailto:{contact["email"]}">{get_icon("mail")}<span>{contact["email"]}</span></a>'
            if contact.get("linkedin"): c_links += f'<a class="contact-link" href="{safe_href(contact["linkedin"])}" target="_blank">{get_icon("linkedin")}<span>LinkedIn</span></a>'
            if contact.get("github"): c_links += f'<a class="contact-link" href="{safe_href(contact["github"])}" target="_blank">{get_icon("github")}<span>GitHub</span></a>'
            sections += f'<section id="contact" class="section section-contact" data-section="contact"><div class="contact-wrap"><div><h2 class="section-title">Get In Touch</h2></div><div class="contact-links">{c_links}</div></div></section>'

            # Final Assembly
            template = TEMPLATE_PATH.read_text(encoding="utf-8")
            css = CSS_PATH.read_text(encoding="utf-8")
            
            output = template.replace('<link rel="stylesheet" href="style.css">', f'<style>{css}</style>')
            output = output.replace('data-theme="{{THEME}}"', f'data-theme="{theme}"')
            output = output.replace('{{NAME}}', esc(data.get("name", "Portfolio")))
            output = output.replace('{{HEADLINE}}', esc(data.get("headline", "")))
            output = output.replace('{{NAV}}', nav)
            output = output.replace('{{SECTIONS}}', sections)
            output = output.replace('{{YEAR}}', '2026')
            output = output.replace('{{HERO_VISUAL}}', '<div class="hero-art" aria-hidden="true"><span></span><span></span><span></span><i></i></div>')
            
            badge = f'<span class="availability-badge">{esc(data.get("availability"))}</span>' if data.get("availability") else ""
            output = output.replace('{{BADGE}}', badge)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"html": output}).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())