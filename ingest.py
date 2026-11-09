import httpx
import json
import time, re
from pathlib import Path
from datetime import datetime, timezone


API_URL = "https://en.wikipedia.org/w/api.php"

headers = {
    "User-Agent": "HebrewTravelRAG/0.1 (contact: oshriidan1@gmail.com)"
}

OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def safe_filename(title):
    return re.sub(r'[<>:"/\\|?*]', '_', title)

def req_with_retry(params):
    max_retries = 3
    
    for attempt in range(max_retries):
            try:
                response = httpx.get(
                    API_URL,
                    params=params,
                    headers=headers,
                    timeout=20
                )
    
                response.raise_for_status()
                return response
            
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                print(f"Attempt {attempt + 1} failed: {e}")
    
                if attempt == max_retries - 1:
                    return None
    
                wait_time = 2 ** (attempt + 1)
                time.sleep(wait_time)
                
                
    

def fetch_page(title):
    output_path = OUTPUT_DIR / f"{safe_filename(title)}.json"
    
    if output_path.exists():
        return "skipped"
    
    params = {
        "action": "query",
        "prop": "extracts",
        "titles": title,
        "explaintext": 1,
        "format": "json",
        "formatversion": 2
    }
    
    response = req_with_retry(params)
    
    if response is None:
        print(f"Failed to fetch: {title}")
        return "failed"

    data = response.json()
    page_data = data["query"]["pages"][0]
    
    if "missing" in page_data:
        print(f"Page not found: {title}")
        return "failed"

    page_id = page_data["pageid"]
    title = page_data["title"]
    content = page_data.get("extract", "")

    if not content.strip():
        return "empty"

    page = {
        "pageid": page_id,
        "title": title,
        "url": f"https://en.wikipedia.org/?curid={page_data['pageid']}",
        "content": content,
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(page, file, ensure_ascii=False, indent=2)

    return "saved"


def get_category_titles(category, limit=100):
    titles = []
    continue_params = {}

    request_count = 0
    
    while len(titles) < limit:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Category:{category}",
            "cmtype": "page",
            "cmlimit": min(50, limit - len(titles)),
            "format": "json",
            "formatversion": 2,
            **continue_params
        }
        
        
        print(f"Requesting more pages... Already collected: {len(titles)}")

        request_count += 1
        response = req_with_retry(params)
        
        if response is None:
            print(f"Failed to fetch: {category}")
            return "failed"

        data = response.json()

        for page in data["query"]["categorymembers"]:
            titles.append(page["title"])

        if "continue" not in data:
            break

        continue_params = data["continue"]
        
        time.sleep(1)

    print(f"{category}: {len(titles)} titles, {request_count} API requests")
    
    return titles


    
titles = [
    "Madrid", "Barcelona", "Rome", "Paris", "London",
    "Berlin", "Amsterdam", "Lisbon", "Prague", "Vienna",
    "Budapest", "Athens", "Istanbul", "Tokyo", "Kyoto",
    "Eiffel Tower", "Colosseum", "Sagrada Família", "Louvre",
    "Buckingham Palace", "Acropolis of Athens", "Trevi Fountain", "Brandenburg Gate", "Tower of London",
    "Palace of Versailles", "Pantheon, Rome", "Alhambra", "Park Güell", "Royal Palace of Madrid",
    "Renaissance", "Spanish cuisine", "Italian cuisine", "French cuisine", "Flamenco",
    "Roman Empire", "Ancient Greece", "Japanese tea ceremony", "Oktoberfest", "Carnival of Venice",
    "Grand Canyon", "Mount Fuji", "Santorini", "Amalfi Coast", "Swiss Alps",
    "Banff National Park", "Machu Picchu", "Great Barrier Reef", "Petra", "Iguazu Falls"
]


stats = {
    "saved": 0,
    "skipped": 0,
    "failed": 0,
    "empty": 0
}


if __name__ == "__main__":
    
    categories = {
        "Museums in Madrid": 30,
        "Museums in Barcelona": 30,
        "Tourist attractions in Paris": 50,
        "Tourist attractions in Rome": 50,
        "Tourist attractions in London": 50,
        "Museums in Paris": 50,
        "Museums in London": 50,
        "Tourist attractions in Berlin": 50,
        "Tourist attractions in Amsterdam": 50,
        "Museums in Rome": 50
    }


    all_titles = set(titles)

    for category, limit in categories.items():
        print(f"\nFetching category: {category}")

        category_titles = get_category_titles(category, limit)
        
        if category_titles is None:
            continue

        all_titles.update(category_titles)

    print(f"\nTotal unique titles: {len(all_titles)}")
    
    titles_to_ingest = sorted(all_titles)
    total = len(titles_to_ingest)


    for index, title in enumerate(titles_to_ingest, start=1):
        status = fetch_page(title)
        stats[status] += 1
        
        if index % 25 == 0 or index == total:
            print(
                f"Progress: {index}/{total} | "
                f"Saved: {stats['saved']} | "
                f"Skipped: {stats['skipped']} | "
                f"Failed: {stats['failed']} | "
                f"Empty: {stats['empty']}"
            )

        if status != "skipped":
            time.sleep(0.5)
        

    print("\nIngestion finished!")
    print(f"Saved: {stats['saved']}")
    print(f"Skipped: {stats['skipped']}")
    print(f"Failed: {stats['failed']}")
    print(f"Empty: {stats['empty']}")

