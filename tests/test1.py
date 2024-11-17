from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import warnings
warnings.filterwarnings("ignore")
from neo4j import GraphDatabase
from langchain_community.graphs import Neo4jGraph
from langchain_experimental.llms.ollama_functions import OllamaFunctions
from langchain.chains import GraphCypherQAChain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import PydanticOutputParser
from typing import List

load_dotenv()

app = Flask(__name__)
CORS(app)

# Neo4j connection
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# Entities model for structured output
class Entities(BaseModel):
    """Identifying information about entities."""
    names: List[str] = Field(..., description="List of identified entities from the input text.")

    @classmethod
    def model_construct(cls, **kwargs):
        """Custom method to create an instance using data."""
        return cls(**kwargs)

def graph_connection():
    try:
        graph = Neo4jGraph(url=NEO4J_URI, username=NEO4J_USERNAME, password=NEO4J_PASSWORD)
        return graph
    except Exception as e:
        print(f"Error connecting to Neo4j: {e}")
        return None

# Ollama LLM connection
def llm_connection():
    try:
        llm = OllamaFunctions(
            model="llama3-8b",
            endpoint="http://localhost:11434"
        )
        return llm
    except Exception as e:
        print(f"Error initializing LLM: {e}")
        return None

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are extracting automotive entities like Model, Engine, Variant, etc., from the input."),
    ("human", "Use the given format to extract entities from: {input_text}")
])

# Function to map entities to nodes in the database based on the schema
match_query = """
MATCH (n)
WHERE n.name CONTAINS $value
RETURN n.name AS result, labels(n)[0] AS type
LIMIT 1
"""

def map_to_database(graph, values):
    if not graph:
        return "Graph connection failed."
    result = ""
    for entity in values.names:
        try:
            response = graph.query(match_query, {"value": entity})
            if response:
                result += f"{entity} maps to {response[0]['result']} {response[0]['type']} in the database.\n"
        except IndexError:
            continue
    return result or "No matching entities found."

def cypher_query_generator(graph, llm, entity_chain, question):
    cypher_template = """Based on the Neo4j graph schema below, write a Cypher query that would answer the user's question:
    {schema}
    Entities in the question map to the following database values:
    {entities_list}
    Question: {question}
    Cypher query:"""

    cypher_prompt = ChatPromptTemplate.from_messages([
        ("system", "Given an input question, convert it to a Cypher query."),
        ("human", cypher_template)
    ])

    try:
        entities = entity_chain.invoke({"input_text": question})
        print("Extracted Entities:", entities)

        # Map extracted entities to database nodes
        mapped_entities = map_to_database(graph, entities)
        print("Mapped Entities:", mapped_entities)

        # Retrieve schema from the graph
        schema = graph.get_schema()
        print("Graph Schema:", schema)

        # Prepare the prompt with extracted data
        cypher_prompt_data = {
            "schema": schema,
            "entities_list": mapped_entities,
            "question": question,
        }

        # Pass the data to the LLM for Cypher query generation
        cypher_response = (
            cypher_prompt
            | llm.bind(stop=["\nCypherResult:"])
            | StrOutputParser()
        ).invoke(cypher_prompt_data)

        print("Generated Cypher Query:", cypher_response)

        if not isinstance(cypher_response, str) or not cypher_response.strip().lower().startswith(("match", "return")):
            raise ValueError(f"Generated response is not a valid Cypher query: {cypher_response}")

        return cypher_response

    except Exception as e:
        print(f"Error generating Cypher query: {e}")
        return None

# Main function
def main(query):
    graph = graph_connection()
    llm = llm_connection()
    
    if not graph or not llm:
        return "Failed to initialize graph or LLM."

    # Chain to extract entities from query
    output_parser = PydanticOutputParser(pydantic_object=Entities)
    entity_chain = prompt | llm | output_parser

    # Generate the Cypher query based on user input and schema mapping
    try:
        cypher_response = cypher_query_generator(graph, llm, entity_chain, query)
        if not cypher_response:
            return "Cypher query generation failed."
    except Exception as e:
        print(f"Error during Cypher query generation: {e}")
        return f"Error during Cypher query generation: {e}"

    # Execute the Cypher query on the graph
    try:
        print(f"Executing Cypher Query: {cypher_response}")
        query_result = graph.query(cypher_response)
        print(f"Query Result: {query_result}")
        return {"query_result": query_result}
    except Exception as e:
        print(f"Graph Query Error: {e}")
        return f"Graph Query Error: {e}"

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Flask server is running!"})

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    query = data.get("query")
    if not query:
        return jsonify({"error": "Query is required"}), 400

    answer = main(query)
    return jsonify({"answer": answer})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)