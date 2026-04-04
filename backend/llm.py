import os
import concurrent.futures
from dotenv import load_dotenv
from groq import Groq
import google.generativeai as genai
from duckduckgo_search import DDGS

# ── Load API key from .env file ──
from pathlib import Path
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# ── Setup Groq client ─────────────────────────────────
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Setup Gemini client ───────────────────────────────
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

# ── Dynamic System Prompt Generator ───────────────────
def get_system_prompt(mode: str) -> str:
    base_instructions = """You are AI Judge — a smart, structured, and unbiased evaluation engine.

IMPORTANT: First, silently fix any typos or spelling mistakes (e.g., "ecplan" -> "explain", "indi" -> "india") to understand the user's true intent. Do not output an error or penalize them for typos.

CRITICAL INSTRUCTION: If the intended meaning is a direct factual question (e.g., asking to explain a theory, "who", "what") or asks you to WRITE, GENERATE, or CREATE something, you MUST fulfill their request directly. Answer their question or output the generated content. Do NOT evaluate their prompt as if it were a submission.

For all other inputs where the user wants you to evaluate or judge their work, you ALWAYS respond in this exact format based on your active mode:
"""

    if mode == "feedback":
        format_instructions = """## 📝 Strengths\nHighlight what the user did well.\n\n## 📉 Areas for Improvement\nPoint out specific flaws or weak points.\n\n## 🛠️ Actionable Steps\n- Step 1\n- Step 2"""
    elif mode == "analyze":
        format_instructions = """## 🔍 Core Concept\nA breakdown of the main idea.\n\n## 🧩 Logical Structure\nHow the pieces of the user's input fit together.\n\n## 💡 Deep Insights\nHidden nuances, implications, or edge cases."""
    elif mode == "compare":
        format_instructions = """## ⚖️ A vs B Breakdown\nA detailed comparison of the elements in the prompt.\n\n## 🌟 Pros and Cons\nStrengths and weaknesses of each side.\n\n## 🏆 Final Recommendation\nWhich approach is objectively better and why."""
    else: # Default to "judge"
        format_instructions = """## ⚖️ Verdict\nOne clear sentence judgment.\n\n## 🧠 Reasoning\n2-3 lines explaining why you gave this verdict.\n\n## 📊 Score\nX/10 — one line reason for this score.\n\n## 💡 Suggestions\n- Suggestion 1\n- Suggestion 2"""

    return base_instructions + "\n" + format_instructions + "\n\nAlways be direct, fair, constructive and helpful."

# ── Groq function ─────────────────────────────────────
def ask_groq(user_message: str, history: list, mode: str) -> str:
    """
    Sends message to Groq (Llama 3.1 model).
    history = list of previous messages in conversation.
    """
    system_prompt = get_system_prompt(mode)
    # Build the full message list
    messages = [{"role": "system", "content": system_prompt}]

    # Add previous conversation
    for msg in history:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    # Call Groq API
    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        temperature=0.7,
        max_tokens=1024
    )

    return response.choices[0].message.content


# ── Live Web Search (Ground Truth) ────────────────────
def search_web(query: str) -> str:
    """Searches the live internet (prioritizing research sites) for ground truth facts."""
    try:
        # 1. Use Groq to instantly fix typos and generate a clean, optimized search term
        try:
            ai_query = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "Extract the main entity or question from the user's text into a simple 2-4 word search query. Fix all typos. DO NOT output quotes, punctuation, or conversational text. ONLY the raw keywords."},
                    {"role": "user", "content": query}
                ],
                temperature=0.0,
                max_tokens=15
            )
            clean_query = ai_query.choices[0].message.content.strip(' "\'\n.,')
        except Exception:
            # Fallback if the AI cleanup fails
            clean_query = query if len(query) < 50 else query[:50]
        
        print(f"\n🔍 [DEBUG] Searching the web for: '{clean_query}'")

        # 2. Search authoritative sources explicitly with the clean keywords
        with DDGS() as ddgs:
            # 1. Try strict Wikipedia search
            results = list(ddgs.text(f"{clean_query} site:wikipedia.org", max_results=3))
            
            # 2. Try broad Wikipedia search if strict fails
            if not results:
                results = list(ddgs.text(f"{clean_query} wikipedia", max_results=3))
                
            # 3. Fallback to general search if all else fails
            if not results:
                results = list(ddgs.text(clean_query, max_results=3))
                
            if not results:
                print("❌ [DEBUG] Web search returned 0 results.")
                return "No live web results found. You must rely on your internal knowledge."
                
            context = ""
            for r in results:
                context += f"Source: {r.get('href')}\nSummary: {r.get('body')}\n\n"
            
            print(f"✅ [DEBUG] Found sources!\n{context}")
            return context
    except Exception as e:
        print(f"🚨 [DEBUG] Web search crashed: {str(e)}")
        return f"Web search unavailable due to error: {str(e)}"

# ── Meta-Synthesis Prompt ─────────────────────────────
SYNTHESIS_PROMPT = """
You are the AI Consensus Evaluator. You are provided with answers from two different AI models: Groq/Llama and Gemini.
Your job is to compare them, find contradictions, and fact-check them against the provided LIVE WEB SEARCH RESULTS. Treat the web results (which prioritize Wikipedia, Britannica, and academic/gov sources) as the ABSOLUTE AUTHENTIC GROUND TRUTH to determine which model is correct.

IMPORTANT: If the user's original prompt contains typos (e.g., "indi" instead of "india"), intelligently infer what they meant. Do not state that the query is invalid.

You MUST respond in this exact format:

## 🏆 Best Answer
[State which model (Groq/Llama or Gemini) gave the better answer and why in 1-2 sentences. Use their actual names.]

## 🔍 Contradictions
[List any factual or logical contradictions between the two models. If none, say "Models completely agree."]

## 💯 Confidence Score
[Provide a score from 0-100% based on how closely the models agree]

## ⚖️ Final Consensus Verdict
[Your final combined response to the user's prompt.
CRITICAL 1: If the user asked a factual question (even with typos), you MUST answer it accurately using the LIVE WEB SEARCH RESULTS, even if the base models failed to answer it.
CRITICAL 2: If the user asked you to GENERATE content (e.g., write an essay, code), you MUST output the FULL, actual generated text here. Do NOT summarize.]

## 📚 Sources & References
[List the actual URLs from the LIVE WEB SEARCH RESULTS used to verify the facts. For each source, include a brief explanation of HOW it proves the correct answer. Format them as clickable Markdown links, e.g., - [Website Name](URL): Explanation. If the LIVE WEB SEARCH RESULTS text says "Web search unavailable" or "No live web results found", you MUST output EXACTLY: "Internal AI Knowledge: [Explain why web search failed based on the provided text]". Do NOT write N/A for factual questions.]
"""

# ── Gemini function ───────────────────────────────────
def ask_gemini(user_message: str, history: list, mode: str) -> str:
    """
    Sends message to Gemini.
    Gemini doesn't support system prompts the same way,
    so we include it at the start of the conversation.
    """
    system_prompt = get_system_prompt(mode)
    # Build full prompt with history
    full_prompt = system_prompt + "\n\n"

    for msg in history:
        role = "User" if msg["role"] == "user" else "Assistant"
        full_prompt += f"{role}: {msg['content']}\n\n"

    full_prompt += f"User: {user_message}"

    response = gemini_model.generate_content(full_prompt)
    return response.text


# ── Main function (used by routes.py) ─────────────────
def get_ai_response(user_message: str, history: list, model: str = "groq", mode: str = "judge") -> str:
    """
    Runs BOTH models in parallel, then synthesizes the results 
    to provide a confidence score, contradictions, and best answer.
    """
    try:
        # 1. Run both models AND web search in parallel to prevent lag
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_groq = executor.submit(ask_groq, user_message, history, mode)
            future_gemini = executor.submit(ask_gemini, user_message, history, mode)
            future_search = executor.submit(search_web, user_message)
            
            try:
                groq_answer = future_groq.result()
            except Exception as e:
                groq_answer = f"Error from Groq: {str(e)}"
                
            try:
                gemini_answer = future_gemini.result()
            except Exception as e:
                gemini_answer = f"Error from Gemini: {str(e)}"
                
            try:
                live_web_facts = future_search.result()
            except Exception:
                live_web_facts = "Web search unavailable."

        # 2. Synthesize the final consensus using the live facts
        synthesis_user_message = f"User's original prompt: {user_message}\n\nLIVE WEB SEARCH RESULTS (GROUND TRUTH):\n{live_web_facts}\n\nGroq/Llama Answer:\n{groq_answer}\n\nGemini Answer:\n{gemini_answer}"
        
        messages = [
            {"role": "system", "content": SYNTHESIS_PROMPT},
            {"role": "user", "content": synthesis_user_message}
        ]
        
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.3,
            max_tokens=1024
        )
        
        return response.choices[0].message.content

    except Exception as e:
        raise RuntimeError(f"AI call failed: {str(e)}")