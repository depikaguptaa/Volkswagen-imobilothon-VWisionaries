import os
from py2neo import Graph, Node, Relationship
import json

# Neo4j connection details from environment variables
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# Connect to Neo4j
graph = Graph(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

# Function to create nodes and relationships based on ontology
def create_knowledge_graph(data):
    for brand_name, models in data.items():
        if not brand_name:  # Skip if brand_name is None
            continue

        # Create Brand node
        brand_node = Node("Brand", name=brand_name)
        graph.merge(brand_node, "Brand", "name")

        for model in models:
            model_url = model.get("model_url", "Unknown")
            model_node = Node("Model", url=model_url)
            graph.merge(model_node, "Model", "url")

            # Relationship: Brand -> Model
            graph.merge(Relationship(brand_node, "HAS_MODEL", model_node))

            for variant in model["variants"]:
                variant_name = variant.get("variant_name")
                if not variant_name:  # Skip if variant_name is None
                    continue

                price = variant.get("price", "Unknown")
                variant_node = Node("Variant", name=variant_name, price=price)
                graph.merge(variant_node, "Variant", "name")

                # Relationship: Model -> Variant
                graph.merge(Relationship(model_node, "HAS_VARIANT", variant_node))

                # Create nodes for each specification category
                for spec_category, specs in variant["specifications"].items():
                    # Ensure category name is valid and non-empty
                    category_name = spec_category.replace(" ", "_")
                    if not category_name:  # Skip if category name is None
                        continue

                    # Create or merge the category node with non-null name
                    category_node = Node(category_name, name=category_name)
                    graph.merge(category_node, category_name, "name")

                    # Relationship: Variant -> Spec Category
                    graph.merge(Relationship(variant_node, f"HAS_{spec_category.upper()}", category_node))

                    # Add attributes as individual properties of the category node
                    for spec_key, spec_value in specs.items():
                        if spec_value is not None:  # Only set non-null values
                            category_node[spec_key] = spec_value
                    # Push the node to update properties in Neo4j
                    graph.push(category_node)

# Load data from JSON file
def load_data(json_file_path):
    with open(json_file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data

# Main function
def main(json_file_path):
    data = load_data(json_file_path)
    create_knowledge_graph(data)
    print("Knowledge graph created successfully!")

json_file_path = "car_data.json"
main(json_file_path)