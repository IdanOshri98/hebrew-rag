import json
from pathlib import Path

from anthropic import Anthropic

from settings import settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORRECTNESS_LABELS = ("correct", "partial", "incorrect")


def valid_label(label):
    return (
        isinstance(label, dict)
        and label.get("correctness") in CORRECTNESS_LABELS
        and type(label.get("grounded")) is bool
    )


def judge_case(case, llm, instructions):
    fields = ("question", "expected_answer", "system_answer", "sources")
    judge_input = {field: case[field] for field in fields}

    response = llm.messages.create(
        model="claude-haiku-4-5",
        max_tokens=500,
        system=instructions,
        messages=[
            {"role": "user", "content": json.dumps(judge_input, ensure_ascii=False)}
        ],
    )

    text = "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()

    if text.startswith("```") and text.endswith("```"):
        text = "\n".join(text.splitlines()[1:-1]).strip()

    judge = json.loads(text)
    
    if isinstance(judge, dict):
        grounded = judge.get("grounded")
        if grounded in ("true", "false"):
            judge["grounded"] = grounded == "true"
        
    if not valid_label(judge) or not isinstance(judge.get("reason"), str):
        raise ValueError(f"Invalid judge output: {text}")

    return judge


def main():
    case_path = PROJECT_ROOT / "results" / "judge_cases.json"
    prompt_path = PROJECT_ROOT / "eval" / "judge_prompt.txt"

    cases = json.loads(case_path.read_text(encoding="utf-8-sig"))
    instructions = prompt_path.read_text(encoding="utf-8-sig")

    if not isinstance(cases, list) or len(cases) != 20:
        raise SystemExit("Expected a JSON array with 20 calibration cases.")

    for number, case in enumerate(cases, start=1):
        if not valid_label(case.get("human_label")):
            raise SystemExit(f"Case {number} has a missing or invalid human label.")

    llm = Anthropic(api_key=settings.anthropic_api_key.get_secret_value())
    total = len(cases)
    correctness_matches = 0
    grounded_matches = 0
    full_matches = 0

    for number, case in enumerate(cases, start=1):
        print(f"[{number}/{total}] {case['question']}", flush=True)
        human = case["human_label"]
        judge = judge_case(case, llm, instructions)

        correctness_match = judge["correctness"] == human["correctness"]
        grounded_match = judge["grounded"] == human["grounded"]

        correctness_matches += int(correctness_match)
        grounded_matches += int(grounded_match)

        if correctness_match and grounded_match:
            full_matches += 1
        else:
            print("  Human:", json.dumps(human, ensure_ascii=False))
            print("  Judge:", json.dumps(judge, ensure_ascii=False))

    print(f"Correctness agreement: {correctness_matches}/{total} ({correctness_matches / total:.0%})")
    print(f"Groundedness agreement: {grounded_matches}/{total} ({grounded_matches / total:.0%})")
    print(f"Full agreement: {full_matches}/{total} ({full_matches / total:.0%})")


if __name__ == "__main__":
    main()