"""
FastAPI web layer.

This exposes the agent over HTTP so it is a real service, not a script.
Run it with:  uvicorn app.main:app --reload
Then open http://127.0.0.1:8000/docs for an interactive UI.
"""

from dotenv import load_dotenv
load_dotenv()  # load ANTHROPIC_API_KEY / TAVILY_API_KEY from .env before anything else

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .agent import validate_idea
from .schema import Evaluation

app = FastAPI(title="Idea Validator Agent", version="1.0")


class ValidateRequest(BaseModel):
    idea: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/validate", response_model=Evaluation)
def validate(req: ValidateRequest):
    if not req.idea or len(req.idea.strip()) < 10:
        raise HTTPException(status_code=400, detail="Please provide a real idea (>= 10 chars).")
    try:
        return validate_idea(req.idea)
    except Exception as e:
        # Surface a clean error instead of a stack trace to the client.
        raise HTTPException(status_code=500, detail=f"Agent failed: {e}")
