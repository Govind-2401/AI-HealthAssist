# AI HealthAssist — Implementation Plan

## Top-Level Overview

Build a greenfield AI-powered healthcare education web application called **AI HealthAssist** using Python/Flask on the backend and vanilla HTML5/CSS3/JavaScript on the frontend. The app exposes two educational modules — an AI First-Aid Guide and a Medicine Information Assistant — each powered by IBM watsonx.ai (meta-llama/llama-3-1-8b-instruct by default, configurable via `.env`).

The UI is a single page: a landing section with two prominent module cards that expand inline when clicked. AI responses are rendered as flat styled section-cards with icons and headings. Medical safety guardrails are enforced at the prompt engineering level. No auth, database, chat history, or advanced features are in scope.

---

## Sub-Tasks

---

### Sub-Task 1 — Project Scaffold & Configuration

**Intent**
Establish the full project directory structure, dependency manifest, environment configuration, and git hygiene files so all subsequent sub-tasks have a consistent foundation to build on.

**Expected Outcomes**
- Project root contains `app.py`, `requirements.txt`, `.env.example`, `.gitignore`, `README.md`
- `requirements.txt` pins Flask, `ibm-watsonx-ai`, `python-dotenv`
- `.env.example` documents all required environment variables with placeholder values
- `.gitignore` excludes `.env`, `__pycache__`, `.venv`, `*.pyc`
- `README.md` contains project overview, setup instructions, and how to run

**Todo List**
1. Create the top-level directory layout:
   ```
   AI-HealthAssist/
   ├── app.py
   ├── requirements.txt
   ├── .env.example
   ├── .gitignore
   ├── README.md
   ├── static/
   │   ├── css/
   │   │   └── style.css
   │   └── js/
   │       └── main.js
   └── templates/
       └── index.html
   ```
2. Write `requirements.txt` with pinned versions for: `flask`, `ibm-watsonx-ai`, `python-dotenv`
3. Write `.env.example` with variables: `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, `WATSONX_URL`, `WATSONX_MODEL_ID` (default `meta-llama/llama-3-1-8b-instruct`)
4. Write `.gitignore`
5. Write `README.md` with: project description, prerequisites, setup steps (clone → create `.env` → install deps → run), module descriptions, disclaimer note

**Relevant Context**
- No existing codebase; all files are new
- IBM watsonx.ai SDK package name: `ibm-watsonx-ai`
- `.env` must never be committed — it holds the real API key and project ID

**Status**
[x] done

---

### Sub-Task 2 — watsonx.ai Service Layer

**Intent**
Create a reusable Python service module that wraps the IBM watsonx.ai SDK. This isolates all AI logic from Flask routing, making prompts easy to iterate on and the integration straightforward to test or swap.

**Expected Outcomes**
- `services/watsonx_service.py` exists and is importable
- Exposes two public functions: `get_first_aid_guidance(situation: str) -> dict` and `get_medicine_info(medicine_name: str) -> dict`
- Each function builds a safety-guardrailed prompt, calls watsonx.ai, parses the response into a structured Python dict with defined section keys
- Model ID, API key, project ID, and URL are all read from environment variables via `python-dotenv`
- Returns a well-defined error dict if the API call fails

**Todo List**
1. Create `services/` package with `__init__.py` and `watsonx_service.py`
2. In `watsonx_service.py`, load env vars at module init using `python-dotenv`
3. Initialise the `ibm-watsonx-ai` client (`APIClient` or `ModelInference`) using `WATSONX_API_KEY`, `WATSONX_URL`, `WATSONX_PROJECT_ID`
4. Write `get_first_aid_guidance(situation)`:
   - Input validation: reject empty or suspiciously short input
   - Build a system+user prompt that instructs the model to:
     - Provide general educational first-aid guidance only
     - Return exactly four labelled sections: `immediate_steps`, `things_to_avoid`, `warning_signs`, `when_to_seek_help`
     - Explicitly NOT diagnose, NOT prescribe, NOT give personalized treatment
     - Direct to emergency services for life-threatening situations
   - Call the model, parse the text response into a dict with those four keys
   - Return the dict
5. Write `get_medicine_info(medicine_name)`:
   - Input validation: reject empty input
   - Build a prompt instructing the model to return five labelled sections: `what_it_is`, `common_uses`, `general_precautions`, `important_warnings`, `when_to_consult`
   - Explicitly NOT prescribe, NOT recommend dosages, NOT make treatment decisions
   - Call the model, parse into a dict with those five keys
   - Return the dict
6. Implement a shared `_parse_sections(raw_text, keys)` helper that extracts labelled sections from the model's text output
7. Implement graceful error handling: catch SDK/network exceptions, return `{"error": "<message>"}` dict

**Relevant Context**
- IBM watsonx.ai Python SDK: `ibm-watsonx-ai`; relevant classes: `ModelInference` or `APIClient` with `generate_text`
- Model ID env var: `WATSONX_MODEL_ID` (default: `meta-llama/llama-3-1-8b-instruct`)
- Prompt design is the primary safety guardrail — section labels in the prompt must exactly match the parse keys

**Status**
[x] done

---

### Sub-Task 3 — Flask Application & REST API

**Intent**
Wire up the Flask app with two REST API endpoints that call the service layer and return structured JSON. This is the bridge between the frontend and the AI service.

**Expected Outcomes**
- `app.py` creates and configures the Flask app
- `GET /` serves `templates/index.html`
- `POST /api/first-aid` accepts `{"situation": "..."}`, returns structured JSON or `{"error": "..."}` with appropriate HTTP status codes
- `POST /api/medicine` accepts `{"medicine": "..."}`, returns structured JSON or `{"error": "..."}` with appropriate HTTP status codes
- Input validation at the route level (missing/empty fields return 400)
- CORS not required (frontend is served from the same Flask app)

**Todo List**
1. Write `app.py`:
   - Create Flask app, load `.env` via `python-dotenv`
   - Register `GET /` route to render `index.html`
   - Register `POST /api/first-aid`:
     - Parse JSON body, validate `situation` field (non-empty, max length guard)
     - Call `watsonx_service.get_first_aid_guidance(situation)`
     - Return JSON response with 200 on success, 400 for bad input, 500 for service error
   - Register `POST /api/medicine`:
     - Parse JSON body, validate `medicine` field (non-empty, max length guard)
     - Call `watsonx_service.get_medicine_info(medicine_name)`
     - Return JSON response with 200 on success, 400 for bad input, 500 for service error
   - Add a global error handler for unhandled exceptions returning `{"error": "Unexpected server error"}` with 500
2. Set `debug=False` for production safety; use `app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")`

**Relevant Context**
- Service layer lives in `services/watsonx_service.py` (Sub-Task 2)
- All frontend assets served as Flask static files — no separate dev server needed

**Status**
[ ] pending

---

### Sub-Task 4 — HTML Template (Single Page Structure)

**Intent**
Build the single `index.html` template that defines the full page structure: header with disclaimer banner, landing hero section with two module cards, the two inline module form+response sections, and a footer.

**Expected Outcomes**
- `templates/index.html` is a complete, semantic HTML5 document
- Contains: sticky header with app name + disclaimer badge, hero section with two module cards (First-Aid, Medicine Info), two module sections (hidden by default, expanded by JS), and a footer with the full medical disclaimer
- Each module section contains: a description, an input form, a loading indicator (hidden by default), a response container (hidden by default), and an error container (hidden by default)
- Response container has five/four named `div` elements matching the section keys from the API response, each with a placeholder icon and heading
- Links `static/css/style.css` and `static/js/main.js`
- No inline styles or inline JS

**Todo List**
1. Write the full HTML document structure with semantic tags (`header`, `main`, `section`, `footer`)
2. Header: app logo/name on left, "Educational Use Only" badge on right
3. Hero section: two cards side-by-side (responsive), each with icon, title, short description, and a "Get Started" button that triggers module expansion
4. First-Aid module section (`id="first-aid-section"`): textarea for describing the situation, submit button, loading spinner div, error div, response div with four section-card divs (`id` matching `immediate_steps`, `things_to_avoid`, `warning_signs`, `when_to_seek_help`)
5. Medicine module section (`id="medicine-section"`): text input for medicine name, submit button, loading spinner div, error div, response div with five section-card divs (`id` matching `what_it_is`, `common_uses`, `general_precautions`, `important_warnings`, `when_to_consult`)
6. Footer: full medical disclaimer text and copyright
7. Each section-card div has a consistent structure: icon placeholder, heading, content paragraph

**Relevant Context**
- Module sections are hidden on page load and revealed by `main.js` (Sub-Task 5)
- Section `id` attributes must exactly match the JSON keys returned by the API (Sub-Task 3)

**Status**
[ ] pending

---

### Sub-Task 5 — CSS Styling (Modern, Responsive)

**Intent**
Style the application with a clean, modern, professional look using plain CSS3. No framework dependencies — keeps the project lightweight and showcases front-end fundamentals.

**Expected Outcomes**
- `static/css/style.css` styles all elements defined in `index.html`
- Responsive layout: two-column card grid collapses to single column on mobile (≤768px)
- Colour palette: healthcare-appropriate (clean whites, soft blues, accent greens)
- Module cards have hover effect and clear visual affordance for being clickable
- Response section-cards are visually distinct flat cards with left-border accent colour per section type
- Loading spinner is a CSS-only animation
- Disclaimer banner/footer is visually prominent (amber/yellow accent)
- Smooth scroll and expand animation when a module section is revealed

**Todo List**
1. Define CSS custom properties (variables) for colour palette, spacing, border-radius, font stack
2. Style the sticky header
3. Style the hero section and module cards (grid, hover, icon size)
4. Style the module form sections (textarea/input, button states: default, hover, disabled/loading)
5. Style the loading spinner (CSS keyframe animation)
6. Style the response section-cards (flat card, icon+heading row, content area, accent border per section)
7. Style the error message container
8. Style the footer disclaimer
9. Add responsive breakpoints (`@media` at 768px and 480px)

**Relevant Context**
- Section-card accent colours suggestion: immediate_steps → blue, things_to_avoid → red, warning_signs → amber, when_to_seek_help → green; what_it_is → blue, common_uses → teal, general_precautions → amber, important_warnings → red, when_to_consult → green
- No external CSS frameworks or icon libraries — use Unicode/emoji icons or simple SVG inline in CSS

**Status**
[x] done

---

### Sub-Task 6 — JavaScript (UI Interactions & API Integration)

**Intent**
Write the client-side JavaScript that handles module expansion, form submission, API calls, response rendering, loading states, and error display. Vanilla JS only — no frameworks.

**Expected Outcomes**
- `static/js/main.js` handles all interactivity
- Clicking a module card smoothly scrolls to and reveals that module's section
- Form submission calls the correct Flask endpoint via `fetch()` with JSON body
- During the API call: submit button is disabled, loading spinner is shown, previous results/errors are cleared
- On success: loading state is cleared, response section-cards are populated with the returned content and made visible
- On error: loading state is cleared, error container is shown with a user-friendly message
- Input validation in JS (non-empty check) before the API call, with inline error feedback
- No page reloads

**Todo List**
1. On DOMContentLoaded, attach click handlers to both module "Get Started" buttons
2. Module reveal function: toggle visibility of the target section, smooth-scroll to it
3. Attach submit handler to the First-Aid form:
   - Validate textarea is non-empty
   - Call `POST /api/first-aid` via `fetch`
   - Handle loading state (show spinner, disable button)
   - On success: call `renderFirstAidResponse(data)` to populate section-card divs
   - On fetch/network error or API error field: call `showError(sectionId, message)`
4. Attach submit handler to the Medicine form (same pattern, calling `POST /api/medicine`)
5. Write `renderFirstAidResponse(data)`: iterate over the four section keys, set `textContent` of each section-card's content paragraph, make response container visible
6. Write `renderMedicineResponse(data)`: same for five section keys
7. Write `showError(containerId, message)`: display error div with message
8. Write `setLoading(formId, isLoading)`: toggle spinner visibility and button disabled state
9. Write `clearResults(sectionId)`: hide and empty the response and error containers before a new request

**Relevant Context**
- Section `div` IDs in HTML (Sub-Task 4) must match the JSON keys from the API (Sub-Task 3)
- `fetch` is used with `method: "POST"`, `headers: {"Content-Type": "application/json"}`, `body: JSON.stringify({...})`

**Status**
[ ] pending

---

## Implementation Order

Sub-Tasks must be completed in this order — each builds on the previous:

```
Sub-Task 1 (Scaffold) → Sub-Task 2 (AI Service) → Sub-Task 3 (Flask API)
→ Sub-Task 4 (HTML) → Sub-Task 5 (CSS) → Sub-Task 6 (JavaScript)
```

After Sub-Task 3 is complete, the backend is independently testable with `curl` or Postman.  
After Sub-Task 6 is complete, the full MVP is runnable end-to-end.

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `WATSONX_API_KEY` | Yes | IBM Cloud API key |
| `WATSONX_PROJECT_ID` | Yes | watsonx.ai project ID |
| `WATSONX_URL` | Yes | watsonx.ai regional endpoint URL |
| `WATSONX_MODEL_ID` | No | Model ID (default: `meta-llama/llama-3-1-8b-instruct`) |
| `FLASK_DEBUG` | No | Set to `true` for dev hot-reload |

---

## Out of Scope (MVP)

- User authentication
- Database or persistence
- Chat history
- Voice input/output
- Payment or subscription
- Admin dashboard
- Rate limiting (can be added post-MVP)
- Unit tests (can be added post-MVP)
