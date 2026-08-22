# AI Resume Portfolio Generator

An interactive web application that transforms plain-text resumes into professional, multi-themed portfolio websites using Gemini AI.

## 🚀 Features

* Convert raw resume text into a structured portfolio
* Gemini-powered resume information extraction
* Four interactive portfolio themes:

  * Vivid
  * Bold
  * Editorial
  * Dark
* Live portfolio preview using an interactive iframe
* Automatic theme synchronization between the portfolio and preview interface
* Sample Portfolio mode using a pre-loaded `resume.txt`
* Fault-tolerant JSON extraction for incomplete or inconsistent AI responses
* Ephemeral sessions with no permanent portfolio storage

---

## ⚙️ How It Works

1. **Resume Input**
   Users either paste their resume text or select the pre-loaded Sample Portfolio.

2. **AI Processing**
   The resume is sent to the Gemini API with a structured JSON extraction prompt.

3. **Data Validation**
   The Python backend safely extracts and validates the AI-generated response.

4. **Portfolio Generation**
   The structured data is injected into the HTML portfolio template.

5. **Live Preview**
   The generated portfolio is rendered inside an iframe with real-time theme synchronization.

---

## 🏗️ Architecture

```text
                    ┌──────────────────────┐
                    │       User           │
                    │ Resume / Sample      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Frontend Interface │
                    │   index.html + CSS   │
                    └──────────┬───────────┘
                               │
                         POST /api/generate
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Python Backend     │
                    │   api/generate.py    │
                    │                      │
                    │ • Gemini API call    │
                    │ • JSON extraction    │
                    │ • Validation         │
                    │ • HTML generation    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │      Gemini AI       │
                    │  Resume → JSON Data  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Portfolio Template  │
                    │ template.html        │
                    │ style.css            │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Live Preview       │
                    │      iframe          │
                    └──────────────────────┘
```

---

## 🛠️ Tech Stack

* **Frontend:** HTML, CSS, JavaScript
* **Backend:** Python
* **AI:** Gemini API
* **Deployment:** Vercel

---

## 📁 Project Structure

```text
Resume_to_portfolio/
│
├── api/
│   └── generate.py       # Serverless backend and Gemini integration
│
├── index.html            # Main application interface
├── launcher.css          # Generator UI styling
├── template.html         # Base portfolio template
├── style.css             # Portfolio theme styling
├── resume.txt            # Sample resume
├── requirements.txt      # Python dependencies
├── vercel.json            # Vercel configuration
└── .gitignore
```

### File Roles

* **`api/generate.py`**
  Handles Gemini API communication, safe JSON extraction, validation, and dynamic HTML generation.

* **`index.html`**
  Provides the main interface, resume input, Sample Portfolio mode, and live preview.

* **`launcher.css`**
  Styles the generator interface and preview controls.

* **`template.html`**
  Defines the base structure and navigation of generated portfolios.

* **`style.css`**
  Contains the four visual theme systems.

* **`resume.txt`**
  Provides the sample resume used by Sample Portfolio mode.

---

## 💻 Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/Aniket-Singh25cp/Resume_To_Portfolio_Generator
cd Resume_to_portfolio
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Gemini API Key

Create a `.env` file in the project root:

```text
GEMINI_API_KEY=your_gemini_api_key
```

Do **not** commit the `.env` file to GitHub.

The `.gitignore` file already excludes `.env`.

### 4. Run the application

```bash
python main.py
```

Open the local URL shown by the application in your browser.

---

## 🌐 Deployment

The application is designed to work with Vercel serverless functions.

The Python backend is exposed through:

```text
/api/generate
```

For deployment, configure the Gemini API key in the hosting platform's environment variables instead of committing it to the repository.