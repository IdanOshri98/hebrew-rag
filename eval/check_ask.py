import json
from pathlib import Path

import httpx

NO_INFO = "לא מצאתי מידע על זה במקורות"
golden_path = Path(__file__).with_name("golden.jsonl")

with golden_path.open(encoding="utf-8") as file:
    examples = [json.loads(line) for line in file if line.strip()]
    
if len(examples) != 20:
    raise SystemExit(f"Expected 20 questions, found {len(examples)}")

failures = []
quality_notes = []

with httpx.Client(base_url="http://127.0.0.1:8000", timeout=90.0) as client:
    for number, example in enumerate(examples, start=1):
        question = example["question"]
        
        try:
            response = client.post("/ask", json={"question": question})
            response.raise_for_status()
            data = response.json()
            
            answer = data["answer"]
            sources = data["sources"]
            
            if not isinstance(answer,str) or not answer.strip():
                raise ValueError("Missing or empty answer")
            if not isinstance(sources, list):
                raise ValueError("sources is not a list")
            if any(
                not isinstance(source, dict)
                or not isinstance(source.get("url"), str)
                or not source["url"].strip()
                for source in sources
            ):
                raise ValueError("A source is missing its URL")

            if answer.strip() == NO_INFO:
                if sources:
                    raise ValueError("No-info response returned sources")
                if example["expected_urls"]:
                    quality_notes.append((number, "No answer for a question with known sources"))
            elif not sources:
                raise ValueError("Answer returned without sources")
            elif not example["expected_urls"]:
                quality_notes.append((number, "Answered the out-of-scope question"))

            print(f"{number:02d} OK   | {question}", flush=True)

        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            failures.append(number)
            print(f"{number:02d} FAIL | {question} | {error}", flush=True)

print(f"\nPassed: {len(examples) - len(failures)}/{len(examples)}")
print("Failed questions:", failures)

for number, note in quality_notes:
    print(f"Quality note #{number:02d}: {note}")