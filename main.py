import time
import logging
import uuid 
import json

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from anthropic import Anthropic
from settings import settings
from retrieval import build_prompt, retrieve, generate_answer

app = FastAPI()

logger  =logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    
    request.state.request_id = request_id
    
    response = await call_next(request)
    
    response.headers["X-Request-ID"] = request_id
    
    return response



def get_llm():
    return Anthropic(api_key = settings.anthropic_api_key.get_secret_value())

def cost(usage):
    input_cost=usage.input_tokens / 1_000_000*1
    output_cost=usage.output_tokens / 1_000_000*5
    
    return input_cost + output_cost
    
    
@app.get("/health")
def get_status():
    return {"status": "ok"}


class ChatRequest(BaseModel):
    text: str
    
class ChatResponse(BaseModel):
    reply: str
    
class Classification(BaseModel):
    category: str
    entities: list[str]
    needs_search: bool    
    
    
@app.post("/chat",response_model=ChatResponse)
def chat(msg: ChatRequest, req: Request, client: Anthropic = Depends(get_llm)):
    if not msg.text.strip():
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )
        
    start=time.perf_counter()
    
    res = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=500,
        messages=[
            {
                "role": "user",
                "content": msg.text
            }
        ]
    )
    
    latency=time.perf_counter() - start
    
    req_cost=cost(res.usage)
    
    logger.info(
        json.dumps({
            "request_id": req.state.request_id,
            "endpoint":"/chat",
            "input_tokens": res.usage.input_tokens,
            "output_tokens": res.usage.output_tokens,
            "cost": req_cost,
            "latency_ms": latency * 1000
        })
    )

    
    return {"reply": res.content[0].text}

@app.post("/chat/stream")
def chat_stream(msg: ChatRequest, req: Request, client: Anthropic = Depends(get_llm)):
    if not msg.text.strip():
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )
        
    start=time.perf_counter()
     
    def generate():
        with client.messages.stream(
                model="claude-haiku-4-5",
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": msg.text
                    }
                ]
            ) as stream:
            
            for text in stream.text_stream:
                yield text 
                
            final_message = stream.get_final_message()
        
        latency=time.perf_counter() - start

        req_cost=cost(final_message.usage)
        
        
        logger.info(
                json.dumps({
                    "request_id": req.state.request_id,
                    "endpoint":"/chat/stream",
                    "input_tokens": final_message.usage.input_tokens,
                    "output_tokens": final_message.usage.output_tokens,
                    "cost": req_cost,
                    "latency_ms": latency * 1000
                })
            )
        

    
    return StreamingResponse(
        generate(),
        media_type = "text/plain"
    )
    
    
@app.post("/classify")   
def classify(msg: ChatRequest, req: Request, client: Anthropic = Depends(get_llm)):
    if not msg.text.strip():
            raise HTTPException(
                status_code=400,
                detail="Message cannot be empty"
            )
            
    start=time.perf_counter()
    
    res = client.messages.parse(
        model="claude-haiku-4-5",
        max_tokens=500,
        system=(
            "Classify travel and culture questions. "
            "Set category to one of: city, landmark, museum, culture, nature, other. "
            "Extract the main places, people, or topics as entities. "
            "Set needs_search to true if answering requires external or up-to-date information."
        ),
        messages=[
            {
                "role": "user",
                "content": msg.text
            }
        ],
        output_format=Classification
    )
        
    latency = time.perf_counter() - start
    req_cost = cost(res.usage)
    
    logger.info(
                    json.dumps({
                        "request_id": req.state.request_id,
                        "endpoint":"/classify",
                        "input_tokens": res.usage.input_tokens,
                        "output_tokens": res.usage.output_tokens,
                        "cost": req_cost,
                        "latency_ms": latency * 1000
                    })
                )
                
    
    
    return res.parsed_output

class AskRequest(BaseModel):
    question: str

## מחברת בין השלבים - קוראת ובודקת את השאלה ואח"כ קוראת לretieve, build_prompt ושולחת את הפרומפט לקלוד
## מחזירה תשובה ורשימת מקורות ורושמת בלוג את השימוש בתוקנים, עלות וזמן
@app.post("/ask")
def ask(body: AskRequest, req: Request, llm=Depends(get_llm)):
    started = time.perf_counter()
    question = body.question.strip()
    
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    no_info = "לא מצאתי מידע על זה במקורות"
    chunks = retrieve(question, k=5)
    
    if not chunks:
        return {"answer": no_info, "sources":[]}
    
    answer, usage = generate_answer(question, chunks, llm)
    
    sources = [
                {"title": chunk["title"], "url": chunk["url"]}
                for chunk in chunks
                ]

    logger.info(json.dumps({
        "request_id": req.state.request_id,
        "endpoint": "/ask",
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cost": cost(usage),
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
    }))
    
    return {
        "answer": answer,
        "sources": [] if answer == no_info else sources,
    }
    
        
    