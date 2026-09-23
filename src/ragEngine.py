import os
import sys
import json
import re
import math
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from openai import OpenAI
from src.config import SPECS_DIR, TESTS_DIR, RUNS_DIR, GEMINI_API_KEY, GEMINI_BASE_URL, GEMINI_MODEL, AI_PROVIDER

def tokenize(text):
    return re.findall(r'\w+', text.lower())

def compute_tf(tokens):
    tf = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1
    total = len(tokens) or 1
    return {k: v / total for k, v in tf.items()}

def cosine_sim(tf1, tf2):
    all_keys = set(tf1.keys()).union(set(tf2.keys()))
    dot = sum(tf1.get(k, 0) * tf2.get(k, 0) for k in all_keys)
    norm1 = math.sqrt(sum(v*v for v in tf1.values()))
    norm2 = math.sqrt(sum(v*v for v in tf2.values()))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

class RAGEngine:
    def __init__(self):
        self.documents = []

    def index_all(self):
        self.documents = []

        # Index specs
        for p in SPECS_DIR.glob("*.md"):
            with open(p, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for idx, line in enumerate(lines, 1):
                if line.strip():
                    self.documents.append({
                        "source": str(p.relative_to(p.parent.parent)),
                        "line": idx,
                        "content": line.strip(),
                        "type": "spec"
                    })

        # Index tests
        for p in TESTS_DIR.glob("*.py"):
            with open(p, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for idx, line in enumerate(lines, 1):
                if line.strip():
                    self.documents.append({
                        "source": str(p.relative_to(p.parent.parent)),
                        "line": idx,
                        "content": line.strip(),
                        "type": "test"
                    })

        # Index run logs
        for p in RUNS_DIR.glob("*.json"):
            with open(p, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    summary = f"Run {data.get('timestamp')}: Status={data.get('status')}. Error={data.get('error_summary')}"
                    self.documents.append({
                        "source": str(p.relative_to(p.parent.parent)),
                        "line": 1,
                        "content": summary,
                        "type": "run_log"
                    })
                except Exception:
                    pass

    def query(self, question, top_k=3):
        if not self.documents:
            self.index_all()

        query_tokens = tokenize(question)
        query_tf = compute_tf(query_tokens)

        scored_docs = []
        for doc in self.documents:
            doc_tokens = tokenize(doc["content"])
            doc_tf = compute_tf(doc_tokens)
            score = cosine_sim(query_tf, doc_tf)
            if score > 0:
                scored_docs.append((score, doc))

        scored_docs.sort(key=lambda x: x[0], reverse=True)
        top_matches = [doc for score, doc in scored_docs[:top_k]]

        if not top_matches:
            top_matches = self.documents[:min(3, len(self.documents))]

        # Gemini-synthesized grounded answer
        if GEMINI_API_KEY:
            try:
                client = OpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL)
                context_str = "\n".join([f"[{d['source']}:L{d['line']}] {d['content']}" for d in top_matches])
                res = client.chat.completions.create(
                    model=GEMINI_MODEL,
                    messages=[
                        {"role": "system", "content": "You are Sentinel's Test Knowledge Assistant. Answer the question using ONLY the provided document context. Cite source files and line numbers in your answer."},
                        {"role": "user", "content": f"Context:\n{context_str}\n\nQuestion: {question}"}
                    ],
                    temperature=0.2,
                    timeout=15
                )
                return res.choices[0].message.content.strip()
            except Exception as e:
                print(f"[RAG Warning] {AI_PROVIDER} API call failed ({e}). Using local citation formatter...")

        # Local grounded citation formatter (fallback only)
        response = f"### Sentinel RAG Answer for: \"{question}\"\n\n"
        response += "Based on test specifications, Playwright code, and execution run logs:\n\n"
        for doc in top_matches:
            response += f"- **Citation**: [`{doc['source']}:L{doc['line']}`](file:///{doc['source']})\n"
            response += f"  > \"{doc['content']}\"\n"
        return response

def ask_question(question_text):
    rag = RAGEngine()
    answer = rag.query(question_text)
    print(answer)
    return answer

if __name__ == "__main__":
    if len(sys.argv) > 1:
        ask_question(" ".join(sys.argv[1:]))
    else:
        ask_question("Which tests cover the export PDF feature?")
