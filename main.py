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
        
        

