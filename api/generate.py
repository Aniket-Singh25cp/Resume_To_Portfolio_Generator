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

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length).decode('utf-8'))
            
            use_default = body.get("use_default", False)
            resume_text = body.get("resume_text", "")
            
            if use_default and RESUME_PATH.exists():
                resume_text = RESUME_PATH.read_text(encoding="utf-8")

            # 1. API Call
            client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=f"Return ONLY JSON. Extract resume into fields: name, headline, summary, availability, skills[], education[degree, institution, dates], experience[role, company, dates, details[]], projects[title, description, technologies[], link], contact{{email, linkedin, github}}. Resume:\n{resume_text}",
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )

            data = json.loads(response.text)
            
            # --- SAFE DATA EXTRACTION (Fixes the NoneType Error) ---
            def get_safe(key, default=""): return data.get(key) or default

            name = get_safe("name", "Portfolio")
            headline = get_safe("headline", "")
            summary = get_safe("summary")
            skills = data.get("skills") or []
            availability = get_safe("availability")
            
            # Process availability length safely
            if len(availability) > 22:
                availability = availability[:19] + "..."

            sections_html = ""
            nav_html = '<a href="#home" data-nav="home" class="is-active">Home</a>'

            # 2. Render Profile
            if summary or skills:
                nav_html += '<a href="#profile" data-nav="profile">Profile</a>'
                skill_chips = "".join(f'<span class="chip">{esc(s)}</span>' for s in skills[:10])
                if len(skills) > 10:
                    more = "".join(f'<span class="chip">{esc(s)}</span>' for s in skills[10:])
                    skill_chips += f'<span hidden>{more}</span><button type="button" class="chip more-btn" onclick="this.previousElementSibling.hidden=false; this.remove();">+{len(skills)-10} more</button>'
                
                sections_html += f'<section id="profile" class="section" data-section="profile"><h2 class="section-title">Profile</h2><div class="profile-grid"><p class="summary">{esc(summary)}</p><div class="skill-stack">{skill_chips}</div></div></section>'

            # 3. Render Projects
            projects = data.get("projects") or []
            if projects:
                nav_html += '<a href="#projects" data-nav="projects">Projects</a>'
                proj_cards = "".join(f'<article class="project-card"><h3>{esc(p.get("title"))}</h3><p>{esc(p.get("description"))}</p><div>{" ".join(f"<span class=\'project-chip\'>{esc(t)}</span>" for t in p.get("technologies", []))}</div></article>' for p in projects if p.get("title"))
                if proj_cards:
                    sections_html += f'<section id="projects" class="section" data-section="projects"><h2 class="section-title">Projects</h2><div class="projects-grid">{proj_cards}</div></section>'

            # 4. Final Assembly
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