# ──────────────────────────────────────────────────────────────────────
# config.py — AI RoundTable central configuration
# All model identifiers, timeouts, and prompt templates live here.
# No other file should hardcode model strings.
# ──────────────────────────────────────────────────────────────────────

# ── Model Configuration ──────────────────────────────────────────────
MODEL_CONFIG = {
    "openai":     "gpt-4o",
    "anthropic":  "claude-opus-4-5",
    "gemini":     "gemini-2.5-pro",
    "perplexity": "llama-3.1-sonar-large-128k-online",
    "groq_1":     "llama-3.3-70b-versatile",
    "groq_2":     "llama-3.1-8b-instant",
}

# Human-readable display names shown in the UI
MODEL_DISPLAY_NAMES = {
    "gemini":     "Gemini (2.5 Pro)",
    "groq_1":     f"Groq ({MODEL_CONFIG['groq_1']})",
    "groq_2":     f"Groq ({MODEL_CONFIG['groq_2']})",
    "openai":     "ChatGPT (GPT-4o)",
    "anthropic":  "Claude (Opus)",
    "perplexity": "Perplexity (Sonar Online)",
}

# Maps internal model key → the API-key name used in the keys dict.
# groq_1 and groq_2 share the same "groq" API key.
MODEL_KEY_MAP = {
    "gemini":     "gemini",
    "groq_1":     "groq",
    "groq_2":     "groq",
    "openai":     "openai",
    "anthropic":  "anthropic",
    "perplexity": "perplexity",
}

# ── Timeouts & Rate Limits ───────────────────────────────────────────
TIMEOUT_SECONDS = 45
RATE_LIMIT_SECONDS = 60

# ── Prompt Templates ─────────────────────────────────────────────────
SYNTHESIS_PROMPT_TEMPLATE = """\
Here are answers to a user's prompt from multiple AI models:

{model_responses}

Task: Synthesize the above information into a single, comprehensive, \
well-structured, and easy-to-read report. Eliminate redundancies, \
highlight the most important insights, and present a cohesive final \
answer to the original prompt. Act like an expert analyst combining \
research from multiple top-tier sources."""

DISAGREEMENT_PROMPT_TEMPLATE = """\
Here are answers to a user's prompt from multiple AI models:

{model_responses}

Task: Carefully compare the responses above. Identify every point \
where the models disagree, contradict each other, or provide \
materially different information. For each disagreement, quote the \
conflicting statements and briefly explain what the discrepancy is. \
If all models substantially agree, say so and highlight any minor \
nuance differences. Be concise and specific."""
