# AI Resume Portfolio Generator
An interactive web application that transforms plain-text resumes into professional, multi-themed portfolio websites instantly using Gemini 3.5 flash.
## How it Works
1. Input: Users can paste raw resume text or select the "Sample Portfolio" mode (which uses a pre-loaded resume.txt).
2. AI Processing: The backend sends the text to the Gemini 3.5 flash model with a strict JSON extraction prompt.
3. Structured Rendering: Python parses the AI's response, validates the data, and injects it into a dynamic HTML template.
4. Ephemeral Preview: The final portfolio is rendered inside an interactive, live-syncing iframe. The website updates its UI colors to match the specific portfolio theme selected by the user.
## File Structure & Roles
* api/generate.py: The engine of the project. This serverless function handles Gemini API | communication, safely extracts data to prevent crashes, and generates the final HTML string.
* index.html: The landing page and launcher. It manages the user interface, handles the "Paste" and "Sample" modes, and hosts the live portfolio viewer.
* launcher.css: Provides the dark-themed styling for the generator and handles the complex theme-syncing colors for the top "Live Portfolio" bar.
* template.html: The base structure for all generated portfolios. It contains the navigation logic, smooth scrolling, and the theme-switching bridge.
* style.css: Defines the four distinct visual systems (Vivid, Bold, Editorial, and Dark) used by the generated portfolios.
* resume.txt: The source file used for the "Sample Portfolio" generation.
 ## Key Features
* Gemini 3.5 flash Integration: High-speed, accurate extraction of professional data.
* Interactive Themes: Four unique visual layouts that change typography and color systems completely.
* Smart Sync: The preview bar automatically changes its appearance to match the theme selected inside the generated portfolio using cross-window communication.
* Fault-Tolerant: Includes a "Safe Extraction" layer to handle incomplete resumes or missing information without breaking the layout.
* Privacy-Focused: Operates on ephemeral sessions—portfolios exist only in browser memory and are cleared upon exit.