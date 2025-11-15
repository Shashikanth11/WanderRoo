# setup_vectorstore.py
import os
import toml
from openai import OpenAI
from vector import VectorStoreManager

def load_api_key_from_secrets():
    """Load OpenAI API key from .streamlit/secrets.toml"""
    secrets_path = os.path.join(".chainlit", "secrets.toml")
    if not os.path.exists(secrets_path):
        raise FileNotFoundError("Could not find '.chainlit/secrets.toml'. Please create it with your OpenAI key.")

    secrets = toml.load(secrets_path)
    return secrets.get("openai", {}).get("api_key", None)

def main():
    print("🔑 Loading OpenAI API key from secrets.toml...")
    api_key = load_api_key_from_secrets()
    if not api_key:
        raise ValueError("Missing OpenAI API key in secrets.toml under [openai] section.")

    print("⚙️ Initializing OpenAI client...")
    client = OpenAI(api_key=api_key)

    print("📦 Setting up Airbnb vector stores...")
    manager = VectorStoreManager(client=client)
    manager.set_airbnb_vector_stores()

    print("✅ Vector stores setup complete.")

if __name__ == "__main__":
    main()
