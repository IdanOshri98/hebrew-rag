import json
import os
from supabase import create_client
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

CHUNKS_PATH = Path("data/chunks.jsonl")
BATCH_SIZE = 100


def load_chunks():
    with CHUNKS_PATH.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


load_dotenv()

client = OpenAI()

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_KEY"]
)

chunks = load_chunks()
total_tokens = 0

for start in range(0, len(chunks), BATCH_SIZE):
    batch = chunks[start:start + BATCH_SIZE]
    texts = [chunk["text"] for chunk in batch]
    
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
        dimensions=1536,
    )

    total_tokens +=  response.usage.total_tokens
        
    rows = []

    for item in response.data:
        chunk = batch[item.index]
        
        rows.append({
            "id": chunk["id"],
            "text": chunk["text"],
            "title": chunk["title"],
            "url": chunk["url"],
            "section": chunk["section"],
            "embedding": item.embedding,
        })
        
    supabase.table("chunks").upsert(rows, on_conflict="id").execute()

    print(f"Saved {start + len(batch)}/{len(chunks)}")

print("Total tokens used:", total_tokens)