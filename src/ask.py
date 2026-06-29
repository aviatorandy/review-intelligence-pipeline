"""
Ask a question about the reviews using semantic search + LLM summarization.
"""
import os
from .embeddings import query_index
from .llm_client import call_llm


ASK_SYSTEM = """You are a product analyst answering questions about Amazon product reviews.
You will be given a question and a set of relevant reviews retrieved by semantic search.
Answer the question directly and concisely, grounding every claim in the reviews provided.
Format your response as:

**Answer:** <2-3 sentence direct answer>

**Key evidence:**
- Review #<id> (<sentiment>): "<quote>"
- Review #<id> (<sentiment>): "<quote>"
(up to 5 pieces of evidence)

**Confidence:** <high/medium/low> — <one sentence reason>

Respond in plain text, no JSON."""


def ask_question(job_id: str, question: str) -> dict:
    """
    Retrieve relevant reviews and generate a grounded answer.
    Returns {answer, sources, question}.
    """
    reviews = query_index(job_id, question, n_results=20)

    if not reviews:
        return {
            "question": question,
            "answer": "No indexed reviews found for this job. Please wait for indexing to complete.",
            "sources": [],
        }

    # Format retrieved reviews for the prompt
    reviews_text = "\n".join([
        f"Review #{r['review_id']} ({r['sentiment']}, relevance={r['relevance']}): {r['text']}"
        for r in reviews
    ])

    user_prompt = f"""Question: {question}

Retrieved reviews (ordered by relevance):
{reviews_text}

Answer the question based only on these reviews."""

    answer_text = call_llm(ASK_SYSTEM, user_prompt)

    return {
        "question": question,
        "answer": answer_text,
        "sources": reviews[:5],  # top 5 for display
    }
