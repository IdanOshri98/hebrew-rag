import time

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from anthropic import Anthropic
from settings import settings

app = FastAPI()

def get_llm():
    return Anthropic(api_key = settings.anthropic_api_key)

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
def chat(msg: ChatRequest, client: Anthropic = Depends(get_llm)):
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
    
    print("======== METRICS ========")
    print(
        f"input={res.usage.input_tokens}, "
        f"output={res.usage.output_tokens}, "
        f"cost={req_cost:.6f}, "
        f"latency={latency:.2f}s"
    )

    
    return {"reply": res.content[0].text}

@app.post("/chat/stream")
def chat_stream(msg: ChatRequest, client: Anthropic = Depends(get_llm)):
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
        
        print("======== METRICS ========")
        print(
            f"input={final_message.usage.input_tokens}, "
            f"output={final_message.usage.output_tokens}, "
            f"cost=${req_cost:.6f}, "
            f"latency={latency:.2f}s"
        )

    
    return StreamingResponse(
        generate(),
        media_type = "text/plain"
    )
    
    
@app.post("/classify")   
def classify(msg: ChatRequest, client: Anthropic = Depends(get_llm)):
    if not msg.text.strip():
            raise HTTPException(
                status_code=400,
                detail="Message cannot be empty"
            )
    
    res = client.messages.parse(
        model="claude-haiku-4-5",
        max_tokens=500,
        system=
            "You are a classifier for hebrew questions."
             "Define a catagory such as work, health, housing, studies, finance, etc."
             "entities are the main terms or  organizations mentioned in the question."
             "need_search should be true if external or up-to-date information is needed to answer the question.",
        messages=[
            {
                "role": "user",
                "content": msg.text
            }
        ],
        output_format=Classification
    )
    
    return res.parsed_output
    
        
    