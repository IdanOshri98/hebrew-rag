from settings import settings
from openai import OpenAI
from supabase import create_client
from anthropic import Anthropic

openai_client = OpenAI(
    api_key=settings.openai_api_key.get_secret_value(),
)

supabase = create_client(
    settings.supabase_url,
    settings.supabase_key.get_secret_value(),
)

## מציאת קטעים
## הפונקציה הופכת שאלה לוקטור ומוצאת את חמשת הקטעים בדאטה שהכי קרובים אליו
def retrieve(question, k=5, include_usage=False):
    embedding_res = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=question,
        dimensions=1536
    )
    
    query_embedding = embedding_res.data[0].embedding
    
    search_res = supabase.rpc(
        "match_chunks",
        {
            "query_embedding": query_embedding,
            "match_count": k,
        },
    ).execute()
    
    if include_usage:
        return search_res.data, embedding_res.usage.total_tokens

    return search_res.data

## מכינים את מה שקלוד יקרא
## מקבלת שאלה ואת הקטעים שנשלפו ומחזירה מחרוזתת - הפרומפט. הפרומפט מכיל את ההוראות, השאלה ואת הקטעים ממוספרים.
def build_prompt(question, chunks):
    sources = []
    
    for number, chunk in enumerate(chunks, start=1):
        source = (
            f"[{number}] {chunk['title']} - {chunk['section']}\n"
            f"{chunk['text']}"
        )
        sources.append(source)
        
    context = "\n\n".join(sources)
    
    return f"""ענה בעברית פשוטה על השאלה, על סמך המקורות שלהלן בלבד.
                ליד כל טענה עובדתית ציין את מספר המקור שתומך בה, למשל [2].
                אם חסר מידע על אחד מחלקי השאלה, ציין מה חסר וענה רק על החלקים שהמקורות תומכים בהם.
                אם המקורות לא עונים על אף חלק מהשאלה, החזר רק את המשפט הבא, בלי כותרת, נקודה או טקסט נוסף:
                לא מצאתי מידע על זה במקורות


                שאלה:
                {question}

                מקורות:
                {context}
                """
                
def generate_answer(question, chunks, llm):
    res = llm.messages.create(
        model="claude-haiku-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": build_prompt(question, chunks)}],        
    )
    
    text_parts = [
        block.text for block in res.content if block.type == "text"
    ]
    answer = "".join(text_parts).strip()
    
    return answer, res.usage

if __name__ == "__main__":
    question = "Why was the Colosseum built and what was it used for?"
    chunks = retrieve(question)
    prompt = build_prompt(question, chunks)
    claude = Anthropic(api_key=settings.anthropic_api_key.get_secret_value())
    
    res = claude.messages.create(
        model="claude-haiku-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    
    text_parts = []

    for block in res.content:
        if block.type == "text":
            text_parts.append(block.text)

    answer = "".join(text_parts)
    print(answer)
    print("Stop reason:", res.stop_reason)
    
