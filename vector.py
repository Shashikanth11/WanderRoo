import os
import json
import re
import streamlit as st
import ast  # for safely parsing stringified lists

class VectorStoreManager:
    
    def __init__(self, client):
        self.client = client

    def set_airbnb_vector_stores(self):
        """Setting Airbnb Listings and Reviews knowledge base"""
        print("In set_airbnb_vector_stores")

        if not self._ensure_client():
            return None

        listing_vector_store = None
        review_vector_store = None

        try:
            # Listings
            listing_vector_store = st.session_state.get("airbnb_listing_vector_store", None)
            if not listing_vector_store:
                print("Checking Listing Vector Store...")
                listing_vector_stores = self.client.vector_stores.list()
                if listing_vector_stores and listing_vector_stores.data:
                    for vs in listing_vector_stores.data:
                        if vs.name == 'Airbnb Listings':
                            listing_vector_store = vs
                            st.session_state["airbnb_listing_vector_store"] = listing_vector_store
                            break
                if not listing_vector_store:
                    print("Creating new Airbnb Listings vector store...")
                    listing_vector_store = self.client.vector_stores.create(name="Airbnb Listings")
                    st.session_state["airbnb_listing_vector_store"] = listing_vector_store
                    print(f"Created Airbnb Listings vector store with ID: {listing_vector_store.id}")

            # Reviews
            review_vector_store = st.session_state.get("airbnb_review_vector_store", None)
            if not review_vector_store:
                print("Checking Review Vector Store...")
                review_vector_stores = self.client.vector_stores.list()
                if review_vector_stores and review_vector_stores.data:
                    for vs in review_vector_stores.data:
                        if vs.name == 'Airbnb Reviews':
                            review_vector_store = vs
                            st.session_state["airbnb_review_vector_store"] = review_vector_store
                            break
                if not review_vector_store:
                    print("Creating new Airbnb Reviews vector store...")
                    review_vector_store = self.client.vector_stores.create(name="Airbnb Reviews")
                    st.session_state["airbnb_review_vector_store"] = review_vector_store
                    print(f"Created Airbnb Reviews vector store with ID: {review_vector_store.id}")

            # Upload Files
            self._upload_files(listing_vector_store, "listings")
            self._upload_files(review_vector_store, "reviews")

        except Exception as e:
            print(f"Error creating/checking vector stores: {e}")
            st.error(f"Failed to setup Airbnb vector stores: {str(e)}")
            return None

    def _upload_files(self, vector_store, data_type):
        """Upload files to a specific vector store (listings or reviews) and skip already uploaded ones."""
        print(f"Uploading files for {data_type}...")

        kb_text_path = f'data/{data_type}_files'
        os.makedirs(kb_text_path, exist_ok=True)

        if not os.path.exists(kb_text_path) or not any(os.path.isfile(os.path.join(kb_text_path, f)) for f in os.listdir(kb_text_path)):
            print(f"Converting {data_type} JSON to text files...")
            self._convert_json_to_text_airbnb(data_type)

        uploaded_log_path = f'data/{data_type}_uploaded_files.json'
        if os.path.exists(uploaded_log_path):
            with open(uploaded_log_path, 'r') as f:
                uploaded_files = set(json.load(f))
        else:
            uploaded_files = set()

        file_count = 0
        for filename in os.listdir(kb_text_path):
            if filename in uploaded_files:
                print(f"Skipping already uploaded file: {filename}")
                continue

            file_path = os.path.join(kb_text_path, filename)
            if os.path.exists(file_path):
                try:
                    with open(file_path, "rb") as file:
                        print(f"Uploading file: {filename}")
                        file_batch = self.client.vector_stores.file_batches.upload_and_poll(
                            vector_store_id=vector_store.id,
                            files=[file]
                        )
                        uploaded_files.add(filename)
                        file_count += 1
                        print(f"Uploaded {filename} - Status: {file_batch.status}")
                except Exception as e:
                    print(f"Error uploading {filename}: {e}")

        with open(uploaded_log_path, 'w') as f:
            json.dump(list(uploaded_files), f)

        print(f"Upload complete for {data_type}. Total new files uploaded: {file_count}")

    def _convert_json_to_text_airbnb(self, data_type):
        """Convert Airbnb Listings or Reviews JSON to individual text files with metadata"""
        try:
            if data_type == "listings":
                json_file = 'data/sydney_listings.json'
                kb_text_path = 'data/listings_files'
            elif data_type == "reviews":
                json_file = 'data/sydney_reviews.json'
                kb_text_path = 'data/reviews_files'
            else:
                print("Invalid data type specified.")
                return

            with open(json_file, 'r') as f:
                data = [json.loads(line) for line in f]

            os.makedirs(kb_text_path, exist_ok=True)

            for idx, entry in enumerate(data):
                if data_type == "listings":
                    metadata = entry.get("metadata", {})
                    entry_id = str(entry.get("id", f"unknown_{idx}"))
                    name = entry.get("name", "No Title")
                    url = entry.get("listing_url", f"https://www.airbnb.com/rooms/{entry_id}")
                    description = entry.get("description", "No description")
                    neighborhood = entry.get("neighbourhood_cleansed", "Unknown neighborhood")
                    property_type = entry.get("property_type", "Unknown property type")
                    room_type = entry.get("room_type", "Unknown room type")
                    accommodates = entry.get("accommodates", "Unknown")
                    price = entry.get("price", "No price provided")
                    amenities_raw = entry.get("amenities", "[]")
                    try:
                        amenities_list = ast.literal_eval(amenities_raw)
                    except Exception:
                        amenities_list = [amenities_raw]
                    amenities_str = ", ".join(amenities_list)

                    num_reviews = entry.get("number_of_reviews", 0)
                    availability = entry.get("availability_365", 0)
                    bedrooms = entry.get("bedrooms", "N/A")
                    beds = entry.get("beds", "N/A")
                    bathrooms = entry.get("bathrooms_text", "N/A")
                    min_nights = entry.get("minimum_nights", "N/A")
                    max_nights = entry.get("maximum_nights", "N/A")
                    neighborhood_overview = entry.get("neighborhood_overview", "No neighborhood overview")

                    text = f"""
Listing ID: {entry_id}
Airbnb URL: {url}
Name: {name}
Room Type: {room_type}
Property Type: {property_type}
Accommodates: {accommodates}
Bedrooms: {bedrooms}
Beds: {beds}
Bathrooms: {bathrooms}
Price: {price}
Location: {neighborhood}
Minimum Nights: {min_nights}
Maximum Nights: {max_nights}

Description
{description}

Neighborhood Overview
{neighborhood_overview}

Amenities
{amenities_str}

Reviews: {num_reviews}
Availability: Available for {availability} days per year
""".strip()

                    file_path = os.path.join(kb_text_path, f"{entry_id}.txt")

                elif data_type == "reviews":
                    metadata = entry.get("metadata", {})
                    entry_id = str(entry.get("listing_id", f"unknown_{idx}"))
                    review_text = entry.get("comments", "No comment provided.")

                    text = f"""Listing ID: {entry_id}

Review
{review_text}
""".strip()

                    file_path = os.path.join(kb_text_path, f"{entry_id}.txt")

                if os.path.exists(file_path):
                    print(f"File already exists: {file_path}")
                    continue

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                print(f"Created text file: {file_path}")

        except Exception as e:
            print(f"Error converting JSON to text for {data_type}: {e}")

    def _ensure_client(self):
        """Ensure client is valid (placeholder)"""
        if not self.client:
            st.error("Client not initialized.")
            return False
        return True
