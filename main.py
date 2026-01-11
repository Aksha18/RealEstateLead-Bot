from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict
from langchain_core.messages import HumanMessage
from fastapi.middleware.cors import CORSMiddleware
from chatbot import graph_app, LeadState
import uvicorn

app = FastAPI()

# Store states per session
sessions: Dict[str, LeadState] = {}

class Lead(BaseModel):
    name: str
    email: str
    phone: str
    property_type: str
    budget: str
    location: str

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

@app.post("/chat/")
async def chat_endpoint(payload: ChatRequest):
    # Get or create session state
    if payload.session_id not in sessions:
        sessions[payload.session_id] = {
            "messages": [],
            "property_type": None,
            "budget": None,
            "location": None,
            "name": None,
            "email": None,
            "phone": None,
            "lead_saved": False
        }
    
    state = sessions[payload.session_id]
    
    # DON'T add message here - let the graph handle it via invoke input
    # This is the key fix!
    
    # Invoke with the NEW message as input
    updated_state = graph_app.invoke({
        **state,
        "messages": state["messages"] + [HumanMessage(content=payload.message)]
    })
    
    # Save the updated state
    sessions[payload.session_id] = updated_state
    
    # Get the last AI message
    ai_messages = [m for m in updated_state["messages"] if hasattr(m, 'content')]
    bot_reply = ai_messages[-1].content if ai_messages else "Sorry, something went wrong."
    
    return {
        "reply": bot_reply,
        "lead_complete": updated_state.get("lead_saved", False),
        "collected": {
            "property_type": updated_state.get("property_type"),
            "budget": updated_state.get("budget"),
            "location": updated_state.get("location"),
            "name": updated_state.get("name"),
            "email": updated_state.get("email"),
            "phone": updated_state.get("phone")
        }
    }

@app.post("/reset/")
async def reset_session(session_id: str = "default"):
    if session_id in sessions:
        del sessions[session_id]
    return {"status": "session reset"}

@app.get("/")
async def root():
    return {"message": "Real Estate Lead Bot API", "endpoints": ["/chat/", "/reset/"]}


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)