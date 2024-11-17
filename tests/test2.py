from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import requests
from neo4j import GraphDatabase

load_dotenv()

app = Flask(__name__)
CORS(app)

# Neo4j connection
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# Groq API connection
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_ENDPOINT = os.getenv("GROQ_API_ENDPOINT")
MODEL_NAME = "llama3-8b-8192"

# schema retrieval and query execution
class Neo4jHandler:
    def __init__(self, uri, username, password):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))

    def get_schema(self):
        with self.driver.session() as session:
            query = "CALL db.schema.visualization()"
            result = session.run(query)
            
            # Extract nodes and relationships
            schema = []
            for record in result:
                nodes = [
                    {
                        "element_id": node.element_id,
                        "labels": list(node.labels),
                        "properties": dict(node._properties),
                    }
                    for node in record["nodes"]
                ]
                relationships = [
                    {
                        "element_id": rel.element_id,
                        "start_node": rel.start_node.element_id,
                        "end_node": rel.end_node.element_id,
                        "type": rel.type,
                        "properties": dict(rel._properties),
                    }
                    for rel in record["relationships"]
                ]
                schema.append({"nodes": nodes, "relationships": relationships})
            
            return schema

    def query(self, cypher_query):
        with self.driver.session() as session:
            return [record.data() for record in session.run(cypher_query)]

    def close(self):
        self.driver.close()

def connect_to_neo4j():
    try:
        return Neo4jHandler(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
    except Exception as e:
        print(f"Error connecting to Neo4j: {e}")
        return None

def query_groq(schema, question):
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "llama3-8b-8192",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Schema: {schema}\nQuestion: {question}"}
            ],
            "max_tokens": 100
        }
        print("Groq API Payload:", payload)
        response = requests.post(GROQ_API_ENDPOINT, headers=headers, json=payload)

        if response.status_code == 200:
            response_data = response.json()
            print("Groq API Response:", response_data)
            return response_data["choices"][0]["message"]["content"].strip()
        else:
            raise Exception(f"Error from Groq API: {response.status_code} {response.text}")
    except Exception as e:
        print(f"Error querying Groq API: {e}")
        return None

# Generate Cypher query
def generate_cypher_query(handler, question):
    try:
        schema = handler.get_schema()
        if not schema:
            raise ValueError("Schema is empty or could not be retrieved.")
        
        cypher_query = query_groq(schema, question)
        return cypher_query
    except Exception as e:
        print(f"Error generating Cypher query: {e}")
        return None

# Main function
def handle_query(question):
    handler = connect_to_neo4j()
    if not handler:
        return "Failed to connect to Neo4j."

    try:
        cypher_query = generate_cypher_query(handler, question)
        if not cypher_query:
            return "Failed to generate Cypher query."

        result = handler.query(cypher_query)
        return {"query": cypher_query, "result": result}
    except Exception as e:
        print(f"Error executing Cypher query: {e}")
        return "Error executing Cypher query."
    finally:
        handler.close()

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