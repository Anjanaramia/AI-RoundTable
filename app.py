import streamlit as st
import asyncio
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
import google.generativeai as genai
import os

st.set_page_config(page_title="AI RoundTable", page_icon="🧠", layout="wide")

# Initialize Session State
if "responses" not in st.session_state:
    st.session_state.responses = {}
if "synthesis" not in st.session_state:
    st.session_state.synthesis = ""

# --- API Clients Setup ---
async def query_openai(prompt, api_key):
    if not api_key: return "API Key not provided."
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
    if not api_key: return "API Key not provided."
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
    if not api_key: return "API Key not provided."
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

async def query_perplexity(prompt, api_key):
    if not api_key: return "API Key not provided."
    try:
        # Note: Perplexity models update occasionally. Currently llama-3.1-sonar-large-128k-online is popular.
        client = AsyncOpenAI(api_key=api_key, base_url="https://api.perplexity.ai")
        response = await client.chat.completions.create(
            model="llama-3.1-sonar-large-128k-online",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# --- Main App Logic ---
async def fetch_all_responses(prompt, keys):
    tasks = [
        query_openai(prompt, keys.get('openai')),
        query_anthropic(prompt, keys.get('anthropic')),
        query_gemini(prompt, keys.get('gemini')),
        query_perplexity(prompt, keys.get('perplexity'))
    ]
    results = await asyncio.gather(*tasks)
    return {
        "ChatGPT (GPT-4o)": results[0],
        "Claude (Opus)": results[1],
        "Gemini (1.5 Pro)": results[2],
        "Perplexity (Sonar Online)": results[3]
    }

async def synthesize_with_gemini(responses, api_key):
    if not api_key:
        return "Cannot synthesize: Gemini API Key is missing. Please provide it in the sidebar to enable synthesis."
    
    context = "Here are answers to a user's prompt from multiple AI models:\n\n"
    for model_name, answer in responses.items():
        if "API Key not provided" not in answer and "Error:" not in answer:
            context += f"### {model_name}\n{answer}\n\n"
    
    if context == "Here are answers to a user's prompt from multiple AI models:\n\n":
        return "No valid responses were generated to synthesize. Check your API keys."
    
    synthesis_prompt = f"{context}\n\nTask: Synthesize the above information into a single, comprehensive, well-structured, and easy-to-read report. Eliminate redundancies, highlight the most important insights, and present a cohesive final answer to the original prompt. Act like an expert analyst combining research."
    
    return await query_gemini(synthesis_prompt, api_key)

# --- UI ---
st.title("🧠 AI RoundTable")
st.markdown("Ask a master prompt to the top AI models at once, and have Gemini synthesize the final result—just like NotebookLM!")

with st.sidebar:
    st.header("🔑 API Keys")
    st.markdown("Enter the keys for the models you want to query. They are not stored permanently.")
    openai_key = st.text_input("OpenAI API Key (ChatGPT)", type="password")
    anthropic_key = st.text_input("Anthropic API Key (Claude)", type="password")
    gemini_key = st.text_input("Google Gemini API Key", type="password")
    perplexity_key = st.text_input("Perplexity API Key", type="password")

st.markdown("---")
st.subheader("📝 Master Prompt")
prompt = st.text_area("Enter your question or task here:", height=150, placeholder="e.g., What is Clipboard Health? How is RevOps done there?")

if st.button("Run Queries & Synthesize", type="primary"):
    if not prompt.strip():
        st.warning("Please enter a prompt.")
    else:
        keys = {
            'openai': openai_key,
            'anthropic': anthropic_key,
            'gemini': gemini_key,
            'perplexity': perplexity_key
        }
        
        with st.status("Fetching responses from all models...", expanded=True) as status:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            responses = loop.run_until_complete(fetch_all_responses(prompt, keys))
            st.session_state.responses = responses
            
            status.update(label="Responses fetched! Now synthesizing with Gemini 1.5 Pro...", state="running")
            
            synthesis = loop.run_until_complete(synthesize_with_gemini(responses, gemini_key))
            st.session_state.synthesis = synthesis
            
            status.update(label="Complete!", state="complete", expanded=False)

# Display Results
if st.session_state.synthesis:
    st.header("✨ Synthesized Result (by Gemini 1.5 Pro)")
    st.markdown(st.session_state.synthesis)
    
    st.markdown("---")
    st.subheader("🔍 Raw Source Responses")
    
    col1, col2 = st.columns(2)
    models = list(st.session_state.responses.keys())
    
    if len(models) >= 4:
        with col1:
            with st.expander(f"{models[0]}"):
                st.markdown(st.session_state.responses[models[0]])
            with st.expander(f"{models[2]}"):
                st.markdown(st.session_state.responses[models[2]])
                
        with col2:
            with st.expander(f"{models[1]}"):
                st.markdown(st.session_state.responses[models[1]])
            with st.expander(f"{models[3]}"):
                st.markdown(st.session_state.responses[models[3]])
