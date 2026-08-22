# AI Usage Log

This log records AI assistance used during development, as required by the bootcamp brief.

| AI tool | Prompt / request | What it generated | What we changed or corrected |
|---|---|---|---|
| ChatGPT | Build an AI-assisted resume portfolio generator from the supplied bootcamp brief, keeping the Gemini → JSON → HTML/CSS pipeline and adding selectable editorial themes. | Project architecture, Python pipeline, HTML/CSS/JS implementation, README structure, tests and documentation. | Reviewed the implementation, removed invented resume content from the generation path, added safe JSON normalization, API error handling, empty-section omission, theme inference, theme switcher, project filtering and scroll-synced navigation. |
| Gemini API | Runtime prompt in `main.py`: extract portfolio fields using only information present in `resume.txt`, return JSON only, and leave missing fields empty. | Structured resume/portfolio JSON. | The program validates/parses JSON safely and normalizes incomplete fields before rendering.

