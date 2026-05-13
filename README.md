# 🧠 AI RoundTable

AI RoundTable is a multi-model AI query and synthesis tool built with Streamlit. Ask a single **Master Prompt** to multiple top-tier AI models simultaneously — ChatGPT, Claude, Gemini, Groq, and Perplexity — then have a synthesizer model combine all perspectives into a single, comprehensive report.

## Features

- **Multi-Model Querying** — Get diverse perspectives from paid models (GPT-4o, Claude Opus, Perplexity Sonar) and free/open-source models (Llama 3.3 70B, Llama 3.1 8B via Groq).
- **Real-Time Streaming** — Fast models (Groq) appear within seconds; each model card updates independently as responses arrive.
- **Configurable Synthesizer** — Choose which model synthesizes the final report. Fallback order: Gemini 2.5 Pro → GPT-4o → Claude → error.
- **Disagreement Analysis** — After synthesis, a second Gemini 2.5 Pro call identifies where models disagreed or contradicted each other.
- **Query History** — View your last 10 queries in the History tab with full prompt and synthesis text.
- **Markdown Export** — Download any synthesis result as a timestamped `.md` file.
- **Model Selector** — Per-model checkboxes in the sidebar; disabled automatically when the API key is missing.
- **Cookie Toggle** — Opt in/out of browser cookie persistence for API keys. When off, keys stay in server-side session state only.
- **Per-User Rate Limiting** — 60-second cooldown between queries to prevent accidental API spend.
- **Email Gate & Lead Capture** — Users enter an email to access the tool; data is stored in SQLite.
- **Admin Dashboard** — Password-protected admin page (hidden from sidebar nav) to view and export user data.

## Models

All model identifiers are centralized in [`config.py`](config.py). No model string is hardcoded elsewhere.

| Provider | Model | Type |
|---|---|---|
| Google Gemini | `gemini-2.5-pro` | Paid |
| OpenAI | `gpt-4o` | Paid |
| Anthropic | `claude-opus-4-5` | Paid |
| Perplexity | `llama-3.1-sonar-large-128k-online` | Paid |
| Groq | `llama-3.3-70b-versatile` | Free |
| Groq | `llama-3.1-8b-instant` | Free |

## Project Structure

```
├── app.py                  # Main Streamlit application
├── config.py               # All model strings, timeouts, prompt templates
├── database.py             # SQLite persistence (users, rate limits, history)
├── pages/
│   └── admin.py            # Password-gated admin dashboard
├── .streamlit/
│   └── config.toml         # Theme, runner settings, hidden pages
├── BannerImage.png         # Header banner
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
└── .gitignore              # Excludes users.db, .env, __pycache__
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and set your admin password:

```env
ADMIN_PASSWORD=your_secure_password_here
```

> **Note:** API keys are entered by each user in the sidebar at runtime. You do not need to set them in `.env`.

### 3. Run the App

```bash
streamlit run app.py
```

## Usage

### For Users

1. **Email Gate** — Enter your email (and optional name) to unlock the tool.
2. **API Keys** — Add at least one API key in the sidebar. Keys can optionally be saved to browser cookies.
3. **Select Models** — Check/uncheck which models to query. Models without a key are disabled.
4. **Choose Synthesizer** — Pick which model produces the final report (defaults to Gemini if available).
5. **Run** — Enter your question and click **Run Queries & Synthesize**.
6. **Review** — See the synthesis, disagreement analysis, metrics bar, and raw responses. Download the result as Markdown.
7. **History** — Switch to the **📜 History** tab to revisit past queries.

### For Admins

1. Navigate to the **admin** page via the Streamlit pages menu (or direct URL).
2. Enter the `ADMIN_PASSWORD` set in your `.env` file.
3. View the user table and export to CSV.

## Database Note

This app uses SQLite (`users.db`) for local development. On stateless cloud platforms (Streamlit Cloud, Railway, Render), the database resets on every deploy. See the migration notes in [`database.py`](database.py) for instructions on switching to Supabase or PostgreSQL.
