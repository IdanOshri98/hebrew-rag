from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel

from anthropic import Anthropic
from settings import settings

app = FastAPI()

def get_llm():
    return Anthropic(api_key = settings.anthropic_api_key)
    
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
    
    return {"reply": res.content[0].text}

