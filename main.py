from fastapi import FastAPI
import wikipedia
import os
from dotenv import load_dotenv

# Gemini
import google.generativeai as genai

# Groq
from groq import Groq

load_dotenv()

app = FastAPI()

# 🔹 Setup APIs
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.5-flash")

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# 🔹 Gemini Answer
def get_ai_answer(query):
    response = gemini_model.generate_content(query)
    return response.text

# 🔹 Groq Answer
def get_groq_answer(query):
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": query}]
    )
    return response.choices[0].message.content


# 🔹 Better Evidence Retrieval
def get_evidence(claim):
    try:
        short_query = claim.split(".")[0]
        return wikipedia.summary(short_query, sentences=2)
    except:
        return "No evidence found"


# 🔹 Improved Claim Extraction
def extract_claims(answer):
    prompt = f"""
    Extract 3-5 short factual claims from this answer.

    Keep them simple and separate.

    Answer:
    {answer}

    Output ONLY like:
    ["claim 1", "claim 2", "claim 3"]
    """

    response = gemini_model.generate_content(prompt)

    try:
        claims = eval(response.text)
    except:
        claims = [answer[:100]]

    return claims


# 🔹 Claim Verification
def verify_claim(claim):

    evidence = get_evidence(claim)

    # ❗ Important fix: No evidence = Not Supported
    if evidence == "No evidence found":
        return {
            "claim": claim,
            "evidence": evidence,
            "result": "Not Supported",
            "score": 0
        }

    prompt = f"""
    Claim: {claim}

    Evidence: {evidence}

    Is the claim supported?

    Reply ONLY:
    Supported / Not Supported / Conflicting
    """

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    result = response.choices[0].message.content

    return {
        "claim": claim,
        "evidence": evidence,
        "result": result
    }


# 🔹 Score Logic
def score_claim(result):
    if "Supported" in result:
        return 1
    elif "Conflicting" in result:
        return 0.5
    else:
        return 0


# 🔹 Evaluate Full Answer
def evaluate_answer(claims):
    results = []
    total_score = 0

    for claim in claims:
        verification = verify_claim(claim)

        # If score not already set
        if "score" not in verification:
            score = score_claim(verification["result"])
            verification["score"] = score
        else:
            score = verification["score"]

        total_score += score
        results.append(verification)

    avg_score = total_score / len(claims) if claims else 0

    return results, avg_score


# 🔹 Winner Selection
def select_winner(gemini_score, groq_score):
    if gemini_score > groq_score:
        return "gemini", gemini_score
    elif groq_score > gemini_score:
        return "groq", groq_score
    else:
        return "tie", gemini_score


# 🔹 Explanation
def generate_explanation(results):
    explanation = []

    for model in results:
        explanation.append(
            f"{model['model']} scored {model['score']} based on claim verification."
        )

    explanation.append("Higher score means more claims were supported by evidence.")

    return explanation


# 🔹 FINAL API
@app.get("/verify")
def verify_query(query: str):
    try:
        gemini_answer = get_ai_answer(query)
        groq_answer = get_groq_answer(query)

        gemini_claims = extract_claims(gemini_answer)
        groq_claims = extract_claims(groq_answer)

        gemini_results, gemini_score = evaluate_answer(gemini_claims)
        groq_results, groq_score = evaluate_answer(groq_claims)

        winner, best_score = select_winner(gemini_score, groq_score)

        results = [
            {
                "model": "gemini",
                "answer": gemini_answer,
                "score": gemini_score,
                "details": gemini_results
            },
            {
                "model": "groq",
                "answer": groq_answer,
                "score": groq_score,
                "details": groq_results
            }
        ]

        explanation = generate_explanation(results)

        return {
            "query": query,
            "winner": winner,
            "best_score": best_score,
            "results": results,
            "explanation": explanation
        }

    except Exception as e:
        return {"error": str(e)}
