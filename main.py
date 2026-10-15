
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="LexAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "LexAI backend is running!"
    }


@app.post("/api/chat")
def chat(data: dict):
    message = data.get("message", "")

    return {
        "reply": f"LexAI received your question: {message}"
    } 