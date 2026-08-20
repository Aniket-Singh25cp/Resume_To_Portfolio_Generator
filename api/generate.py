import json
import os
import re
import html
import traceback
from pathlib import Path
from http.server import BaseHTTPRequestHandler

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

CURRENT_DIR = Path(__file__).parent.resolve()
BASE_DIR = CURRENT_DIR.parent
TEMPLATE_PATH = BASE_DIR / "template.html"
CSS_PATH = BASE_DIR / "style.css"
RESUME_PATH = BASE_DIR / "resume.txt"

def esc(v): return html.escape(str(v or ""), quote=True)

def get_icon(kind):
    icons = {
        "mail": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>',
        "phone": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>',
        "linkedin": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 8.76a1.65 1.65 0 1 0 0-3.3 1.65 1.65 0 0 0 0 3.3m1.4 9.74v-8.37H5.06v8.37z"/></svg>',
        "github": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0 0 22 12.017C22 6.484 17.522 2 12 2z"/></svg>'
    }
    return icons.get(kind, '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>')

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length).decode('utf-8'))
            
            use_default = body.get("use_default", False)
            resume_text = body.get("resume_text", "")
            if use_default and RESUME_PATH.exists():
                resume_text = RESUME_PATH.read_text(encoding="utf-8")

            client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=f"Return ONLY JSON. Extract resume into fields: name, headline, summary, availability, skills[], education[degree, institution, dates], experience[role, company, dates, details[]], projects[title, description, technologies[], link], contact{{email, phone, linkedin, github}}. Resume:\n{resume_text}",
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )

            data = json.loads(response.text)
            
            def get_safe(k, d=""): return data.get(k) or d

            name = get_safe("name", "Portfolio")
            headline = get_safe("headline")
            summary = get_safe("summary")
            skills = data.get("skills") or []
            availability = get_safe("availability")
            if len(availability) > 22: availability = availability[:19] + "..."

            sections_html = ""
            nav_html = '<a href="#home" data-nav="home" class="is-active">Home</a>'

            # 1. Profile
            if summary or skills:
                nav_html += '<a href="#profile" data-nav="profile">Profile</a>'
                chips = "".join(f'<span class="chip">{esc(s)}</span>' for s in skills[:10])
                if len(skills) > 10:
                    more = "".join(f'<span class="chip">{esc(s)}</span>' for s in skills[10:])
                    chips += f'<span hidden>{more}</span><button type="button" class="chip more-btn" onclick="this.previousElementSibling.hidden=false; this.remove();">+{len(skills)-10} more</button>'
                sections_html += f'<section id="profile" class="section" data-section="profile"><h2 class="section-title">Profile</h2><div class="profile-grid"><p class="summary">{esc(summary)}</p><div class="skill-stack">{chips}</div></div></section>'

            # 2. Projects
            projects = data.get("projects") or []
            if projects:
                nav_html += '<a href="#projects" data-nav="projects">Projects</a>'
                cards = "".join(f'<article class="project-card"><h3>{esc(p.get("title"))}</h3><p>{esc(p.get("description"))}</p><div class="project-tags">{" ".join(f"<span class=\'project-chip\'>{esc(t)}</span>" for t in p.get("technologies", []))}</div></article>' for p in projects if p.get("title"))
                sections_html += f'<section id="projects" class="section" data-section="projects"><h2 class="section-title">Projects</h2><div class="projects-grid">{cards}</div></section>'

            # 3. Contact (FIXED)
            contact = data.get("contact") or {}
            if any(contact.values()):
                nav_html += '<a href="#contact" data-nav="contact">Contact</a>'
                links = []
                if contact.get("email"): links.append(f'<a class="contact-link" href="mailto:{contact["email"]}">{get_icon("mail")}<span>{esc(contact["email"])}</span></a>')
                if contact.get("phone"): links.append(f'<a class="contact-link" href="tel:{re.sub(r"[^\d+]", "", contact["phone"])}">{get_icon("phone")}<span>{esc(contact["phone"])}</span></a>')
                if contact.get("linkedin"): links.append(f'<a class="contact-link" href="{esc(contact["linkedin"])}" target="_blank">{get_icon("linkedin")}<span>LinkedIn</span></a>')
                if contact.get("github"): links.append(f'<a class="contact-link" href="{esc(contact["github"])}" target="_blank">{get_icon("github")}<span>GitHub</span></a>')
                
                sections_html += f'''<section id="contact" class="section section-contact" data-section="contact">
                    <div class="contact-wrap">
                        <div><h2 class="section-title">Get In Touch</h2><p class="contact-desc">Let\'s discuss your next project or opportunity.</p></div>
                        <div class="contact-links">{"".join(links)}</div>
                    </div></section>'''

            template = TEMPLATE_PATH.read_text(encoding="utf-8")
            css = CSS_PATH.read_text(encoding="utf-8")
            badge = f'<span class="availability-badge">{esc(availability)}</span>' if availability else ""

            output = template.replace('<link rel="stylesheet" href="style.css">', f'<style>{css}</style>')
            output = output.replace('{{NAME}}', esc(name)).replace('{{HEADLINE}}', esc(headline))
            output = output.replace('{{NAV}}', nav_html).replace('{{SECTIONS}}', sections_html)
            output = output.replace('{{BADGE}}', badge).replace('{{YEAR}}', '2026')
            output = output.replace('{{HERO_VISUAL}}', '<div class="hero-art"><span></span><span></span><span></span><i></i></div>')

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"html": output}).encode())
        except Exception:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": traceback.format_exc()}).encode())