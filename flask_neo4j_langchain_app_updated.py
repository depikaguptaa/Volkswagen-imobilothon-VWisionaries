from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import requests
from neo4j import GraphDatabase
from langchain_community.graphs import Neo4jGraph

load_dotenv()

app = Flask(__name__)
CORS(app)

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_ENDPOINT = os.getenv("GROQ_API_ENDPOINT")

# Connect to Neo4j
def connect_to_neo4j():
    try:
        return Neo4jGraph(url=NEO4J_URI, username=NEO4J_USERNAME, password=NEO4J_PASSWORD)
    except Exception as e:
        print(f"Error connecting to Neo4j: {e}")
        return None

# Query Groq API
def query_groq(prompt):
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {"prompt": prompt}
        response = requests.post(GROQ_API_ENDPOINT, headers=headers, json=payload)

        if response.status_code == 200:
            return response.json().get("text", "")
        else:
            raise Exception(f"Error from Groq API: {response.status_code} {response.text}")
    except Exception as e:
        print(f"Error querying Groq API: {e}")
        return None

def generate_cypher_query(graph, question):
    try:
        schema = graph.get_schema()
        prompt = f"""
            Based on the Neo4j graph schema below, write a Cypher query that would answer the user's question:
            Schema: {schema}
            Question: {question}
            Cypher query:"""
        return query_groq(prompt)
    except Exception as e:
        print(f"Error generating Cypher query: {e}")
        return None

# Main function
def handle_query(question):
    graph = connect_to_neo4j()
    if not graph:
        return "Failed to connect to Neo4j."

    cypher_query = generate_cypher_query(graph, question)
    if not cypher_query:
        return "Failed to generate Cypher query."

    try:
        result = graph.query(cypher_query)
        return {"query": cypher_query, "result": result}
    except Exception as e:
        print(f"Error executing Cypher query: {e}")
        return "Error executing Cypher query."

# Flask routes
@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Flask server is running!"})

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    question = data.get("query")
    if not question:
        return jsonify({"error": "Query is required"}), 400

    response = handle_query(question)
    return jsonify({"answer": response})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)