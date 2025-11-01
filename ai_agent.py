from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests, os
from typing import List
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI 

load_dotenv()

app = FastAPI()
SERPER_API_KEY="549f4973f633c4bec0a51879cf6dd1f45f095a2f"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL_NAME = os.getenv("DEEPSEEK_MODEL_NAME", "deepseek/deepseek-chat-v3.1:free")
MODEL_BASE_URL = os.getenv("MODEL_BASE_URL", "https://openrouter.ai/api/v1")


# --- Models ---
class TopicRequest(BaseModel):
    topic: str

# --- Gemini Setup ---
llm = ChatOpenAI(
    api_key=DEEPSEEK_API_KEY,
    model="deepseek/deepseek-chat-v3.1:free",
    base_url="https://openrouter.ai/api/v1"
)


# --- Helper: Search ---
def search_serper(topic: str):
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {"q": topic, "num": 8}
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code != 200:
        raise HTTPException(status_code=500, detail="Serper search failed")
    data = res.json()
    results = []
    for item in data.get("organic", []):
        results.append({
            "title": item.get("title"),
            "link": item.get("link"),
            "snippet": item.get("snippet", "")
        })
    return results

# --- Helper: Summarize & Rank ---
import json
import re

def summarize_and_rank(results, topic):
    # Clear instruction + JSON-only constraint
    prompt = PromptTemplate.from_template("""
    You are an AI content summarizer and evaluator.

    Topic: {topic}
    Content items: {results}

    For each item:
    - Write a concise 2-line summary.
    - Assign relevance (0–10) and sentiment (-1, 0, 1).

    Return **strict JSON only**, no explanations, no text before or after:
    [
      {{"title": "string", "summary": "string", "relevance": int, "sentiment": int, "link": "string"}},
      ...
    ]
    """)

    chain = prompt | llm
    response = chain.invoke({"topic": topic, "results": results})

    raw_text = response.content.strip()

    # Try to isolate JSON if model wraps it in extra text
    match = re.search(r"\[.*\]", raw_text, re.DOTALL)
    json_text = match.group(0) if match else raw_text

    try:
        data = json.loads(json_text)
    except Exception as e:
        print("⚠️ Error parsing JSON:", e)
        # fallback: generate basic summaries manually
        data = [
            {
                "title": item.get("title", "Untitled"),
                "summary": item.get("snippet", "")[:200],
                "relevance": 5,
                "sentiment": 0,
                "link": item.get("link", "")
            }
            for item in results[:5]
        ]

    # Sort and trim
    data = sorted(data, key=lambda x: x.get("relevance", 0), reverse=True)
    return data[:5]
# --- Route ---
@app.post("/search")
def search_topic(req: TopicRequest):
    results = search_serper(req.topic)
    ranked = summarize_and_rank(results, req.topic)
    return {"topic": req.topic, "results": ranked}
