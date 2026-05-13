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

# --- UI ---
st.title("🧠 AI RoundTable")
st.markdown("Ask a master prompt to top-tier AI models at once, and have Gemini synthesize the final result—just like NotebookLM!")
st.info("💡 **Pro Tip:** To save free tokens and avoid rate limits, bundle multiple questions into a single master prompt rather than asking them one by one!")

with st.sidebar:
    st.header("🔑 API Keys")
    st.markdown("Enter keys for the models you want to query. The app will automatically skip any that are left blank.")
    
    st.subheader("Required for Synthesis")
    gemini_key = st.text_input("Google Gemini API Key", type="password")
    st.caption("[Get Gemini API Key](https://aistudio.google.com/app/apikey)")
    
    st.subheader("Free Alternatives")
    groq_key = st.text_input("Groq API Key", type="password")
    st.caption("[Get Groq API Key](https://console.groq.com/keys)")
    
    st.subheader("Paid Options")
    openai_key = st.text_input("OpenAI API Key (ChatGPT)", type="password")
    st.caption("[Get OpenAI API Key](https://platform.openai.com/api-keys)")
    
    anthropic_key = st.text_input("Anthropic API Key (Claude)", type="password")
    st.caption("[Get Anthropic API Key](https://console.anthropic.com/settings/keys)")
    
    perplexity_key = st.text_input("Perplexity API Key", type="password")
    st.caption("[Get Perplexity API Key](https://www.perplexity.ai/settings/api)")

st.markdown("---")
st.subheader("📝 Master Prompt")
prompt = st.text_area("Enter your question or task here:", height=150, placeholder="e.g., What is Clipboard Health? How is RevOps done there?")

if st.button("Run Queries & Synthesize", type="primary"):
    if not prompt.strip():
        st.warning("Please enter a prompt.")
    else:
        keys = {
            'gemini': gemini_key.strip() if gemini_key else None,
            'groq': groq_key.strip() if groq_key else None,
            'openai': openai_key.strip() if openai_key else None,
            'anthropic': anthropic_key.strip() if anthropic_key else None,
            'perplexity': perplexity_key.strip() if perplexity_key else None,
        }
        
        # Check if at least one key is provided
        if not any(keys.values()):
            st.error("Please provide at least one API key in the sidebar.")
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
    
    # Dynamically display raw responses in rows of 2
    for i in range(0, len(models), 2):
        col1, col2 = st.columns(2)
        with col1:
            with st.expander(f"{models[i]}"):
                st.markdown(st.session_state.responses[models[i]])
        if i + 1 < len(models):
            with col2:
                with st.expander(f"{models[i+1]}"):
                    st.markdown(st.session_state.responses[models[i+1]])
