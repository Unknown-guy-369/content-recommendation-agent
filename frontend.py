import streamlit as st
import requests

BACKEND_URL = "http://127.0.0.1:8000/search"

st.set_page_config(page_title="Content Research Agent", layout="wide")

st.title("🔎 Content Research Agent")
topic = st.text_input("Enter a topic to research", placeholder="e.g. AI agents, LangGraph, Blockchain...")

if st.button("Search & Summarize"):
    if not topic.strip():
        st.warning("Enter a topic first.")
    else:
        with st.spinner("Fetching and analyzing content..."):
            res = requests.post(BACKEND_URL, json={"topic": topic})
            if res.status_code != 200:
                st.error("Backend request failed")
            else:
                data = res.json()["results"]
                st.subheader(f"Top Results for: {topic}")
                for idx, item in enumerate(data, 1):
                    st.markdown(f"### {idx}. [{item['title']}]({item['link']})")
                    st.markdown(f"**Summary:** {item['summary']}")
                    st.markdown(f"**Relevance:** {item['relevance']} | **Sentiment:** {item['sentiment']}")
                    st.divider()
