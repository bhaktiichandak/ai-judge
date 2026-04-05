# AI Judge

AI Judge is an LLM-powered evaluation app built with FastAPI and Streamlit. It reviews writing, code, arguments, and ideas using a multi-model consensus flow.

## Features

- Deterministic consensus judging
- Structured verdict, reasoning, and suggestions
- Streamlit chat UI
- Optional MongoDB Atlas chat persistence by session id

## Tech Stack

- Python
- FastAPI
- Streamlit
- Groq
- Gemini
- MongoDB Atlas

## Installation

```bash
git clone https://github.com/bhaktiichandak/ai-judge.git
cd ai-judge
pip install -r requirements.txt
```

## Environment Variables

Add these values to `backend/.env`:

```env
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
MONGODB_URI=your_mongodb_atlas_connection_string
MONGODB_DB_NAME=ai_judge
```

Add this value to `frontend/.env` if needed:

```env
BACKEND_URL=http://localhost:8000
```

If `MONGODB_URI` is not set, the app still works, but chat history stays local to the current Streamlit session instead of being stored in MongoDB Atlas. When MongoDB is configured, the frontend keeps a `chat` session id in the URL and reloads that conversation from the backend on refresh.

## Run Locally

```bash
uvicorn backend.main:app --reload
streamlit run frontend/app.py
```
