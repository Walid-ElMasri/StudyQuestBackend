from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import os
import json
import re

router = APIRouter()

# From your .env:
# HF_API_KEY=...
# HF_MODEL=HuggingFaceTB/SmolLM3-3B:hf-inference   (example)
HF_TOKEN = "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"
HF_MODEL = "HuggingFaceTB/SmolLM3-3B:hf-inference"


# OpenAI client, but pointed at Hugging Face router
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key="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",
)



class FlashcardsRequest(BaseModel):
    required: int
    text: str


@router.post("/ai/flashcards")
async def ai_flashcards(req: FlashcardsRequest):
    if not HF_TOKEN or not HF_MODEL:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Server misconfigured",
                "details": "HF_API_KEY or HF_MODEL missing",
            },
        )

    prompt = (
        "You are a study assistant.\n"
        f"Create exactly {req.required} flashcards from the following text.\n"
        "Return them as PURE JSON ONLY (no explanations, no backticks), in this format:\n"
        '[{\"question\": \"...\", \"answer\": \"...\"}, ...]\n'
        "Text:\n"
        f"{req.text}"
    )

    try:
        completion = client.chat.completions.create(
            model=HF_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful study assistant."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=512,
            temperature=0.6,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "AI generation failed", "details": str(e)},
        )

    # Extract the assistant message
    try:
        content = completion.choices[0].message.content or ""
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Bad AI response",
                "details": f"parse error: {e}, raw={completion}",
            },
        )

    # ---------- CLEAN THE OUTPUT & PARSE JSON ----------

    text = content.strip()

    # 1) Remove <think> ... </think> or <think> ... (even if no closing tag)
    text = re.sub(r"<think>.*?(?:</think>|$)", "", text, flags=re.DOTALL).strip()

    # 2) If there are ``` fences, keep only what's inside them
    if "```" in text:
        parts = text.split("```")
        inner_candidates = [p for p in parts if p.strip()]
        if inner_candidates:
            text = max(inner_candidates, key=len).strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()

    # 3) Extract the JSON array [ ... ]
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and start < end:
        json_text = text[start : end + 1]
    else:
        json_text = text  # fallback

    # 4) Try to parse JSON
    try:
        questions = json.loads(json_text)
        if not isinstance(questions, list):
            questions = [{"question": "AI output", "answer": text}]
    except Exception:
        questions = [{"question": "AI output", "answer": text}]

    # ---------- ENSURE EXACTLY req.required FLASHCARDS ----------

    # Make sure required is at least 1
    needed = req.required if req.required > 0 else 1

    # Normalize: everything must be a dict with question/answer strings
    normalized = []
    for idx, q in enumerate(questions):
        if isinstance(q, dict):
            question_text = str(q.get("question", "")).strip()
            answer_text = str(q.get("answer", "")).strip()
            if not question_text:
                question_text = f"Question {idx+1}"
            if not answer_text:
                answer_text = "Answer not provided."
        else:
            # If it's not a dict, just wrap it
            question_text = f"Question {idx+1}"
            answer_text = str(q)
        normalized.append({"question": question_text, "answer": answer_text})

    questions = normalized

    # If fewer than needed, fill with generic extras
    while len(questions) < needed:
        n = len(questions) + 1
        questions.append({
            "question": f"Extra question {n}: Summarize a key idea from the text.",
            "answer": "This is a placeholder flashcard. The user should summarize a key idea from the text."
        })

    # If more than needed, trim
    if len(questions) > needed:
        questions = questions[:needed]

    return {"questions": questions, "error": None, "details": None}
