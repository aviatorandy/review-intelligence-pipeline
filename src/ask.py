"""
Ask a question about the reviews using semantic search + LLM summarization.
"""
import os
from .embeddings import query_index
from .llm_client import call_llm


ASK_SYSTEM = """You are a helpful product analyst answering questions about Amazon product reviews.
You will be given a question and a set of relevant customer reviews.
Write a clear, conversational answer in 2-4 sentences as if explaining to a colleague.
Use natural language — no bullet points, no headers, no JSON, no markdown formatting like ** or #.
Ground your answer in what the reviews actually say, but write it naturally.
If the reviews don't contain enough information to answer confidently, say so plainly."""


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
