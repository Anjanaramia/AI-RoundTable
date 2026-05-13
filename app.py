import streamlit as st
import asyncio
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
import google.generativeai as genai
import os
from streamlit_cookies_manager import CookieManager
import database as db

# Initialize DB
db.init_db()

st.set_page_config(page_title="AI RoundTable", page_icon="🧠", layout="wide")

# Initialize Session State
if "responses" not in st.session_state:
    st.session_state.responses = {}
if "synthesis" not in st.session_state:
    st.session_state.synthesis = ""
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "admin_mode" not in st.session_state:
    st.session_state.admin_mode = False

# Initialize Cookies Manager
cookies = CookieManager()
if not cookies.ready():
    st.stop()

# --- API Clients Setup ---
async def query_openai(prompt, api_key):
    try:
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

async def query_anthropic(prompt, api_key):
    try:
        client = AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return f"Error: {str(e)}"

async def query_gemini(prompt, api_key):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

async def query_perplexity(prompt, api_key):
    try:
        client = AsyncOpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
        response = await client.chat.completions.create(
            model="llama-3.1-sonar-large-128k-online",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

async def query_groq(prompt, api_key, model_name):
    try:
        client = AsyncOpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        response = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# --- Main App Logic ---
async def fetch_all_responses(prompt, keys):
    tasks = []
    model_names = []
    
    if keys.get('gemini'):
        tasks.append(query_gemini(prompt, keys['gemini']))
        model_names.append("Gemini (1.5 Pro)")
    if keys.get('groq'):
        tasks.append(query_groq(prompt, keys['groq'], "llama3-70b-8192"))
        model_names.append("Groq (Llama-3 70B)")
        tasks.append(query_groq(prompt, keys['groq'], "mixtral-8x7b-32768"))
        model_names.append("Groq (Mixtral 8x7B)")
    if keys.get('openai'):
        tasks.append(query_openai(prompt, keys['openai']))
        model_names.append("ChatGPT (GPT-4o)")
    if keys.get('anthropic'):
        tasks.append(query_anthropic(prompt, keys['anthropic']))
        model_names.append("Claude (Opus)")
    if keys.get('perplexity'):
        tasks.append(query_perplexity(prompt, keys['perplexity']))
        model_names.append("Perplexity (Sonar Online)")
        
    if not tasks:
        return {}
        
    results = await asyncio.gather(*tasks)
    return dict(zip(model_names, results))

async def synthesize_with_gemini(responses, api_key):
    if not api_key:
        return "Cannot synthesize: Gemini API Key is missing. Please provide it in the sidebar to enable synthesis."
    if not responses:
        return "No API keys were provided, so no responses were generated."
    
    context = "Here are answers to a user's prompt from multiple AI models:\n\n"
    valid_responses = 0
    for model_name, answer in responses.items():
        if "API Key not provided" not in answer and "Error:" not in answer:
            context += f"### {model_name}\n{answer}\n\n"
            valid_responses += 1
            
    if valid_responses == 0:
        return "No valid responses were generated to synthesize. Check your API keys or quota limits."
    
    synthesis_prompt = f"{context}\n\nTask: Synthesize the above information into a single, comprehensive, well-structured, and easy-to-read report. Eliminate redundancies, highlight the most important insights, and present a cohesive final answer to the original prompt. Act like an expert analyst combining research."
    
    return await query_gemini(synthesis_prompt, api_key)


# --- Helper: Save Cookies ---
def update_cookies(key_name, new_val):
    if cookies.get(key_name) != new_val:
        cookies[key_name] = new_val
        cookies.save()


# --- UI: Admin View ---
def render_admin_dashboard():
    st.title("🛡️ Admin Dashboard")
    st.markdown("Welcome to the Admin view. Here you can see who has accessed the tool.")
    
    users_df = db.get_all_users()
    if users_df.empty:
        st.info("No users have registered yet.")
    else:
        st.dataframe(users_df, use_container_width=True)
        csv = users_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Data as CSV",
            data=csv,
            file_name='users_export.csv',
            mime='text/csv',
        )

# --- UI: Email Gate View ---
def render_email_gate():
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
                db.add_user(email.strip(), name.strip())
                st.session_state.user_email = email.strip()
                st.rerun()

# --- UI: Main App View ---
def render_main_app():
    st.title("🧠 AI RoundTable")
    st.markdown("Ask a master prompt to top-tier AI models at once, and have Gemini synthesize the final result—just like NotebookLM!")
    st.info("💡 **Pro Tip:** To save free tokens and avoid rate limits, bundle multiple questions into a single master prompt rather than asking them one by one!")
    
    with st.sidebar:
        st.header("🔑 API Keys")
        st.markdown("Keys are saved securely in your browser cookies.")
        
        st.subheader("Required for Synthesis")
        gemini_key = st.text_input("Google Gemini API Key", type="password", value=cookies.get("gemini_key", ""))
        update_cookies("gemini_key", gemini_key)
        st.caption("[Get Gemini API Key](https://aistudio.google.com/app/apikey)")
        
        st.subheader("Free Alternatives")
        groq_key = st.text_input("Groq API Key", type="password", value=cookies.get("groq_key", ""))
        update_cookies("groq_key", groq_key)
        st.caption("[Get Groq API Key](https://console.groq.com/keys)")
        
        st.subheader("Paid Options")
        openai_key = st.text_input("OpenAI API Key (ChatGPT)", type="password", value=cookies.get("openai_key", ""))
        update_cookies("openai_key", openai_key)
        st.caption("[Get OpenAI API Key](https://platform.openai.com/api-keys)")
        
        anthropic_key = st.text_input("Anthropic API Key (Claude)", type="password", value=cookies.get("anthropic_key", ""))
        update_cookies("anthropic_key", anthropic_key)
        st.caption("[Get Anthropic API Key](https://console.anthropic.com/settings/keys)")
        
        perplexity_key = st.text_input("Perplexity API Key", type="password", value=cookies.get("perplexity_key", ""))
        update_cookies("perplexity_key", perplexity_key)
        st.caption("[Get Perplexity API Key](https://www.perplexity.ai/settings/api)")
    
    st.markdown("---")
    st.subheader("📝 Master Prompt")
    prompt = st.text_area("Enter your question or task here:", height=150, placeholder="e.g., What is Clipboard Health? How is RevOps done there?")
    
    if st.button("Run Queries & Synthesize", type="primary"):
        keys = {
            'gemini': gemini_key.strip() if gemini_key else None,
            'groq': groq_key.strip() if groq_key else None,
            'openai': openai_key.strip() if openai_key else None,
            'anthropic': anthropic_key.strip() if anthropic_key else None,
            'perplexity': perplexity_key.strip() if perplexity_key else None,
        }
        
        # Checking for Cookie expiration / empty keys
        if not any(keys.values()):
            st.error("⚠️ **Your saved API keys have expired or are missing.** Please re-enter at least one API key in the sidebar.")
        elif not prompt.strip():
            st.warning("Please enter a prompt.")
        else:
            with st.status("Fetching responses from all models...", expanded=True) as status:
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                responses = loop.run_until_complete(fetch_all_responses(prompt, keys))
                st.session_state.responses = responses
                
                status.update(label="Responses fetched! Now synthesizing with Gemini 1.5 Pro...", state="running")
                
                synthesis = loop.run_until_complete(synthesize_with_gemini(responses, keys['gemini']))
                st.session_state.synthesis = synthesis
                
                status.update(label="Complete!", state="complete", expanded=False)
    
    # Display Results
    if st.session_state.synthesis:
        st.header("✨ Synthesized Result (by Gemini 1.5 Pro)")
        st.markdown(st.session_state.synthesis)
        
        st.markdown("---")
        st.subheader("🔍 Raw Source Responses")
        
        models = list(st.session_state.responses.keys())
        for i in range(0, len(models), 2):
            col1, col2 = st.columns(2)
            with col1:
                with st.expander(f"{models[i]}"):
                    st.markdown(st.session_state.responses[models[i]])
            if i + 1 < len(models):
                with col2:
                    with st.expander(f"{models[i+1]}"):
                        st.markdown(st.session_state.responses[models[i+1]])


# --- Routing ---
with st.sidebar:
    st.markdown("---")
    # Secret Admin Toggle
    admin_pw = os.environ.get("ADMIN_PASSWORD", "")
    is_admin = st.text_input("Admin Access", type="password", placeholder="Enter Password")
    if is_admin == admin_pw and admin_pw != "":
        st.session_state.admin_mode = True
    else:
        st.session_state.admin_mode = False

if st.session_state.admin_mode:
    render_admin_dashboard()
elif st.session_state.user_email is None:
    render_email_gate()
else:
    render_main_app()
