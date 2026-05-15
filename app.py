# ──────────────────────────────────────────────────────────────────────
# app.py — AI RoundTable  ·  Multi-Model AI Query & Synthesis Tool
# ──────────────────────────────────────────────────────────────────────

from __future__ import annotations

import streamlit as st
import asyncio
import time
from datetime import datetime

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
import google.generativeai as genai
from streamlit_cookies_manager import CookieManager

import database as db
from config import (
    MODEL_CONFIG,
    MODEL_DISPLAY_NAMES,
    MODEL_KEY_MAP,
    API_QUOTA_INFO,
    TIMEOUT_SECONDS,
    RATE_LIMIT_SECONDS,
    SYNTHESIS_PROMPT_TEMPLATE,
    DISAGREEMENT_PROMPT_TEMPLATE,
)

# ── Initialise DB ────────────────────────────────────────────────────
db.init_db()

# ── Page Config ──────────────────────────────────────────────────────
st.set_page_config(page_title="AI RoundTable", page_icon="🧠", layout="wide")

# ── Session State Defaults ───────────────────────────────────────────
_defaults = {
    "responses": {},
    "synthesis": "",
    "disagreements": "",
    "user_email": None,
    "cookies_changed": False,
    "query_prompt": "",
    "run_complete": False,
    "models_queried_count": 0,
    "run_time_seconds": 0.0,
    "is_mobile": False,
}
for key, val in _defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── Cookie Manager ───────────────────────────────────────────────────
# ⚠️  COOKIE SECURITY WARNING
# ─────────────────────────────────────────────────────────────────────
# Browser cookies set by streamlit-cookies-manager are:
#   • Readable by ANY JavaScript running on the page (no HttpOnly flag).
#   • Transmitted with every HTTP request to the Streamlit server.
# This means API keys stored in cookies could be exposed via XSS or
# network interception on non-HTTPS connections.  The "Remember API
# keys" toggle below lets users opt out of cookie persistence entirely,
# keeping keys in server-side session_state only.
# ─────────────────────────────────────────────────────────────────────
cookies = CookieManager()
if not cookies.ready():
    st.stop()


# ═════════════════════════════════════════════════════════════════════
#  ASYNC API HELPERS
# ═════════════════════════════════════════════════════════════════════

async def query_openai_compatible(
    prompt: str,
    api_key: str,
    base_url: str,
    model: str,
    timeout: float = TIMEOUT_SECONDS,
) -> str:
    """Shared async helper for any OpenAI-compatible chat API."""
    try:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            ),
            timeout=timeout,
        )
        return response.choices[0].message.content
    except asyncio.TimeoutError:
        return f"Error: Request timed out after {int(timeout)} seconds."
    except Exception as e:
        return f"Error: {e}"


async def query_openai(prompt: str, api_key: str) -> str:
    return await query_openai_compatible(prompt, api_key, "https://api.openai.com/v1", MODEL_CONFIG["openai"])


async def query_perplexity(prompt: str, api_key: str) -> str:
    return await query_openai_compatible(prompt, api_key, "https://api.perplexity.ai", MODEL_CONFIG["perplexity"])


async def query_groq(prompt: str, api_key: str, model_key: str) -> str:
    return await query_openai_compatible(prompt, api_key, "https://api.groq.com/openai/v1", MODEL_CONFIG[model_key])


async def query_anthropic(prompt: str, api_key: str) -> str:
    try:
        client = AsyncAnthropic(api_key=api_key, timeout=TIMEOUT_SECONDS)
        response = await asyncio.wait_for(
            client.messages.create(
                model=MODEL_CONFIG["anthropic"],
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}],
            ),
            timeout=TIMEOUT_SECONDS,
        )
        return response.content[0].text
    except asyncio.TimeoutError:
        return f"Error: Request timed out after {TIMEOUT_SECONDS} seconds."
    except Exception as e:
        return f"Error: {e}"


async def query_gemini(prompt: str, api_key: str) -> str:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(MODEL_CONFIG["gemini"])
        response = await asyncio.wait_for(
            model.generate_content_async(prompt),
            timeout=TIMEOUT_SECONDS,
        )
        return response.text
    except asyncio.TimeoutError:
        return f"Error: Request timed out after {TIMEOUT_SECONDS} seconds."
    except Exception as e:
        return f"Error: {e}"


# ── Dispatch Table ───────────────────────────────────────────────────
# Maps a model key to the coroutine that queries it.

def _build_task(model_key: str, prompt: str, api_key: str):
    """Return an (awaitable, display_name) tuple for the given model key."""
    if model_key == "gemini":
        coro = query_gemini(prompt, api_key)
    elif model_key == "openai":
        coro = query_openai(prompt, api_key)
    elif model_key == "anthropic":
        coro = query_anthropic(prompt, api_key)
    elif model_key == "perplexity":
        coro = query_perplexity(prompt, api_key)
    elif model_key in ("groq_1", "groq_2"):
        coro = query_groq(prompt, api_key, model_key)
    else:
        raise ValueError(f"Unknown model key: {model_key}")
    return coro, MODEL_DISPLAY_NAMES[model_key]


# ── Fetch All Responses (as_completed + real-time cards) ─────────────

async def fetch_all_responses(prompt: str, keys: dict, selected_models: list[str], placeholders: dict):
    """
    Query every selected model concurrently.  Uses asyncio.as_completed()
    so that fast models (Groq) update their placeholder card immediately
    without waiting for slower models (Claude, Perplexity).
    """
    results: dict[str, str] = {}
    if not selected_models:
        return results

    # Build {future: display_name} mapping
    future_to_name: dict[asyncio.Task, str] = {}
    for model_key in selected_models:
        api_key = keys.get(MODEL_KEY_MAP[model_key])
        if not api_key:
            continue
        coro, display_name = _build_task(model_key, prompt, api_key)
        task = asyncio.ensure_future(coro)
        future_to_name[task] = display_name

    for completed in asyncio.as_completed(future_to_name.keys()):
        result = await completed
        # Identify which model finished
        for task, name in future_to_name.items():
            if task.done() and name not in results:
                try:
                    res = task.result()
                    results[name] = res
                    # Update the real-time placeholder card
                    if name in placeholders:
                        with placeholders[name].container():
                            st.success(f"✅ {name}")
                            st.markdown(res[:300] + ("…" if len(res) > 300 else ""))
                    break
                except Exception as e:
                    results[name] = f"Error: {e}"
                    if name in placeholders:
                        with placeholders[name].container():
                            st.error(f"❌ {name}: {e}")
                    break

    return results


# ── Synthesis / Disagreement Helpers ─────────────────────────────────

def _build_model_responses_text(responses: dict) -> str:
    """Format model responses into the text block used by prompt templates."""
    parts = []
    for model_name, answer in responses.items():
        if "Error:" not in answer:
            parts.append(f"### {model_name}\n{answer}")
    return "\n\n".join(parts)


async def run_synthesis(responses: dict, api_key: str, model_key: str) -> str:
    """
    Synthesise all valid model responses using the selected synthesiser model.
    Routes to the correct API client based on *model_key*.
    """
    model_text = _build_model_responses_text(responses)
    if not model_text:
        return "No valid responses were generated to synthesize. Check your API keys or quota limits."

    synth_prompt = SYNTHESIS_PROMPT_TEMPLATE.format(model_responses=model_text)

    if model_key == "gemini":
        return await query_gemini(synth_prompt, api_key)
    elif model_key == "openai":
        return await query_openai(synth_prompt, api_key)
    elif model_key == "anthropic":
        return await query_anthropic(synth_prompt, api_key)
    elif model_key == "perplexity":
        return await query_perplexity(synth_prompt, api_key)
    elif model_key in ("groq_1", "groq_2"):
        return await query_groq(synth_prompt, api_key, model_key)
    else:
        return f"Error: Unknown synthesiser model key '{model_key}'."


async def run_disagreement_analysis(responses: dict, gemini_key: str) -> str:
    """
    Identify disagreements across model responses.
    Uses gemini-2.5-pro (via config) for this analysis.
    Returns a clean user-facing message on quota / rate-limit errors.
    """
    model_text = _build_model_responses_text(responses)
    if not model_text:
        return ""
    if not gemini_key:
        return ""
    disagree_prompt = DISAGREEMENT_PROMPT_TEMPLATE.format(model_responses=model_text)
    result = await query_gemini(disagree_prompt, gemini_key)
    # Detect quota / rate-limit errors and return a clean message
    if result.startswith("Error:") and ("429" in result or "quota" in result.lower() or "rate" in result.lower()):
        return "_QUOTA_EXCEEDED_"
    return result


# ── Cookie Helpers ───────────────────────────────────────────────────

def update_cookies(key_name: str, new_val: str, remember: bool):
    """Write to cookies only when the 'Remember' toggle is on."""
    if remember:
        if cookies.get(key_name) != new_val:
            cookies[key_name] = new_val
            st.session_state.cookies_changed = True
    else:
        # Clear the cookie if the user toggled remember off
        if cookies.get(key_name):
            cookies[key_name] = ""
            st.session_state.cookies_changed = True


def _read_key(cookie_name: str, remember: bool) -> str:
    """Read key from cookie (if remember) or return empty string."""
    if remember:
        return cookies.get(cookie_name, "")
    return st.session_state.get(f"_sess_{cookie_name}", "")


# ═════════════════════════════════════════════════════════════════════
#  UI VIEWS
# ═════════════════════════════════════════════════════════════════════

# ── Email Gate ───────────────────────────────────────────────────────

def render_email_gate():
    try:
        st.image("BannerImage.png", use_container_width=True)
    except Exception:
        pass

    st.title("Welcome to AI RoundTable 🧠")
    st.markdown("Please enter your details to access the multi-AI synthesizer tool.")

    with st.form("gate_form"):
        email = st.text_input("Email Address *")
        name = st.text_input("First Name (Optional)")
        submitted = st.form_submit_button("Access Tool")

        if submitted:
            if not email:
                st.error("Please provide an email address.")
            elif "@" not in email:
                st.error("Please provide a valid email address.")
            else:
                with st.spinner("Setting up your session..."):
                    db.add_user(email.strip(), name.strip())
                    st.session_state.user_email = email.strip()
                st.rerun()


# ── Main Application ─────────────────────────────────────────────────

def render_main_app():
    # ── Banner ────────────────────────────────────────────────────────
    try:
        st.image("BannerImage.png", use_container_width=True)
    except Exception:
        pass

    st.title("🧠 AI RoundTable")
    st.markdown(
        "Ask a master prompt to top-tier AI models at once, and have them "
        "synthesize the final result — just like NotebookLM!"
    )

    # ── Sidebar ───────────────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Settings")

        # Cookie toggle
        remember_keys = st.toggle("Remember API keys (cookies)", value=True)

        st.divider()

        # ── API Keys ─────────────────────────────────────────────────
        st.header("🔑 API Keys")

        # Helper: render one API key block with inline quota info
        def _api_key_block(cookie_name, label, provider_key, get_key_url):
            """Render key input + plan selector + quota indicator."""
            info = API_QUOTA_INFO[provider_key]
            tier_names = list(info["paid_tiers"].keys())

            # Plan selector (only show if >1 tier option)
            sess_plan_key = f"_plan_{provider_key}"
            if len(tier_names) > 1:
                selected_plan = st.selectbox(
                    f"{label} — plan",
                    tier_names,
                    key=sess_plan_key,
                    label_visibility="collapsed",
                )
            else:
                selected_plan = tier_names[0]
                st.session_state[sess_plan_key] = selected_plan

            tier = info["paid_tiers"][selected_plan]
            runs = tier["runs_day"]
            cost = tier["cost_per_run"]

            # Quota badge
            if runs >= 9999:
                quota_str = "♾️ unlimited runs/day"
            elif runs == 0:
                quota_str = "⛔ no free tier"
            else:
                quota_str = f"~{runs} runs/day"

            if cost == 0:
                cost_str = "free"
            else:
                cost_str = f"~${cost:.3f}/run"

            st.caption(f"{quota_str}  ·  {cost_str}  ·  {info['free_note'] if selected_plan == tier_names[0] else selected_plan}")

            # Key input
            val = st.text_input(label, type="password", value=_read_key(cookie_name, remember_keys))
            update_cookies(cookie_name, val, remember_keys)
            if not remember_keys:
                st.session_state[f"_sess_{cookie_name}"] = val
            st.caption(f"[Get key]({get_key_url})")
            return val

        st.subheader("Required for Synthesis")
        gemini_key = _api_key_block("gemini_key", "Google Gemini", "gemini", "https://aistudio.google.com/app/apikey")

        st.subheader("Free Alternatives")
        groq_key = _api_key_block("groq_key", "Groq", "groq", "https://console.groq.com/keys")

        st.subheader("Paid Options")
        openai_key    = _api_key_block("openai_key",    "OpenAI (GPT-4o)",  "openai",    "https://platform.openai.com/api-keys")
        anthropic_key = _api_key_block("anthropic_key", "Anthropic (Claude)", "anthropic", "https://console.anthropic.com/settings/keys")
        perplexity_key = _api_key_block("perplexity_key", "Perplexity",      "perplexity", "https://www.perplexity.ai/settings/api")

        st.divider()

        # ── Build keys dict ──────────────────────────────────────────
        keys = {
            "gemini":     gemini_key.strip() if gemini_key else None,
            "groq":       groq_key.strip() if groq_key else None,
            "openai":     openai_key.strip() if openai_key else None,
            "anthropic":  anthropic_key.strip() if anthropic_key else None,
            "perplexity": perplexity_key.strip() if perplexity_key else None,
        }

        # ── Select Models ────────────────────────────────────────────
        st.header("🎯 Select Models")
        selected_models: list[str] = []

        for model_key, display_name in MODEL_DISPLAY_NAMES.items():
            required_key = MODEL_KEY_MAP[model_key]
            has_key = bool(keys.get(required_key))
            checked = st.checkbox(
                display_name,
                value=has_key,
                disabled=not has_key,
                key=f"cb_{model_key}",
            )
            if not has_key:
                st.caption("🔒 Add API key to enable")
            if checked and has_key:
                selected_models.append(model_key)

        st.divider()

        # ── Synthesizer Model ────────────────────────────────────────
        st.header("🔬 Synthesizer Model")

        synth_options: list[tuple[str, str]] = []  # (model_key, display_name)
        # Preferred order: Gemini → GPT-4o → Claude
        if keys.get("gemini"):
            synth_options.append(("gemini", MODEL_DISPLAY_NAMES["gemini"]))
        if keys.get("openai"):
            synth_options.append(("openai", MODEL_DISPLAY_NAMES["openai"]))
        if keys.get("anthropic"):
            synth_options.append(("anthropic", MODEL_DISPLAY_NAMES["anthropic"]))
        if keys.get("perplexity"):
            synth_options.append(("perplexity", MODEL_DISPLAY_NAMES["perplexity"]))
        if keys.get("groq"):
            synth_options.append(("groq_1", MODEL_DISPLAY_NAMES["groq_1"]))

        if synth_options:
            synth_display = [name for _, name in synth_options]
            synth_selection = st.selectbox("Synthesizer Model", synth_display)
            synth_model_key = next(k for k, n in synth_options if n == synth_selection)
            synth_api_key = keys[MODEL_KEY_MAP[synth_model_key]]
        else:
            st.warning("Enter at least one API key to enable synthesis.")
            synth_model_key = None
            synth_api_key = None

    # ── Tabs ──────────────────────────────────────────────────────────
    tab_roundtable, tab_history = st.tabs(["🧠 RoundTable", "📜 History"])

    # ══════════════════════════════════════════════════════════════════
    #  TAB 1 — RoundTable
    # ══════════════════════════════════════════════════════════════════
    with tab_roundtable:
        st.divider()
        st.subheader("📝 Master Prompt")
        prompt = st.text_area(
            "Enter your question or task here:",
            height=150,
            placeholder="e.g., What is Clipboard Health? How is RevOps done there?",
        )

        run_button = st.button("Run Queries & Synthesize", type="primary")

        # ── Empty State ──────────────────────────────────────────────
        if not st.session_state.run_complete and not run_button:
            st.info(
                "👋 **Welcome to AI RoundTable!**\n\n"
                "1. Enter your API keys in the sidebar (at least one).\n"
                "2. Select which models to query.\n"
                "3. Type your question above and click **Run Queries & Synthesize**.\n\n"
                "The tool will query multiple AI models simultaneously, then "
                "synthesize their answers into a single expert report."
            )

        # ── Run Button Handler ───────────────────────────────────────
        if run_button:
            if not any(keys.values()):
                st.error(
                    "⚠️ **Your saved API keys have expired or are missing.** "
                    "Please re-enter at least one API key in the sidebar."
                )
            elif not prompt.strip():
                st.warning("Please enter a prompt.")
            elif not selected_models:
                st.warning("Please select at least one model in the sidebar.")
            elif synth_model_key is None:
                st.error("No synthesizer model available. Please add an API key.")
            else:
                # ── Rate Limiting ────────────────────────────────────
                user_email = st.session_state.user_email
                last_time_str = db.get_last_query_time(user_email)
                if last_time_str:
                    last_time = datetime.strptime(last_time_str, "%Y-%m-%d %H:%M:%S")
                    elapsed = (datetime.now() - last_time).total_seconds()
                    if elapsed < RATE_LIMIT_SECONDS:
                        remaining = int(RATE_LIMIT_SECONDS - elapsed)
                        st.warning(f"Please wait {remaining} seconds before your next query.")
                        st.stop()

                wall_start = time.time()

                # ── Create placeholder cards for selected models ─────
                st.subheader("⏳ Model Responses (streaming in...)")
                placeholders: dict[str, st.delta_generator.DeltaGenerator] = {}
                # Determine column layout
                use_single_col = st.session_state.get("is_mobile", False)
                if use_single_col:
                    for model_key in selected_models:
                        name = MODEL_DISPLAY_NAMES[model_key]
                        placeholders[name] = st.empty()
                        with placeholders[name].container():
                            st.info(f"⏳ Waiting for {name}...")
                else:
                    for i in range(0, len(selected_models), 2):
                        cols = st.columns(2)
                        for j, col in enumerate(cols):
                            idx = i + j
                            if idx < len(selected_models):
                                mk = selected_models[idx]
                                name = MODEL_DISPLAY_NAMES[mk]
                                with col:
                                    placeholders[name] = st.empty()
                                    with placeholders[name].container():
                                        st.info(f"⏳ Waiting for {name}...")

                # ── Fetch responses ──────────────────────────────────
                with st.status("Fetching responses from all models...", expanded=True) as status:
                    responses = asyncio.run(
                        fetch_all_responses(prompt, keys, selected_models, placeholders)
                    )
                    st.session_state.responses = responses

                    status.update(
                        label=f"Responses fetched! Synthesizing with {MODEL_DISPLAY_NAMES.get(synth_model_key, synth_model_key)}...",
                        state="running",
                    )

                    # ── Synthesis ────────────────────────────────────
                    try:
                        synthesis = asyncio.run(
                            run_synthesis(responses, synth_api_key, synth_model_key)
                        )
                    except Exception as e:
                        synthesis = f"Synthesis error ({synth_model_key}): {e}"

                    st.session_state.synthesis = synthesis

                    # ── Disagreement Analysis (separate Gemini call) ──
                    # Only run if Gemini key is present AND synthesis didn't
                    # already fail with a 429 (would just fail again).
                    disagree_key = keys.get("gemini")
                    synthesis_hit_quota = (
                        synthesis.startswith("Error:") and
                        ("429" in synthesis or "quota" in synthesis.lower())
                    )
                    if disagree_key and not synthesis_hit_quota:
                        try:
                            disagreements = asyncio.run(
                                run_disagreement_analysis(responses, disagree_key)
                            )
                        except Exception as e:
                            disagreements = "_QUOTA_EXCEEDED_"
                    else:
                        disagreements = ""
                    st.session_state.disagreements = disagreements

                    status.update(label="Complete!", state="complete", expanded=False)

                wall_end = time.time()
                st.session_state.run_time_seconds = round(wall_end - wall_start, 1)
                st.session_state.models_queried_count = len(responses)
                st.session_state.run_complete = True
                st.session_state.query_prompt = prompt

                # ── Update rate limit & save history ─────────────────
                db.update_last_query_time(user_email)
                db.save_query_history(user_email, prompt, synthesis)

                st.rerun()

        # ── Display Results ──────────────────────────────────────────
        if st.session_state.run_complete and st.session_state.synthesis:
            # Metrics bar
            m1, m2, m3 = st.columns(3)
            m1.metric("Models Queried", st.session_state.models_queried_count)
            m2.metric("Synthesis Words", len(st.session_state.synthesis.split()))
            m3.metric("Time (seconds)", st.session_state.run_time_seconds)

            st.divider()

            st.header("✨ Synthesized Result")
            st.markdown(st.session_state.synthesis)

            # Download button
            now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            md_content = (
                f"# AI RoundTable Result\n\n"
                f"**Prompt:** {st.session_state.query_prompt}\n\n"
                f"**Timestamp:** {now_str}\n\n"
                f"---\n\n"
                f"{st.session_state.synthesis}"
            )
            st.download_button(
                label="📥 Download as Markdown",
                data=md_content,
                file_name=f"roundtable_result_{now_str}.md",
                mime="text/markdown",
            )

            # Disagreement analysis
            if st.session_state.disagreements:
                st.divider()
                if st.session_state.disagreements == "_QUOTA_EXCEEDED_":
                    st.warning(
                        "⚡ **Where Models Disagreed** — analysis skipped.\n\n"
                        "Gemini 2.5 Pro free-tier quota was exhausted for today. "
                        "[Upgrade your plan](https://ai.dev/rate-limit) or try again tomorrow."
                    )
                elif st.session_state.disagreements.startswith("Error:"):
                    st.warning(f"⚡ **Where Models Disagreed** — {st.session_state.disagreements}")
                else:
                    st.info(f"⚡ **Where Models Disagreed**\n\n{st.session_state.disagreements}")

            st.divider()
            st.subheader("🔍 Raw Source Responses")

            models = list(st.session_state.responses.keys())
            use_single_col = st.session_state.get("is_mobile", False)

            if use_single_col:
                for model_name in models:
                    with st.expander(model_name):
                        st.markdown(st.session_state.responses[model_name])
            else:
                for i in range(0, len(models), 2):
                    col1, col2 = st.columns(2)
                    with col1:
                        with st.expander(models[i]):
                            st.markdown(st.session_state.responses[models[i]])
                    if i + 1 < len(models):
                        with col2:
                            with st.expander(models[i + 1]):
                                st.markdown(st.session_state.responses[models[i + 1]])

    # ══════════════════════════════════════════════════════════════════
    #  TAB 2 — History
    # ══════════════════════════════════════════════════════════════════
    with tab_history:
        st.subheader("📜 Recent Query History")
        history = db.get_query_history(st.session_state.user_email, limit=10)
        if not history:
            st.info("No queries yet. Run your first RoundTable query to see history here.")
        else:
            for entry in history:
                label = f"🕐 {entry['created_at']}  —  {entry['prompt'][:80]}{'…' if len(entry['prompt']) > 80 else ''}"
                with st.expander(label):
                    st.markdown(f"**Prompt:** {entry['prompt']}")
                    st.divider()
                    st.markdown(entry["synthesis"])


# ═════════════════════════════════════════════════════════════════════
#  ROUTING
# ═════════════════════════════════════════════════════════════════════

if st.session_state.user_email is None:
    render_email_gate()
else:
    render_main_app()

# ── Persist Cookies ──────────────────────────────────────────────────
if st.session_state.cookies_changed:
    cookies.save()
    st.session_state.cookies_changed = False
