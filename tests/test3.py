import streamlit as st
from neo4j import GraphDatabase
import requests
import json
import os
import re
import atexit
from dotenv import load_dotenv 

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_ENDPOINT = os.getenv("GROQ_API_ENDPOINT")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

def extract_cypher_query(response_content):
    try:
        match = re.search(r"```(.*?)```", response_content, re.DOTALL)
        if match:
            query = match.group(1).strip()
            if query.startswith("MATCH"):
                return query
        st.error("No valid Cypher query found in the Groq API response.")
        return ""
    except Exception as e:
        st.error(f"Error extracting Cypher query: {str(e)}")
        return ""

def generate_cypher_query(user_query):
    endpoint = GROQ_API_ENDPOINT
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {
                "role": "system",
                "content": """
                You are an assistant that converts natural language questions into Cypher queries for a Neo4J knowledge graph. 
                Always respond with only the Cypher query, enclosed in triple backticks. Do not include explanations or other text.

                The knowledge graph schema is as follows:

                - Nodes:
                - Brand (name: unique identifier of the car brand)
                - Model (name: unique identifier of the car model)
                - Variant (name: unique identifier of the car variant)
                - Price (price: numeric price value in rupees, stored as a property of the `Price` node)
                - Engine, Fuel, Safety, Features, Capacity, Dimensions, Suspension, Brake, Steering, Wheel, Entertainment, Transmission.

                - Relationships:
                - Brand `HAS_MODEL` → Model
                - Model `HAS_VARIANT` → Variant
                - Variant `HAS_PRICE` → Price
                - Variant `HAS_ENGINE` → Engine
                - Variant `HAS_FUEL` → Fuel
                - Variant `HAS_SAFETY` → Safety
                - Variant `HAS_FEATURES` → Features
                - Variant `HAS_CAPACITY` → Capacity
                - Variant `HAS_DIMENSIONS` → Dimensions
                - Variant `HAS_SUSPENSION` → Suspension
                - Variant `HAS_BRAKE` → Brake
                - Variant `HAS_STEERING` → Steering
                - Variant `HAS_WHEEL` → Wheel
                - Variant `HAS_ENTERTAINMENT` → Entertainment
                - Variant `HAS_TRANSMISSION` → Transmission.

                Key points for query generation:
                1. Always match the `Brand`, `Model`, and `Variant` nodes using the `name` property.
                2. For price-related queries, use the `price` property of the `Price` node for filtering (e.g., `p.price < 1200000`).
                3. Use precise filtering for relationships, and ensure the query returns only the requested information.
                """
            },
            {
                "role": "user",
                "content": user_query
            }
        ],
        "temperature": 0.0
    }
    try:
        response = requests.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()
        st.write("Groq API Response:", response_data)
        cypher_query = extract_cypher_query(response_data["choices"][0]["message"]["content"])
        return cypher_query
    except requests.exceptions.RequestException as e:
        st.error(f"Error communicating with Groq API: {str(e)}")
        return ""

def query_neo4j(cypher_query):
    if not cypher_query.strip().startswith("MATCH"):
        st.error("Invalid Cypher query. Query must start with 'MATCH'.")
        return []
    try:
        with driver.session() as session:
            results = session.run(cypher_query)
            return [record.data() for record in results]
    except Exception as e:
        st.error(f"Error executing Cypher query: {str(e)}")
        return []

def format_human_readable(data):
    endpoint = GROQ_API_ENDPOINT
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {
                "role": "system",
                "content": "You are a data formatter. Convert the provided data into natural language format."
            },
            {
                "role": "user",
                "content": json.dumps(data)
            }
        ]
    }
    try:
        response = requests.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()
        return response_data["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        st.error(f"Error communicating with Groq API: {str(e)}")
        return "Error generating response."

st.title("LLM-Based Automotive Data Insight Engine")
st.sidebar.header("Knowledge Graph Schema")
st.sidebar.json({
    "Nodes": [
        "Brand", "Model", "Variant", "Price", "Engine", "Fuel", "Safety", "Features",
        "Capacity", "Dimensions", "Suspension", "Brake", "Steering", "Wheel", "Entertainment", "Transmission"
    ],
    "Relationships": [
        "HAS_MODEL", "HAS_VARIANT", "HAS_ENGINE", "HAS_PRICE", "HAS_SAFETY", "HAS_FEATURES",
        "HAS_FUEL", "HAS_CAPACITY", "HAS_DIMENSIONS", "HAS_SUSPENSION", "HAS_BRAKE",
        "HAS_STEERING", "HAS_WHEEL", "HAS_ENTERTAINMENT", "HAS_TRANSMISSION"
    ]
})

user_query = st.text_input("Enter your query:")

if user_query:
    st.session_state["chat_history"].append({"role": "user", "content": user_query})
    
    with st.spinner("Converting your query into a Cypher query..."):
        cypher_query = generate_cypher_query(user_query)
        st.session_state["chat_history"].append({"role": "bot", "content": f"Generated Cypher Query: `{cypher_query}`"})
    
    with st.spinner("Fetching data from the knowledge graph..."):
        neo4j_data = query_neo4j(cypher_query)
        st.session_state["chat_history"].append({"role": "bot", "content": f"Raw Data: {neo4j_data}"})
    
    with st.spinner("Formatting data for human readability..."):
        human_readable_response = format_human_readable(neo4j_data)
        st.session_state["chat_history"].append({"role": "bot", "content": human_readable_response})

for message in st.session_state["chat_history"]:
    if message["role"] == "user":
        st.write(f"**You:** {message['content']}")
    else:
        st.write(f"**Bot:** {message['content']}")

atexit.register(driver.close)