from datetime import date
from anthropic import Anthropic
from settings import settings

client = Anthropic(api_key=settings.anthropic_api_key)

def get_current_date():
    return date.today().isoformat()

tools = [
    {
        "name": "get_current_date",
        "description": "Get the current date.",
        "input_schema": {
            "type" : "object",
            "properties": {},
            "required":[]
        }
        
    }
]

messages = [
    {
        "role": "user",
        "content": "How many days are left until the end of this year?"
    }
]



while True:
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=500,
        tools=tools,
        messages=messages
    )

    print("STOP REASON:", response.stop_reason)
    
    if response.stop_reason == "tool_use":
        print("Claude requested a tool")
        
        tool_use = response.content[0]
        
        if tool_use.name == "get_current_date":
            result = get_current_date()
            print("TOOL RESULT:", result)
            
            
        messages.append({
            "role": "assistant",
            "content": response.content
        })

        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result
                }
            ]
        })
        
    
    else:
        print("FINAL:", response.content)
        break


