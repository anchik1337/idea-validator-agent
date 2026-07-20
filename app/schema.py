"""
Data contracts (schemas).

The single most important idea in this file: we force the LLM to return data that
matches a fixed JSON schema, instead of parsing free text. This is the difference
between a toy and a reliable system. On an interview:
  "I use tool-calling with a strict input_schema to guarantee structured output,
   then validate it with Pydantic. Free-text parsing is fragile; this is not."
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Literal


# ---------- Step 1 output: the idea broken into parts ----------
class IdeaAnalysis(BaseModel):
    problem: str
    target_audience: str
    solution: str


# ---------- Step 4 output: the final evaluation ----------
class Scores(BaseModel):
    problem_severity: int = Field(ge=0, le=10)
    market_potential: int = Field(ge=0, le=10)
    differentiation: int = Field(ge=0, le=10)
    feasibility: int = Field(ge=0, le=10)


class Evaluation(BaseModel):
    problem: str
    target_audience: str
    market_size_estimate: str
    competitors: List[str]
    scores: Scores
    verdict: Literal["pursue", "pivot", "drop"]
    reasoning: str

    @field_validator("competitors", mode="before")
    @classmethod
    def coerce_competitors_to_list(cls, v):
        # The model sometimes returns a single string instead of a list.
        # We normalise it so one stray format doesn't crash the whole request.
        if isinstance(v, str):
            return [v]
        return v


# ---------- JSON schemas handed to Claude as "tools" ----------
# Claude returns tool input that matches these schemas. We then validate with Pydantic.

ANALYSIS_TOOL = {
    "name": "submit_analysis",
    "description": "Break the startup idea into its core parts.",
    "input_schema": {
        "type": "object",
        "properties": {
            "problem": {"type": "string", "description": "The core problem being solved."},
            "target_audience": {"type": "string", "description": "Who has this problem."},
            "solution": {"type": "string", "description": "How the idea solves it."},
        },
        "required": ["problem", "target_audience", "solution"],
    },
}

EVALUATION_TOOL = {
    "name": "submit_evaluation",
    "description": "Submit the final structured evaluation of the startup idea.",
    "input_schema": {
        "type": "object",
        "properties": {
            "problem": {"type": "string"},
            "target_audience": {"type": "string"},
            "market_size_estimate": {"type": "string", "description": "A rough sized estimate with reasoning."},
            "competitors": {
                "type": "array",
                "items": {"type": "string"},
                "description": "A list of competitor names. Always an array, even if "
                               "there is only one, e.g. [\"Competitor A\"]. Never a single string.",
            },
            "scores": {
                "type": "object",
                "properties": {
                    "problem_severity": {"type": "integer", "minimum": 0, "maximum": 10},
                    "market_potential": {"type": "integer", "minimum": 0, "maximum": 10},
                    "differentiation": {"type": "integer", "minimum": 0, "maximum": 10},
                    "feasibility": {"type": "integer", "minimum": 0, "maximum": 10},
                },
                "required": ["problem_severity", "market_potential", "differentiation", "feasibility"],
            },
            "verdict": {"type": "string", "enum": ["pursue", "pivot", "drop"]},
            "reasoning": {"type": "string", "description": "Why this verdict, in 2-4 sentences."},
        },
        "required": [
            "problem", "target_audience", "market_size_estimate",
            "competitors", "scores", "verdict", "reasoning",
        ],
    },
}

# The web-search tool Claude can call autonomously during the research step.
SEARCH_TOOL = {
    "name": "search_web",
    "description": "Search the web for competitors, market data, or existing solutions. "
                   "Call this when you need real-world facts about the idea's market.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "A focused search query."}
        },
        "required": ["query"],
    },
}
