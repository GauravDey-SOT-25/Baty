from src.assistant.local_model import answer_locally


def answer(question: str, lab_context: str | None = None) -> dict:
    question = (question or "").strip()[:8000]
    if not question:
        raise ValueError("Question is required")
    response = answer_locally(question)
    if response is None:
        response = "The local language model is not available yet. It is not downloaded automatically. Use the message and passive URL checks as limited triage aids until a local model is installed."
    return {"answer": response,
            "sources": [], "limitations": ["No external lookup was performed.", "The language model can make mistakes; verify technical steps before use."],
            "authorized_lab_context_supplied": bool(lab_context)}
