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

# VERCEL PATH FIX
CURRENT_DIR = Path(__file__).parent.resolve()
BASE_DIR = CURRENT_DIR.parent
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
    return "vivid"

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(content_length).decode('utf-8'))
            
            resume_text = body.get("resume_text", "")
            if body.get("use_default") and RESUME_PATH.exists():
                resume_text = RESUME_PATH.read_text(encoding="utf-8")
            
            if not resume_text or len(resume_text) < 10:
                raise ValueError("Resume text is too short.")

            # Gemini 3.5 Flash
            api_key = os.environ.get("GEMINI_API_KEY")
            client = genai.Client(api_key=api_key)
            
            prompt = f"Return ONLY JSON. Extract resume: name, headline, summary, availability, skills[], education[degree, institution, dates], experience[role, company, dates, details[]], projects[title, description, technologies[], link], contact{{email, linkedin, github}}. Text:\n{resume_text}"
            
            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )

            data = json.loads(response.text)
            theme = infer_theme(data)

            # HTML Components
            nav = '<a href="#home" data-nav="home" class="is-active">Home</a>'
            sections = ""
            
            # 1. Profile & Skills (Dropdown Logic)
            if data.get("summary") or data.get("skills"):
                nav += '<a href="#profile" data-nav="profile">Profile</a>'
                skills = data.get("skills", [])
                visible_skills = skills[:10]
                hidden_skills = skills[10:]
                
                skill_html = "".join(f'<span class="chip">{esc(s)}</span>' for s in visible_skills)
                if hidden_skills:
                    skill_html += f'<span class="hidden-skills" hidden>{"".join(f"<span class=\'chip\'>{esc(s)}</span>" for s in hidden_skills)}</span>'
                    skill_html += f'<button type="button" class="chip more-btn" onclick="this.previousElementSibling.hidden=false; this.remove();">+{len(hidden_skills)} more</button>'
                
                sections += f'''<section id="profile" class="section section-profile" data-section="profile">
                    <h2 class="section-title">Profile</h2>
                    <div class="profile-grid">
                        <p class="summary">{esc(data.get("summary"))}</p>
                        <div class="skill-stack">{skill_html}</div>
                    </div></section>'''

            # 2. Projects (Grid Fix handled in CSS)
            if data.get("projects"):
                nav += '<a href="#projects" data-nav="projects">Projects</a>'
                cards = "".join(f'<article class="project-card"><h3>{esc(p.get("title"))}</h3><p>{esc(p.get("description"))}</p><div class="project-tags">{" ".join(f"<span class=\'project-chip\'>{esc(t)}</span>" for t in p.get("technologies", []))}</div></article>' for p in data["projects"])
                sections += f'<section id="projects" class="section" data-section="projects"><h2 class="section-title">Projects</h2><div class="projects-grid">{cards}</div></section>'

            # 3. Experience
            if data.get("experience"):
                nav += '<a href="#experience" data-nav="experience">Experience</a>'
                items = "".join(f'<article class="timeline-item"><div class="timeline-date">{esc(exp.get("dates"))}</div><div><h3>{esc(exp.get("role"))}</h3><p class="muted">{esc(exp.get("company"))}</p><ul>{" ".join(f"<li>{esc(d)}</li>" for d in exp.get("details", []))}</ul></div></article>' for exp in data["experience"])
                sections += f'<section id="experience" class="section" data-section="experience"><h2 class="section-title">Experience</h2><div class="timeline">{items}</div></section>'

            # Asset Loading
            template = TEMPLATE_PATH.read_text(encoding="utf-8")
            css = CSS_PATH.read_text(encoding="utf-8")
            
            # Badge Logic
            avail = data.get("availability", "")
            if len(avail) > 22: avail = avail[:19] + "..."
            badge = f'<span class="availability-badge">{esc(avail)}</span>' if avail else ""

            # Replacements
            output = template.replace('<link rel="stylesheet" href="style.css">', f'<style>{css}</style>')
            output = output.replace('data-theme="{{THEME}}"', f'data-theme="{theme}"')
            output = output.replace('{{NAME}}', esc(data.get("name", "Portfolio")))
            output = output.replace('{{HEADLINE}}', esc(data.get("headline", "")))
            output = output.replace('{{NAV}}', nav)
            output = output.replace('{{SECTIONS}}', sections)
            output = output.replace('{{BADGE}}', badge)
            output = output.replace('{{HERO_VISUAL}}', '<div class="hero-art" aria-hidden="true"><span></span><span></span><span></span><i></i></div>')
            output = output.replace('{{YEAR}}', '2026')

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"html": output}).encode())

        except Exception:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": traceback.format_exc()}).encode())