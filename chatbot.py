import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from models import save_lead
from typing import TypedDict, Annotated
import operator
import json

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

class LeadState(TypedDict):
    messages: Annotated[list, operator.add]
    property_type: str | None
    budget: str | None
    location: str | None
    name: str | None
    email: str | None
    phone: str | None
    lead_saved: bool


SYSTEM_PROMPT = """You are RealAI, a warm and experienced real estate consultant who genuinely cares about helping people find their dream home.

🎯 YOUR PERSONALITY:
- Enthusiastic but not pushy - you're excited to help, not desperate to sell
- Conversational and relatable - talk like a friendly human, not a robot
- Use casual language, contractions (I'm, you're, that's), and occasional emojis
- Show empathy - acknowledge their needs, budget constraints, and preferences
- Ask follow-up questions naturally - "Oh, that's a great area!" or "Smart budget planning!"
- Don't just collect info robotically - BUILD RAPPORT

💬 HOW TO TALK:
- Start warm: "Hey there! I'm RealAI 😊" or "Hi! Excited to help you find the perfect place!"
- React to their answers: "Ooh, a house! Great choice for families" or "Chennai! Love that city"
- Be encouraging: "You're doing great!" or "Almost there, just a couple more things"
- Use variety - don't repeat the same phrases
- Keep it SHORT - 1-2 sentences max per response
- Sound natural: "What's your budget looking like?" instead of "Please provide your budget range"

📝 INFO TO COLLECT (but don't make it feel like an interrogation):
1. Property type - "What kind of place are you looking for?"
2. Budget - "What's your budget range?" or "How much are you thinking?"
3. Location - "Which area/city interests you?"
4. Name - "By the way, what should I call you?" or "And you are...?"
5. Email - "What's your email so I can send you listings?"
6. Phone - "Best number to reach you at?"

🚫 DON'T:
- Sound robotic or formal
- Ask multiple questions at once
- Use phrases like "Could you please provide" or "I require"
- Ignore what they said
- Be too long-winded

✅ DO:
- React to their answers naturally
- Use their name once you know it
- Be conversational and warm
- Keep responses brief and engaging
- Show personality!

Remember: You're a human real estate agent having a chat, not a form-filling bot!"""

def chatbot(state: LeadState):
    """Main chatbot node - responds and extracts in ONE step"""
    
    # Check what we still need
    needed = []
    if not state.get("property_type"): needed.append("property type")
    if not state.get("budget"): needed.append("budget")
    if not state.get("location"): needed.append("location")
    if not state.get("name"): needed.append("name")
    if not state.get("email"): needed.append("email")
    if not state.get("phone"): needed.append("phone")
    
    # If we have everything, just thank them
    if not needed:
        return {
            "messages": [AIMessage(content="Thank you! I have all your information. Let me save this for you.")]
        }
    
    # Build context
    context = f"""
Already collected:
- Property type: {state.get('property_type') or 'NOT YET'}
- Budget: {state.get('budget') or 'NOT YET'}
- Location: {state.get('location') or 'NOT YET'}
- Name: {state.get('name') or 'NOT YET'}
- Email: {state.get('email') or 'NOT YET'}
- Phone: {state.get('phone') or 'NOT YET'}

Still need: {', '.join(needed)}
"""
    
    # Get last user message
    last_user_msg = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_user_msg = msg.content
            break
    
    # EXTRACT from the last user message
    extracted = {}
    if last_user_msg:
        extract_prompt = f"""From this user message, extract any lead information.
User said: "{last_user_msg}"

Return JSON only:
{{
  "property_type": "type or null",
  "budget": "amount or null", 
  "location": "place or null",
  "name": "name or null",
  "email": "email or null",
  "phone": "phone or null"
}}"""
        
        try:
            extract_result = llm.invoke([SystemMessage(content=extract_prompt)])
            content = extract_result.content.strip()
            if "```" in content:
                content = content.split("```")[1].replace("json", "").strip()
            extracted = json.loads(content)
            print(f"✓ Extracted from '{last_user_msg}': {extracted}")
        except Exception as e:
            print(f"✗ Extract error: {e}")
            extracted = {}
    
    # Generate response
    messages_for_llm = [
        SystemMessage(content=SYSTEM_PROMPT),
        SystemMessage(content=context),
        *state["messages"][-6:]
    ]
    
    response = llm.invoke(messages_for_llm)
    print(f"→ Bot: {response.content[:100]}")
    
    # Return updates
    return {
        "messages": [AIMessage(content=response.content)],
        "property_type": extracted.get("property_type") or state.get("property_type"),
        "budget": extracted.get("budget") or state.get("budget"),
        "location": extracted.get("location") or state.get("location"),
        "name": extracted.get("name") or state.get("name"),
        "email": extracted.get("email") or state.get("email"),
        "phone": extracted.get("phone") or state.get("phone"),
    }

def save_node(state: LeadState):
    """Save to database"""
    try:
        save_lead({
            "property_type": state["property_type"],
            "budget": state["budget"],
            "location": state["location"],
            "name": state["name"],
            "email": state["email"],
            "phone": state["phone"],
        })
        from google_sheets import save_to_google_sheets
        save_to_google_sheets({
            "property_type": state["property_type"],
            "budget": state["budget"],
            "location": state["location"],
            "name": state["name"],
            "email": state["email"],
            "phone": state["phone"],
        })
        print("✓ Saved to database!")
        return {
            "messages": [AIMessage(content="Perfect! Your information has been saved. Our team will reach out within 24 hours!")],
            "lead_saved": True
        }
    except Exception as e:
        print(f"✗ DB Error: {e}")
        return {"messages": [AIMessage(content="Got your info! We'll be in touch soon.")]}

def route_decision(state: LeadState):
    """Simple router"""
    complete = all([
        state.get("property_type"),
        state.get("budget"),
        state.get("location"),
        state.get("name"),
        state.get("email"),
        state.get("phone")
    ])
    
    if complete and not state.get("lead_saved"):
        print("→ COMPLETE - Saving...")
        return "save"
    else:
        # Always END after chatbot responds - wait for next user message
        print("→ Waiting for user response")
        return "end"

# Build simple graph
workflow = StateGraph(LeadState)

workflow.add_node("chat", chatbot)
workflow.add_node("save", save_node)

workflow.set_entry_point("chat")

workflow.add_conditional_edges(
    "chat",
    route_decision,
    {
        "save": "save",  # All fields collected, save it
        "end": END       # Wait for next user message
    }
)

workflow.add_edge("save", END)

graph_app = workflow.compile()