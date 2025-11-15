1. First create a chainlit folder inside that create secrets.toml file [.chainlit/secrets.toml] and provide your API KEY and Vector Store ID's inside the secrets file like 

[openai] 
api_key= "sk......."  

[vectorstore]
listings_vector_store_id=""
reviews_vector_store_id=""


2. To run the code follow the steps in terminal:

  python3 -m venv pyenv

  source pyenv/bin/activate

  pip install -r requirements.txt

  chainlit run app.py
