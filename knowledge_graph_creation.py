import os
import json
from py2neo import Graph, Node, Relationship

# Neo4j connection details from environment variables
NEO4J_URI='neo4j+s://165b338b.databases.neo4j.io'
NEO4J_USERNAME='neo4j'
NEO4J_PASSWORD='hDXIVCazyWlH9WyFiUvIIN71m_U7BKwmYxYpLwWCqww'
AURA_INSTANCEID='165b338b'
AURA_INSTANCENAME='Instance02'

# Connect to Neo4j
graph = Graph(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

# Mapping dictionary to standardize JSON keys to ontology keys
KEY_MAPPING = {
    # Engine
    "Engine Type": "engine_type",
    "No. of cylinders": "cylinders",
    "Displacement": "displacement",
    "Power": "power",
    "Torque": "torque",

    # Transmission
    "Drive Type": "drive_type",
    "Gear Box": "gearbox",
    "Transmission Type": "trans_type",

    # Fuel
    "Fuel Type": "type",
    "Mileage (ARAI)": "mileage",
    "Fuel Tank Capacity": "capacity",
    "BS Type": "bs_type",

    # Dimension
    "Length": "length",
    "Width": "width",
    "Height": "height",
    "Ground Clearance (Laden)": "ground_clearance_laden",
    "Ground Clearance Unladen": "ground_clearance_unladen",
    "Wheelbase": "wheel_base",
    "Kerb Weight": "kerb_weight",
    "Gross Weight": "gross_weight",

    # Brake
    "Front Brake Type": "front_type",
    "Rear Brake Type": "rear_type",

    # Suspension
    "Front Suspension": "front",
    "Rear Suspension": "rear",

    # Steering
    "Steering Type": "type",
    "Steering Column": "column",
    "Turning Radius": "radius",

    # Capacity
    "Seating Capacity": "seating_capacity",
    "Boot Space": "boot_space",
    "No. of Doors": "no_of_doors",

    # Wheel
    "Wheel Type": "wheel_type",
    "Tyre Size": "tyre_size",
    "Tyre Type": "tyre_type",
    "Wheel Size": "wheel_size",

    # Price
    "Ex-Showroom Price": "ex_showroom",

    # Entertainment
    "Connectivity": "connectivity",
    "Android Auto": "android_auto",
    "Apple CarPlay": "car_play",
    "No. of Speakers": "no_of_speakers",
    "Touchscreen Size": "touchscreen_size",

    # Safety
    "ABS": "abs",
    "No. of Airbags": "no_of_airbags",
    "Hill Assist": "hill_assist",
    "NCAP Rating": "ncap_rating",
    "ADAS": "adas",

    # Features
    "Power Steering": "power_steering",
    "Air Conditioner": "air_conditioner"
}

# Function to map keys based on KEY_MAPPING dictionary
def map_keys(specs, key_mapping):
    mapped_specs = {}
    for key, value in specs.items():
        mapped_key = key_mapping.get(key, key)  # Use mapped key if available, else original key
        mapped_specs[mapped_key] = value

    # Add placeholders for specific keys if missing
    for expected_key in ["engine_type", "wheel_size", "ground_clearance_unladen"]:
        if expected_key not in mapped_specs:
            mapped_specs[expected_key] = "Unknown"  # Set default value as "Unknown"

    return mapped_specs

# Function to create nodes and relationships based on ontology
def create_knowledge_graph(data):
    for brand_name, models in data.items():
        if not brand_name:
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
                if not variant_name:
                    continue

                price = variant.get("price", "Unknown")
                variant_node = Node("Variant", name=variant_name, price=price)
                graph.merge(variant_node, "Variant", "name")

                # Relationship: Model -> Variant
                graph.merge(Relationship(model_node, "HAS_VARIANT", variant_node))

                # Create nodes for each specification category
                for spec_category, specs in variant["specifications"].items():
                    category_name = spec_category.replace(" ", "_")
                    if not category_name:
                        continue

                    # Create or merge the category node
                    category_node = Node(category_name, name=category_name)
                    graph.merge(category_node, category_name, "name")

                    # Relationship: Variant -> Spec Category
                    graph.merge(Relationship(variant_node, f"HAS_{spec_category.upper()}", category_node))

                    # Map the keys in specs based on the KEY_MAPPING dictionary
                    mapped_specs = map_keys(specs, KEY_MAPPING)
                    
                    # Add attributes to the category node based on mapped keys
                    for spec_key, spec_value in mapped_specs.items():
                        if spec_value is not None:  # Only set non-null values
                            category_node[spec_key] = spec_value
                    graph.push(category_node)

# Function to load data from JSON file
def load_data(json_file_path):
    with open(json_file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data

# Main function to create knowledge graph
def main(json_file_path):
    data = load_data(json_file_path)
    create_knowledge_graph(data)
    print("Knowledge graph created successfully!")

# Provide path to your JSON file
json_file_path = "formatted_car_data.json"
main(json_file_path)