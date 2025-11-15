import os
import toml
import chainlit as cl
from agent_manager import AgentManager
import openai
import asyncio

# --- 🔐 Load OpenAI API key from chainlit/secrets.toml ---
secrets_path = os.path.join(os.path.dirname(__file__), ".chainlit", "secrets.toml")

try:
    secrets = toml.load(secrets_path)
    API_KEY = secrets.get("openai", {}).get("api_key")
    if not API_KEY or not API_KEY.startswith("sk-"):
        raise ValueError("Missing or invalid OpenAI API key.")
    openai.api_key = API_KEY
except Exception as e:
    raise RuntimeError(f"❌ Failed to load OpenAI API key: {e}")

# --- 🦘 On Chat Start ---
@cl.on_chat_start
async def start():
    cl.user_session.set("messages", [
        {
            "role": "assistant",
            "content": "G'day mate! I'm WanderRoo, your local guide to the best stays in Sydney 🏖️. What kind of getaway are ya planning today?"
        }
    ])
    cl.user_session.set("agent_manager", AgentManager(api_key=openai.api_key))

    # Show a bold custom title using HTML
    await cl.Message(
        content="""
        <div style="text-align: center; margin-bottom: 1em;">
            <h1 style="font-size: 3em; font-weight: bold;">🦘 WanderRoo</h1>
            <p style="font-size: 1.2em;">Plan Your Dream Sydney Stay 🏡</p>
        </div>
        """
    ).send()
    

    await cl.Message(content=cl.user_session.get("messages")[0]["content"]).send()

# --- 💬 On User Message ---
@cl.on_message
async def handle_message(message: cl.Message):
    messages = cl.user_session.get("messages")
    messages.append({"role": "user", "content": message.content})

    response_parts = []
    agent_manager = cl.user_session.get("agent_manager")
    response_message = cl.Message(content="")
    await response_message.send()

    async for part in agent_manager.process_user_query(message.content):
        response_parts.append(part)
        await response_message.stream_token(part)

    full_response = ''.join(response_parts)
    messages.append({"role": "assistant", "content": full_response})
