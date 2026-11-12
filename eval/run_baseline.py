import json
from pathlib import Path
from statistics import mean

from anthropic import Anthropic

from eval.collect_judge_cases import collect_case
from eval.run_judge import judge_case
from settings import settings

ROOT = Path(__file__).resolve().parent.parent


def main():
    golden_path = ROOT / "eval" / "golden.jsonl"
    with golden_path.open(encoding="utf-8-sig") as file:
        items = [json.loads(line) for line in file if line.strip()]

    instructions = (ROOT / "eval" / "judge_prompt.txt").read_text(
        encoding="utf-8-sig"
    )
    llm = Anthropic(api_key=settings.anthropic_api_key.get_secret_value())

    results = []
    for number, item in enumerate(items, start=1):
        print(f"[{number}/{len(items)}] {item['question']}", flush=True)

        expected_answer = item.get("expected_answer") or ""
        case = collect_case({**item, "expected_answer": expected_answer}, llm)
        case.pop("human_label", None)

        expected_urls = set(item["expected_urls"])
        retrieved_urls = [source["url"] for source in case["sources"]]
        matching_ranks = [
            rank
            for rank, url in enumerate(retrieved_urls, start=1)
            if url in expected_urls
        ]

        case["expected_urls"] = item["expected_urls"]
        case["lang"] = item.get("lang")
        case["source"] = item.get("source")
        case["recall_at_5"] = (
            len(expected_urls.intersection(retrieved_urls)) / len(expected_urls)
            if expected_urls
            else None
        )
        case["reciprocal_rank"] = (
            1 / matching_ranks[0] if matching_ranks else 0.0
        ) if expected_urls else None

        case["judge"] = (
            judge_case(case, llm, instructions) if expected_answer.strip() else None
        )
        results.append(case)

    output_path = ROOT / "results" / "baseline_full.jsonl"
    output_path.parent.mkdir(exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for case in results:
            file.write(json.dumps(case, ensure_ascii=False) + "\n")

    scored = [case for case in results if case["recall_at_5"] is not None]
    judged = [case["judge"] for case in results if case["judge"] is not None]
    correct = sum(label["correctness"] == "correct" for label in judged)

    print(f"Recall@5: {mean(case['recall_at_5'] for case in scored):.1%}")
    print(f"MRR@5: {mean(case['reciprocal_rank'] for case in scored):.3f}")
    print(f"Answer accuracy: {correct}/{len(judged)} ({correct / len(judged):.1%})")
    print(f"Average cost per query: ${mean(case['cost_usd'] for case in results):.6f}")
    print(f"Average latency: {mean(case['latency_ms'] for case in results):.0f} ms")
    print(f"Saved {len(results)} rows to {output_path}")


if __name__ == "__main__":
    main()