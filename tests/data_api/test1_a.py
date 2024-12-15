import numpy as np
import requests
import torch
from transformers import BertTokenizer, BertModel
import streamlit as st
from sklearn.metrics.pairwise import cosine_similarity

# Define API URLs and headers
GROQ_API_KEY = "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"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MONSTER_API_URL = "https://api.mlsakiit.com/monsters"
SURVIVORS_API_URL = "https://api.mlsakiit.com/survivors"
RESOURCES_API_URL = "https://api.mlsakiit.com/resources"
HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

# Load a BERT model and tokenizer for embedding using PyTorch
tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
model = BertModel.from_pretrained("bert-base-uncased")
model.eval()  # Set model to evaluation mode

# Function to fetch monster data from API
def fetch_monster_data():
    try:
        response = requests.get(MONSTER_API_URL, headers={"accept": "application/json"})
        response.raise_for_status()
        return response.json().get("monsters", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching monster data: {e}")
        return [{"monster_id": "unknown", "lat": 0, "lon": 0}]  # Default fallback

# Function to fetch resource data from API
def fetch_resource_data():
    try:
        response = requests.get(RESOURCES_API_URL, headers={"accept": "application/json"})
        response.raise_for_status()
        return response.json().get("features", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching resource data: {e}")
        return []

# Function to fetch survivor data from API
def fetch_survivor_data():
    try:
        response = requests.get(SURVIVORS_API_URL, headers={"accept": "application/json"})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching survivor data: {e}")
        return []

# Function to format monster data into readable context
def format_monster_data(monsters):
    return [f"Monster {monster['monster_id']} at ({monster['lat']}, {monster['lon']})" for monster in monsters]

# Function to format survivor data into readable context
def format_survivor_data(survivors):
    return [f"Survivor {survivor['survivor_id']} in {survivor['district']} ({survivor['lat']}, {survivor['lon']})" for survivor in survivors]

# Function to format resource data into readable context
def format_resource_data(resources):
    return [
        f"{props.get('dist_name', 'Unknown')}: Temp {props.get('temp', 'N/A')}°C, Food {props.get('food_rations', 'N/A')}kg"
        for resource in resources if (props := resource.get("properties"))
    ]

# Function to get BERT embeddings for a list of texts using PyTorch
def get_embeddings(texts):
    inputs = tokenizer(texts, padding=True, truncation=True, return_tensors="pt", max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
        embeddings = outputs.last_hidden_state  # Use the last hidden state
        mean_embeddings = torch.mean(embeddings, dim=1).numpy()  # Mean pooling of token embeddings
    return mean_embeddings

# Function to calculate cosine similarity between embeddings
def calculate_cosine_similarity(query_embedding, context_embeddings):
    return cosine_similarity(query_embedding, context_embeddings)

# Function to find the most relevant context based on cosine similarity
def find_relevant_context(query, context):
    # Get embeddings for the query and context
    query_embedding = get_embeddings([query])
    context_embeddings = get_embeddings(context)

    # Calculate cosine similarities
    similarities = calculate_cosine_similarity(query_embedding, context_embeddings)

    # Sort contexts by similarity in descending order
    top_indices = np.argsort(similarities[0])[::-1]
    top_contexts = [context[i] for i in top_indices[:3]]  # Retrieve top 3 relevant contexts

    return top_contexts

# Function to generate a response using Groq API
def generate_response(query, context):
    messages = [{"role": "user", "content": query}]
    for doc in context:
        messages.append({"role": "system", "content": doc})

    try:
        response = requests.post(GROQ_API_URL, json={
            "model": "mixtral-8x7b-32768",  # Example model ID
            "messages": messages
        }, headers=HEADERS)

        response_data = response.json()
        if "choices" not in response_data:
            raise ValueError(f"Unexpected response format: {response_data}")
        
        return response_data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error generating response: {e}"

# Main function to run the chatbot on Streamlit
def run_chatbot():
    # Fetch monster, survivor, and resource data
    monsters = fetch_monster_data()
    survivors = fetch_survivor_data()
    resources = fetch_resource_data()

    # Format data into readable context
    context = format_monster_data(monsters)
    context += format_survivor_data(survivors)
    context += format_resource_data(resources)

    # Streamlit UI components
    st.title("Survival Chatbot")
    st.write("Ask me anything about survival!")

    # User input for query
    query = st.text_input("Your question:")

    if query:
        # Find relevant context using cosine similarity
        relevant_context = find_relevant_context(query, context)

        # Generate a response based on the query and relevant context
        response = generate_response(query, relevant_context)
        st.write("Chatbot Response:")
        st.write(response)

# Run the Streamlit app
if __name__ == "__main__":
    run_chatbot()
