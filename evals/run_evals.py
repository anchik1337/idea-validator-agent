"""
Evaluation harness. THIS FILE IS YOUR INTERVIEW WEAPON.

It measures the two things that matter for an LLM system:
  1. Structured-output validity  -> did every response match the schema? (target: 100%)
  2. Verdict accuracy            -> did the agent's verdict match the human label?

Run it:  python evals/run_evals.py            (full set, costs API calls)
         python evals/run_evals.py 8          (first 8 cases only, cheaper while iterating)

On an interview you say: "I built a labeled eval set of 30 cases and measure schema
validity and verdict accuracy on every change, so I know when a prompt tweak helps
or hurts instead of guessing."
"""

import sys, os, json
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

from dotenv import load_dotenv
load_dotenv()

from pydantic import ValidationError
from app.agent import validate_idea
from app.schema import Evaluation


def load_dataset():
    path = os.path.join(os.path.dirname(__file__), "dataset.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run(limit=None):
    data = load_dataset()
    if limit:
        data = data[:limit]

    total = len(data)
    valid_schema = 0
    correct_verdict = 0
    failures = []

    for i, case in enumerate(data, 1):
        idea, expected = case["idea"], case["expected"]
        try:
            result: Evaluation = validate_idea(idea)   # Pydantic already validated shape
            valid_schema += 1
            hit = result.verdict == expected
            correct_verdict += int(hit)
            mark = "OK " if hit else "XX "
            print(f"{mark}[{i}/{total}] got={result.verdict:6} expected={expected:6} | {idea[:55]}")
            if not hit:
                failures.append((idea, expected, result.verdict))
        except (ValidationError, ValueError, Exception) as e:
            print(f"ERR [{i}/{total}] schema/agent failure: {e} | {idea[:55]}")
            failures.append((idea, expected, f"ERROR: {e}"))

    print("\n================ EVAL REPORT ================")
    print(f"Schema validity : {valid_schema}/{total} = {valid_schema/total*100:.0f}%")
    print(f"Verdict accuracy: {correct_verdict}/{total} = {correct_verdict/total*100:.0f}%")
    if failures:
        print("\nMismatches to inspect:")
        for idea, exp, got in failures:
            print(f"  - expected {exp}, got {got}: {idea[:60]}")


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run(limit)
