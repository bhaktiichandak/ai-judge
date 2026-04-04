# 🧑‍⚖️ AI Judge

An AI-powered evaluation system that automatically reviews, scores, and provides feedback on user inputs/projects using Large Language Models.

---

## 🚀 Overview

AI Judge is designed to simulate a real-world judging system using AI. It evaluates outputs based on defined criteria such as correctness, clarity, and quality, and provides structured feedback.

This project demonstrates how LLMs can be used as evaluators (LLM-as-a-Judge) to automate decision-making and scoring tasks.

---

## ✨ Features

- 🤖 AI-based evaluation system
- 📊 Scoring based on custom criteria
- 📝 Detailed feedback generation
- ⚡ Fast and automated judging
- 🔧 Easily customizable prompts

---

## 🛠️ Tech Stack

- Python
- FastAPI
- Streamlit
- Groq
- Gemini

---

## ⚙️ How It Works

1. User provides input (project / answer / code / idea)
2. AI model evaluates it using predefined criteria
3. System generates:
   - Score
   - Reasoning
   - Feedback

This follows the concept of **LLM-as-a-Judge**, where AI evaluates outputs instead of humans :contentReference[oaicite:0]{index=0}.

---

## 📦 Installation

```bash
git clone https://github.com/bhaktiichandak/ai-judge.git
cd ai-judge
pip install -r requirements.txt
```

## ▶️ Run Locally

```bash
uvicorn backend.main:app --reload
streamlit run frontend/app.py
```

## 👩‍💻 Authors

- **Bhakti Chandak**  
  GitHub: https://github.com/bhaktiichandak  
  Email: bhaktichandak04@gmail.com

- **Teammate Name**  
  GitHub: https://github.com/teammate  
  Email: tpande966@gmail.com
