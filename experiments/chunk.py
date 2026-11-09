
import re
import json
from pathlib import Path

import tiktoken


MAX_TOKENS = 600
OVERLAP_TOKENS = 50

encoding = tiktoken.get_encoding("cl100k_base")


# ---------- Token utilities ----------

def count_tokens(text):
    return len(encoding.encode(text))


def get_overlap(text, overlap_tokens=OVERLAP_TOKENS):
    if overlap_tokens <= 0:
        return ""

    tokens = encoding.encode(text)
    return encoding.decode(tokens[-overlap_tokens:])


# ---------- Text splitting ----------

def split_by_headings(content):
    sections = []
    current_section = "Introduction"
    current_lines = []

    for line in content.splitlines():
        if line.startswith("## "):
            if current_lines:
                sections.append({
                    "section": current_section,
                    "text": "\n".join(current_lines).strip()
                })

            current_section = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append({
            "section": current_section,
            "text": "\n".join(current_lines).strip()
        })

    return sections


def split_into_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def pack_units(units, max_tokens, separator=" "):
    parts = []
    current = []

    for unit in units:
        candidate = separator.join(current + [unit])

        if count_tokens(candidate) <= max_tokens:
            current.append(unit)
        else:
            if current:
                parts.append(separator.join(current))

            current = [unit]

    if current:
        parts.append(separator.join(current))

    return parts


def split_long_sentence(sentence, max_tokens):
    return pack_units(sentence.split(), max_tokens, " ")


def split_long_paragraph(paragraph, max_tokens):
    units = []

    for sentence in split_into_sentences(paragraph):
        if count_tokens(sentence) > max_tokens:
            units.extend(split_long_sentence(sentence, max_tokens))
        else:
            units.append(sentence)

    return pack_units(units, max_tokens, " ")


# ---------- Chunking ----------

def add_overlap(chunks, max_tokens, overlap_tokens):
    if not chunks:
        return []

    result = [chunks[0]]

    for i in range(1, len(chunks)):
        previous = chunks[i - 1]
        current = chunks[i]

        overlap = get_overlap(previous, overlap_tokens)
        combined = overlap + "\n\n" + current

        while count_tokens(combined) > max_tokens and overlap:
            tokens = encoding.encode(overlap)
            overlap = encoding.decode(tokens[1:])
            combined = overlap + "\n\n" + current

        result.append(combined)

    return result


def split_into_chunks(
    text,
    max_tokens=MAX_TOKENS,
    overlap_tokens=OVERLAP_TOKENS
):
    if not 0 <= overlap_tokens < max_tokens:
        raise ValueError("overlap_tokens must be between 0 and max_tokens")

    content_limit = max_tokens - overlap_tokens
    units = []

    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()

        if not paragraph:
            continue

        if count_tokens(paragraph) > content_limit:
            units.extend(split_long_paragraph(paragraph, content_limit))
        else:
            units.append(paragraph)

    chunks = pack_units(units, content_limit, "\n\n")

    return add_overlap(chunks, max_tokens, overlap_tokens)

def chunk_document(document):
    content = document["content"]

    # Remove embedded MediaWiki chart styles
    content = re.sub(
        r'\.mw-chart-[^\s]*',
        '',
        content
    )

    sections = split_by_headings(content)

    chunks = []

    for section in sections:
        section_chunks = split_into_chunks(section["text"])

        for text in section_chunks:
            chunk = {
                "id": f"{document['pageid']}_{len(chunks)}",
                "text": text,
                "title": document["title"],
                "url": document["url"],
                "section": section["section"],
                "n_tokens": count_tokens(text)
            }

            chunks.append(chunk)

    return chunks

def save_all_chunks(input_dir="data/clean", output_path="data/chunks.jsonl"):
    input_files = sorted(Path(input_dir).glob("*.json"))
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    total_chunks = 0
    total_tokens = 0

    with output_file.open("w", encoding="utf-8") as output:
        for file_path in input_files:
            with file_path.open("r", encoding="utf-8") as file:
                document = json.load(file)

            chunks = chunk_document(document)

            for chunk in chunks:
                output.write(json.dumps(chunk, ensure_ascii=False) + "\n")

                total_chunks += 1
                total_tokens += chunk["n_tokens"]

    average_tokens = total_tokens / total_chunks if total_chunks else 0

    return len(input_files), total_chunks, average_tokens


# ---------- Development check ----------

if __name__ == "__main__":
    documents, total_chunks, average_tokens = save_all_chunks()

    print(f"Documents processed: {documents}")
    print(f"Total chunks: {total_chunks}")
    print(f"Average tokens per chunk: {average_tokens:.1f}")
