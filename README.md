# WanderRoo — Sydney Airbnb Chatbot

A Chainlit-powered assistant that helps you find the best Airbnb stays in Sydney and summarises guest reviews in real time.

---

## 🚀 Quick-start

### 1. Clone the repo

```bash
git clone https://github.com/your-org/wanderroo.git
cd wanderroo
```

### 2. Add your secrets

Create a **`.chainlit`** folder in the project root and drop a `secrets.toml` file inside it:

```toml
# .chainlit/secrets.toml
[openai]
api_key = "sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXX"

[vectorstore]
listings_vector_store_id = "vs_…"
reviews_vector_store_id  = "vs_…"
```

*You can obtain the vector-store IDs by running the ingestion script once (see below) or from the OpenAI dashboard.*

### 3. (Optional) Ingest or refresh the vector stores

If you have new or updated listings/reviews data, run:

```bash
python setup_vectorstore.py
```

The script converts each JSON row into a text file, embeds it (1 536-D), and uploads it to the “Airbnb Listings” and “Airbnb Reviews” vector stores.
It keeps an upload log so re-runs are idempotent.

### 4. Create a virtual environment & install deps

```bash
python3 -m venv pyenv
source pyenv/bin/activate
pip install -r requirements.txt
```

### 5. Launch the chatbot

```bash
chainlit run app.py
```

Open the link printed in your terminal (usually [http://localhost:8000](http://localhost:8000)) and start chatting! 🚦
Ask things like **“Show me a 2-bedroom flat in Bondi with ocean views under \$400 a night”** or **“What do people say about listing 12345678?”**

---

## 🗂️ Project layout

| Path / File              | Purpose                                                                    |
| ------------------------ | -------------------------------------------------------------------------- |
| `app.py`                 | Chainlit entry point; streams chat and routes queries to agents            |
| `agent_manager.py`       | Defines the Triage, Listings, and Reviews agents                           |
| `vector.py`              | Converts JSON → text, embeds, and uploads documents to OpenAI vector store |
| `setup_vectorstore.py`   | One-off / CI script that calls `vector.py` to populate the vector stores   |
| `data/`                  | Raw CSVs, cleaned JSONs, and generated `.txt` files                        |
| `.chainlit/secrets.toml` | **Never commit this!** Holds your API key and vector store IDs             |
| `requirements.txt`       | Python package list                                                        |

---


## 🔒 Security notes

* API key is read **once** from `secrets.toml`—never logged or exposed client-side.
* Agents have **read-only** vector-store access; only the ingestion script can write.
* Guardrails in the triage agent politely refuse off-topic questions.
* CI pipeline runs `bandit`, `safety`, and Dependabot to catch vulnerabilities.

---

Happy hosting, and enjoy your time in sunny Sydney! 🌞🦘
