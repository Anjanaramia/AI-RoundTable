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

# ── API Quota Reference ───────────────────────────────────────────────
# Estimates based on a typical RoundTable query (~2K tokens in, ~500 out).
# free_runs_day  = approx daily runs before hitting free-tier hard limit.
# paid_cost_per_run = estimated USD at base/pay-as-you-go pricing.
# paid_tiers = plan labels the user can select in the sidebar.
API_QUOTA_INFO = {
    "gemini": {
        "label":             "Gemini 2.5 Pro",
        "free_runs_day":     12,    # 25 req/day ÷ 2 calls per run
        "free_note":         "25 req/day · 5 RPM · resets midnight PT",
        "paid_cost_per_run": 0.004,
        "paid_tiers": {
            "Free (25 req/day)":  {"runs_day": 12,   "cost_per_run": 0.000},
            "Pay-as-you-go":      {"runs_day": 9999, "cost_per_run": 0.004},
        },
    },
    "groq": {
        "label":             "Groq (Llama 3.3 70B + 3.1 8B)",
        "free_runs_day":     480,   # 14,400 req/day ÷ 30 (2 models × buffer)
        "free_note":         "14,400 req/day · 30 RPM · truly free",
        "paid_cost_per_run": 0.000,
        "paid_tiers": {
            "Free (unlimited for now)": {"runs_day": 480, "cost_per_run": 0.000},
        },
    },
    "openai": {
        "label":             "GPT-4o",
        "free_runs_day":     0,
        "free_note":         "No free API tier — requires billing",
        "paid_cost_per_run": 0.010,
        "paid_tiers": {
            "Tier 1 ($5 loaded)":   {"runs_day": 50,   "cost_per_run": 0.010},
            "Tier 2 ($50 loaded)":  {"runs_day": 500,  "cost_per_run": 0.010},
            "Tier 3 ($100 loaded)": {"runs_day": 2000, "cost_per_run": 0.010},
        },
    },
    "anthropic": {
        "label":             "Claude Opus",
        "free_runs_day":     0,
        "free_note":         "No free API tier — requires billing",
        "paid_cost_per_run": 0.020,
        "paid_tiers": {
            "Build ($5 credit)":  {"runs_day": 25,  "cost_per_run": 0.020},
            "Scale ($50 credit)": {"runs_day": 250, "cost_per_run": 0.020},
        },
    },
    "perplexity": {
        "label":             "Perplexity Sonar Online",
        "free_runs_day":     0,
        "free_note":         "No free API tier — requires billing",
        "paid_cost_per_run": 0.005,
        "paid_tiers": {
            "Starter ($5 credit)":   {"runs_day": 100,  "cost_per_run": 0.005},
            "Standard ($50 credit)": {"runs_day": 1000, "cost_per_run": 0.005},
        },
    },
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
