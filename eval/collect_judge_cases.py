import json
from pathlib import Path
import time

from anthropic import Anthropic

from retrieval import generate_answer, retrieve
from settings import settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NO_INFO = "לא מצאתי מידע על זה במקורות"



def collect_case(item, llm):
    question = item["question"].strip()
    started = time.perf_counter()
    chunks, embedding_tokens = retrieve(question, k=5, include_usage=True)
     
    if chunks:
        answer, usage = generate_answer(question,chunks,llm)
    else:
        answer = NO_INFO
        usage = None
    
    latency_ms = round((time.perf_counter() - started) * 1000, 2)

    input_tokens = usage.input_tokens if usage else 0
    output_tokens = usage.output_tokens if usage else 0

    cost_usd = (
        embedding_tokens * 0.02
        + input_tokens * 1.00
        + output_tokens * 5.00
    ) / 1_000_000
    
    return {
        "question": question,
        "expected_answer": item["expected_answer"],
        "system_answer": answer,
        "latency_ms": latency_ms,
        "embedding_tokens": embedding_tokens,
        "generation_input_tokens": input_tokens,
        "generation_output_tokens": output_tokens,
        "cost_usd": cost_usd,
        "sources": [
            {
                "number": number,
                "title": chunk["title"],
                "section": chunk["section"],
                "url": chunk["url"],
                "text": chunk["text"],
            }
            for number, chunk in enumerate(chunks, start=1)
        ],
        "human_label": {
            "correctness": None,
            "grounded": None,
            "reason": "",
        },
    }




def main():
    golden_path = PROJECT_ROOT / "eval" / "golden.jsonl"
    
    with golden_path.open(encoding= "utf-8-sig") as file:
        items = [json.loads(line) for line in file if line.strip()]
        
    eligible = [
        item for item in items
        if item.get("lang") == "he" and item.get("expected_answer", "").strip()
    ]
    answerable = [item for item in eligible if item["expected_urls"]]
    fallback = [item for item in eligible if not item["expected_urls"]]
    
    selected = fallback[:1]
    selected += answerable[:20 - len(selected)]
    
    if len(selected) < 20:
        raise SystemExit("Fewer than 20 Hebrew questions have reference answers.")
    
    results_dir = PROJECT_ROOT / "results"
    results_dir.mkdir(exist_ok=True)
    output_path = results_dir / "judge_cases.json"
    
    if output_path.exists():
        raise SystemExit(f"File already exists: {output_path}") 
    
    llm = Anthropic(api_key=settings.anthropic_api_key.get_secret_value())
    cases = []
    
    for number, item in enumerate(selected, start=1):
        print(f"[{number}/20] {item['question']}", flush=True)
        cases.append(collect_case(item, llm))
    
    output_path.write_text(
        json.dumps(cases, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Saved {len(cases)} calibration cases to {output_path}")

if __name__ == "__main__":
    main()
