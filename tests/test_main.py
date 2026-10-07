from fastapi.testclient import TestClient

from main import app, get_llm, Classification


client = TestClient(app)

class FakeTextBlock:
    text = "FAKE Claude response"

class FakeUsage:
    input_tokens = 10
    output_tokens = 20

class FakeRes:
    usage = FakeUsage()
    content = [FakeTextBlock()]
    
class FakeParseRes:
    parsed_output = Classification(
        category="general",
        entities=["Python"],
        needs_search=False
    )
    
class FakeMessages:
    def create(self, **kwargs):
        return FakeRes()
    
    def parse(self,**kwargs):
        return FakeParseRes()
        

class FakeLLM:
    def __init__(self):
        self.messages = FakeMessages()
        

def fake_get_llm():
    return  FakeLLM()


app.dependency_overrides[get_llm] = fake_get_llm


def test_chat():
    response = client.post(
        "/chat",
        json={"text": "Hello"}
    )
    
    assert response.status_code == 200
    assert response.json() == {"reply": "FAKE Claude response"}
    
    
def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_empty_message():
    response = client.post(
        "/chat",
        json={"text": "   "}
    )

    assert response.status_code == 400
    
def test_chat_empty_string():
    res = client.post(
        "/chat",
        json={"text":""}
    )
    
    assert res.status_code == 400
    
def test_chat_missing_text():
    res = client.post(
        "/chat",
        json = {}
    )
    
    assert res.status_code == 422

def test_classify():
    res = client.post(
        "/classify",
        json={"text": "How do I use Python?"}
    )
    
    assert res.status_code == 200
    assert res.json() == {
                    "category": "general",
                    "entities": ["Python"],
                    "needs_search": False
    }
