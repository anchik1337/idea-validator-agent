"""
The agent: a 4-step pipeline that turns a raw idea into a structured evaluation.

Why multiple steps instead of one giant prompt?
  - Each step is testable and debuggable on its own.
  - We can measure quality per step.
  - Step 2 is *agentic* (the model decides when to search); the others are controlled.
This mix of "forced structured output" + "autonomous tool use" is exactly what an
applied AI engineer is expected to build.

Pipeline:
  1. analyze  -> break idea into problem / audience / solution   (forced structured output)
  2. research -> model calls search_web as needed                (agentic tool loop)
  3. retrieve -> pull relevant frameworks from the knowledge base (RAG)
  4. evaluate -> final scored verdict                            (forced structured output)
"""

from .config import MODEL_SMART, MAX_SEARCH_ITERATIONS
from .schema import (
    ANALYSIS_TOOL, EVALUATION_TOOL, SEARCH_TOOL,
    IdeaAnalysis, Evaluation,
)
from .llm import get_structured, raw_message
from .tools import search_web
from .rag import retrieve


def step1_analyze(idea: str) -> IdeaAnalysis:
    prompt = (
        "Break the following startup idea into its core parts.\n\n"
        f"IDEA: {idea}"
    )
    data = get_structured(MODEL_SMART, prompt, ANALYSIS_TOOL)
    return IdeaAnalysis(**data)  # Pydantic validates the shape here.


def step2_research(idea: str, analysis: IdeaAnalysis) -> str:
    """
    Agentic research loop: give the model the search_web tool and let it decide
    when and what to search. We run the loop until it stops calling the tool or
    hits MAX_SEARCH_ITERATIONS (a safety bound on cost).
    """
    messages = [{
        "role": "user",
        "content": (
            "Research the market for this idea. Use search_web to find real "
            "competitors and market signals, then summarise what you found in a "
            "short paragraph.\n\n"
            f"IDEA: {idea}\nPROBLEM: {analysis.problem}\nAUDIENCE: {analysis.target_audience}"
        ),
    }]

    for _ in range(MAX_SEARCH_ITERATIONS):
        resp = raw_message(MODEL_SMART, messages, tools=[SEARCH_TOOL])
        messages.append({"role": "assistant", "content": resp.content})

        tool_calls = [b for b in resp.content if b.type == "tool_use"]
        if not tool_calls:
            # No more searches requested -> return the model's text summary.
            texts = [b.text for b in resp.content if b.type == "text"]
            return "\n".join(texts) if texts else "No research summary produced."

        # Run each requested search and feed results back to the model.
        results = []
        for call in tool_calls:
            output = search_web(call.input["query"])
            results.append({
                "type": "tool_result",
                "tool_use_id": call.id,
                "content": output,
            })
        messages.append({"role": "user", "content": results})

    # If we exhausted the loop, ask once more for a plain summary.
    messages.append({"role": "user", "content": "Summarise your findings in one short paragraph."})
    resp = raw_message(MODEL_SMART, messages)
    return "".join(b.text for b in resp.content if b.type == "text")


def step4_evaluate(idea: str, analysis: IdeaAnalysis, research: str, kb: list[str]) -> Evaluation:
    kb_block = "\n".join(f"- {c}" for c in kb) if kb else "(no framework context retrieved)"
    prompt = (
        "You are a rigorous startup evaluator. Score the idea 0-10 on each dimension "
        "and give a final verdict (pursue / pivot / drop). Be critical and specific.\n\n"
        f"IDEA: {idea}\n\n"
        f"ANALYSIS:\n- problem: {analysis.problem}\n- audience: {analysis.target_audience}\n"
        f"- solution: {analysis.solution}\n\n"
        f"MARKET RESEARCH:\n{research}\n\n"
        f"EVALUATION FRAMEWORKS (use these to judge):\n{kb_block}"
    )
    data = get_structured(MODEL_SMART, prompt, EVALUATION_TOOL)
    return Evaluation(**data)


def validate_idea(idea: str) -> Evaluation:
    """Run the full pipeline end-to-end."""
    analysis = step1_analyze(idea)
    research = step2_research(idea, analysis)
    kb = retrieve(analysis.problem)
    evaluation = step4_evaluate(idea, analysis, research, kb)
    return evaluation
