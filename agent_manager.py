import os
import toml
import asyncio
from openai import OpenAI
from agents import Agent, FileSearchTool, enable_verbose_stdout_logging, Runner, ItemHelpers

class AgentManager:
    def __init__(self, api_key=None, user=None):
        """Initialize the agent manager"""
        self.client = None
        self.triage_agent = None
        self.agents = {}
        self.user = user
        self.conversation_history = [{"role": "system", "content": "You are a helpful assistant."}]
        # Initialize vector stores
        self.listings_vector_store = None
        self.reviews_vector_store = None
        
        # Load secrets from chainlit/secrets.toml manually, like in main.py
        secrets_path = os.path.join(os.path.dirname(__file__), ".chainlit", "secrets.toml")
        try:
            secrets = toml.load(secrets_path)
        except Exception as e:
            raise RuntimeError(f"Failed to load secrets.toml: {e}")

        # Extract keys, fallback to passed api_key arg
        self.api_key = api_key or secrets.get("openai", {}).get("api_key")
        if not self.api_key or not self.api_key.startswith("sk-"):
            raise ValueError("Missing or invalid OpenAI API key.")

        # Vector store IDs
        vectorstore_section = secrets.get("vectorstore", {})
        self.listings_vector_store = vectorstore_section.get("listings_vector_store_id")
        self.reviews_vector_store = vectorstore_section.get("reviews_vector_store_id")

        if not self.listings_vector_store or not self.reviews_vector_store:
            raise ValueError("Missing vector store IDs in secrets.toml")



    def _ensure_client(self):
        if not self.client:
            os.environ["OPENAI_API_KEY"] = self.api_key
            self.client = OpenAI(api_key=self.api_key)
            print(f"OpenAI client initialized with key starting: {self.api_key[:5]}...")
        return self.client

    def initialize_agents(self):
        self._ensure_client()

        if self.triage_agent:
            return self.triage_agent

        self.agents["listings_agent"] = self._create_listings_agent()
        self.agents["reviews_agent"] = self._create_reviews_agent()

        self.triage_agent = self._create_triage_agent([
            self.agents["listings_agent"],
            self.agents["reviews_agent"]
        ])

        print("Agents initialized successfully")
        return self.triage_agent


    def _create_listings_agent(self):
        return Agent(
            name="Airbnb listings filtering",
            model="gpt-4o",
            instructions="""You are the Listings Agent responsible for retrieving relevant Airbnb listings based on the user's preferences.

Your tasks are:
1. Parse the user's query to extract:
   - Desired location
   - Number of guests
   - Specific preferences (e.g., price range, amenities, property type, etc.)

2. Search through the vector store to identify listings that best match the extracted criteria.

3. Return a list of matching listings, each following this exact structure:
   - **Listing ID** (required)
   - **Name**
   - **Property URL**
   - **Location** (e.g., city, neighborhood, country)
   - **Price** (per night or specified period)
   - **Brief Description** (1–2 lines highlighting the appeal or uniqueness)
   - **Bedrooms**: [number]
   - **Bathrooms**: [number]
   - **Amenities**: [comma-separated list of key features]

4. Always include the all the above details for every single result.

5. Maintain a consistent format across all listings to enhance readability and comparison.

6. If no listings match the criteria, respond politely to the user, let them know no relevant listings were found, and suggest how they can refine or broaden their search.


            """,
            tools=[
                FileSearchTool(vector_store_ids=[self.listings_vector_store])
            ]
        )

    def _create_reviews_agent(self):
        """Create the Review Agent for hotel reviews summarization"""
        return Agent(
            name="Hotel Review Summarization Agent",
            model="gpt-4o",
            instructions="""
You are the Reviews Agent responsible for summarizing the reviews of a specific hotel property.

Your tasks are:
1. Parse the user's query to identify the property the user is asking about. The user may refer to:
   - Property name (e.g., 'Grand Beach Hotel')
   - Listing ID
   - Position in the previous listings (e.g., 'second one')

2. Use the provided `listing_id` or property name to search the reviews vector store for the relevant reviews.

3. Provide a structured summary of the reviews under these headings:
   - **Overall Satisfaction:** Provide a short summary of the general sentiment.
   - **Strengths:** List the key strengths (e.g., "Great location", "Comfortable beds").
   - **Weaknesses:** List the common weaknesses (e.g., "Noisy neighborhood", "Small bathrooms").

4. Provide an aggregated **Recommendation Score (1.0 to 10)** based on overall guest sentiment.

5. Clearly state the **Most Reviews** as either Positive, Negative, or Mixed based on the sentiment distribution.

If no reviews are found or the property cannot be identified, respond politely with:
"Sorry, no reviews are available for this property."
            """,
            tools=[
                FileSearchTool(vector_store_ids=[self.reviews_vector_store])
            ]
        )

    def _create_triage_agent(self, specialized_agents):
        """Create the main triage agent"""
        return Agent(
            name="User query management",
            model="gpt-4o",
            instructions="""You are the triage agent responsible for determining the user's needs. You respond in a friendly Aussie slang.
Your job is to:
1. Identify if the user is asking for information about:
   - Airbnb listings (e.g., searching for properties, finding specific amenities)
   - Reviews (e.g., summarizing reviews for a listing)
     DO NOT answer questions that are:
- Not about travel, tourism, or Airbnb listings
- Related to general knowledge, sports, news, or any unrelated topic
2. Route the user query to the appropriate specialized agent:
   - If the query is about listings (e.g., "Show me available properties in Sydney for 2 adults"), forward it to the Listings Agent.
   - If the query is about reviews (e.g., "What do people say about this property?"), forward it to the Reviews Agent.
3. If the query is unclear or needs further clarification, ask the user for more information before routing the request. If out of topic,
appologise and tell what you are trained to do.

For example:
User Query: "Find me a 2-bedroom apartment in Sydney with a pool."
- This should be routed to the Listings Agent.

User Query: "What are the reviews for this property?"
- This should be routed to the Reviews Agent.
            """,
            handoffs=specialized_agents,
        )

    async def process_user_query(self, user_query):
        try:
            if not self.client:
                self._ensure_client()

            if not self.triage_agent:
                if not self.initialize_agents():
                    yield "Initialization failed."
                    return

            self.conversation_history.append({"role": "user", "content": user_query})

            response = Runner.run_streamed(
                starting_agent=self.triage_agent,
                input=self.conversation_history
            )

            full_response_parts = []

            async for event in response.stream_events():
                if event.type == "run_item_stream_event":
                    item = getattr(event, "item", None)
                    if item and hasattr(item, "raw_item"):
                        content_blocks = getattr(item.raw_item, "content", [])
                        for block in content_blocks:
                            if hasattr(block, "text"):
                                yield block.text
                                full_response_parts.append(block.text)

            full_response = "".join(full_response_parts)
            self.conversation_history.append({"role": "assistant", "content": full_response})

        except Exception as e:
            print(f"Error while processing user query: {e}")
            yield f"Error: {e}"
