import argparse 
import json
from pathlib import Path
from statistics import mean

from retrieval import retrieve

TOP_K = 5
PROJECT_ROOT = Path(__file__).resolve().parent.parent

def score_question(item):
    chunks = retrieve(item["question"], k=TOP_K)
    retrieved_urls = [chunk["url"] for chunk in chunks]
    expected_urls = set(item["expected_urls"])
    
    first_rank = next(
        (rank for rank, url in enumerate(retrieved_urls, start=1)
        if url in expected_urls),
        None,
    )
    
    found_urls = expected_urls.intersection(retrieved_urls)
    
    return {
        "question": item["question"],
        "source": item.get("source") or "unknown",
        "lang": item.get("lang") or "unknown",
        "expected_urls": item["expected_urls"],
        "retrieved_urls": retrieved_urls,
        "first_rank": first_rank,
        "recall_at_5": len(found_urls) / len(expected_urls) if expected_urls else None,
        "hit_at_5": int(first_rank is not None) if expected_urls else None,
        "reciprocal_rank": (
            1 / first_rank if first_rank else 0.0
        ) if expected_urls else None,
    }
    
def print_summary(label, rows):
    scored = [row for row in rows if row["recall_at_5"] is not None]
    if not scored:
        print(f"{label}: n=0")
        return
    
    recall = mean(row["recall_at_5"] for row in scored)
    hit_rate = mean(row["hit_at_5"] for row in scored)
    mrr = mean(row["reciprocal_rank"] for row in scored)
    
    print(
        f"{label}: n={len(scored)} | Recall@5={recall:.1%} | "
        f"Hit@5={hit_rate:.1%} | MRR@5={mrr: 3f}"
    )
    


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", choices=["baseline"], required=True)
    parser.add_argument("--limit", type=int, help="Evaluate only the first N questions.")
    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")

    golden_path = PROJECT_ROOT / "eval" / "golden.jsonl"
    with golden_path.open(encoding="utf-8-sig") as file:
        questions = [json.loads(line) for line in file if line.strip()]

    results_dir = PROJECT_ROOT / "results"
    results_dir.mkdir(exist_ok=True)
    output_name = args.config
    if args.limit is not None:
        questions = questions[:args.limit]
        output_name = f"{args.config}_smoke"

    output_path = results_dir / f"{output_name}.jsonl"
    results = []

    with output_path.open("w", encoding="utf-8") as file:
        for index, item in enumerate(questions, start=1):
            print(f"[{index}/{len(questions)}] {item['question']}", flush=True)
            row = score_question(item)
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
            results.append(row)

    print_summary("overall", results)

    for field in ("source", "lang"):
        for value in sorted({row[field] for row in results}):
            group = [row for row in results if row[field] == value]
            print_summary(f"{field}={value}", group)

    print(f"Saved {len(results)} rows to {output_path}")
    

if __name__ == "__main__":
    main()
    