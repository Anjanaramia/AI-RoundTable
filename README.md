# 🧠 AI RoundTable (GenAI Info Summarizer)

AI RoundTable is a powerful, locally-hosted Streamlit application that allows you to ask a single "Master Prompt" to multiple top-tier AI models simultaneously (like ChatGPT, Claude, Gemini, Groq, and Perplexity). It then uses **Google Gemini 1.5 Pro** to synthesize all the diverse answers into a single, comprehensive, NotebookLM-style report.

## Features

- **Multi-Model Querying**: Get diverse perspectives from both paid models (OpenAI, Anthropic, Perplexity) and free, open-source models (Llama-3, Mixtral via Groq).
- **Master Synthesizer**: Automatically blends all perspectives into one cohesive report.
- **Cookie Management**: Your API keys are securely saved in your browser's cookies. You don't need to re-enter them every time.
- **Email Gate & Lead Capture**: Tracks who uses your tool by requiring an email address to unlock the main application.
- **Admin Dashboard**: A hidden view to see all captured user emails and names, with an option to download the data as a CSV.

## Setup Instructions

### 1. Install Dependencies

Ensure you have Python installed, then install the required libraries:
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory (you can copy `.env.example`). 

Set your `ADMIN_PASSWORD`:
```env
ADMIN_PASSWORD=your_secure_password_here
```
*Note: You do not need to hardcode API keys in this file. The app allows users to input their own keys in the sidebar, which are then saved securely in their browser cookies.*

### 3. Run the App

Launch the Streamlit server:
```bash
streamlit run app.py
```

## How to Use the App

### For Users:
1. **Email Gate**: When a user first opens the app, they will be asked to enter their Email and optional First Name.
2. **API Keys**: Once unlocked, they must enter at least one API key in the sidebar. (Google Gemini is recommended for the synthesis step). Keys are automatically saved to their browser cookies.
3. **Prompt**: Enter a detailed question in the Master Prompt box and click "Run Queries & Synthesize".

### For Admins:
To view the captured emails and user data:
1. Look at the very bottom of the sidebar for the **Admin Access** password box.
2. Enter the `ADMIN_PASSWORD` you set in your `.env` file.
3. The app will transform into the Admin Dashboard, displaying a table of all registered users and a button to export the data to CSV.
