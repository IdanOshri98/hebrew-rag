import re, json
from pathlib import Path

def clean_text(content):
    content = re.sub(
        r"^(={2,6})[ \t]*([^\n]+?)[ \t]*\1[ \t]*$",
        lambda match: "#" * len(match.group(1)) + " " + match.group(2),
        content,
        flags=re.MULTILINE
    )

    content = remove_unwanted_sections(content)

    content = re.sub(r"\n{3,}", "\n\n", content)

    return content.strip()


def remove_unwanted_sections(content):
    unwanted = {
        "references",
        "external links",
        "see also",
        "further reading",
        "notes",
        "bibliography",
    }

    lines = content.splitlines()
    result = []
    skipping = False

    for line in lines:
        if line.startswith("## "):
            heading = line[3:].strip().lower()
            skipping = heading in unwanted

        if not skipping:
            result.append(line)

    return "\n".join(result)
    
if __name__ == "__main__":
    input_dir = Path("data/raw")
    output_dir = Path("data/clean")
    
    files = list(input_dir.glob("*.json"))

    print(f"Found {len(files)} files")
    
    success = 0
    failed = 0
    
    for input_path in files:
        try:
        
            with input_path.open("r", encoding="utf-8") as file:
                data = json.load(file)

            original_content = data["content"]
            cleaned_content = clean_text(original_content)

            data["content"] = cleaned_content

            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / input_path.name


            with output_path.open("w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)

            success += 1

        except Exception as e:
            failed += 1
            print(f"Failed: {input_path.name} - {e}")
    
    print(f"Successfully cleaned: {success}")
    print(f"Failed: {failed}")