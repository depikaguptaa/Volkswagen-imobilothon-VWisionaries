from langchain_community.graphs import Neo4jGraph
import json
import re
from dotenv import load_dotenv
import os

load_dotenv()

neo4j_uri = os.getenv("NEO4J_URI")
neo4j_username = os.getenv("NEO4J_USERNAME")
neo4j_password = os.getenv("NEO4J_PASSWORD")
neo4j_database = os.getenv("NEO4J_DATABASE")

graph = Neo4jGraph(url=neo4j_uri, username=neo4j_username, password=neo4j_password)

# Utility to clean JSON keys
def clean_key(key):
    return re.sub(r'[^a-zA-Z0-9_]', '_', key)

def clean_json(data):
    if isinstance(data, dict):
        return {clean_key(k): clean_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_json(i) for i in data]
    return data

# Create constraints
def create_constraints(graph):
    graph.query('CREATE CONSTRAINT BRAND_CONSTRAINT IF NOT EXISTS FOR (b:Brand) REQUIRE b.name IS UNIQUE')
    graph.query('CREATE CONSTRAINT MODEL_CONSTRAINT IF NOT EXISTS FOR (m:Model) REQUIRE m.name IS UNIQUE')

def create_node(graph, label, properties):
    props = ', '.join(f"{k}: '{v}'" for k, v in properties.items())
    QUERY = f"MERGE (n:{label} {{{props}}})"
    graph.query(QUERY)

def create_relationship(graph, node1_label, node1_props, relationship, node2_label, node2_props):
    node1 = ', '.join(f"{k}: '{v}'" for k, v in node1_props.items())
    node2 = ', '.join(f"{k}: '{v}'" for k, v in node2_props.items())
    QUERY = f"""
    MATCH (a:{node1_label} {{{node1}}})
    MATCH (b:{node2_label} {{{node2}}})
    MERGE (a)-[:{relationship}]->(b)
    """
    graph.query(QUERY)

# Create Brand and Model nodes
def create_brand_and_model_nodes(graph, car):
    brand = car['brand']
    model = car['model']
    create_node(graph, "Brand", {"name": brand['name'], "origin": brand['origin']})
    create_node(graph, "Model", {"name": model['name'], "type": model['type'], "launched": model['launched']})
    create_relationship(graph, "Brand", {"name": brand['name']}, "HAS_MODEL", "Model", {"name": model['name']})

# Function to create Features node
def create_features_node(graph, variant):
    if "features" in variant:
        try:
            print(f"Creating Features node for Variant {variant['name']}.")
            features = json.dumps(variant['features']).replace("'", '"')
            create_node(graph, "Features", {"details": features})
            create_relationship(graph, "Variant", {"name": variant['name']}, "HAS_FEATURES", "Features", {"details": features})
        except Exception as e:
            print(f"Exception occurred while creating Features node: {e}")

# Create Variant node and related nodes
def create_variant_nodes(graph, car):
    model_name = car['model']['name']
    for variant in car['variant']:
        create_node(graph, "Variant", {"name": variant['name'], "launched": variant['launched']})
        create_relationship(graph, "Model", {"name": model_name}, "HAS_VARIANT", "Variant", {"name": variant['name']})

        feature_mapping = {
            "steering": "Steering",
            "capacity": "Capacity",
            "suspension": "Suspension",
            "brake": "Brake",
            "dimensions": "Dimensions",
            "entertainment": "Entertainment",
            "safety": "Safety",
            "fuel": "Fuel",
            "wheel": "Wheel",
            "price": "Price",
            "engine": "Engine",
            "transmission": "Transmission"
        }

        for key, label in feature_mapping.items():
            if key in variant:
                feature_data = variant[key]

                if key == "price" and isinstance(feature_data, dict) and 'ex_showroom' in feature_data:
                    # Convert ex_showroom price to a numeric value
                    numeric_price = convert_price_to_number(feature_data['ex_showroom'])
                    if numeric_price is not None:
                        feature_data['ex_showroom'] = numeric_price

                if isinstance(feature_data, dict):
                    create_node(graph, label, feature_data)
                else:
                    create_node(graph, label, {"details": json.dumps(feature_data).replace("'", '"')})

                create_relationship(graph, "Variant", {"name": variant['name']}, f"HAS_{label.upper()}", label, feature_data)

        create_features_node(graph, variant)

# convert price to a numeric value
def convert_price_to_number(price_string):
    price_string = price_string.lower().replace(",", "").strip()

    # Handle various cases for "crore" and "lakh"
    if any(term in price_string for term in ["crore", "cr", "crores", "cr.", "crore.", "crores."]):
        price_string = re.sub(r"crore|crores|cr|cr\.|crore\.|crores\.", "", price_string).strip()
        try:
            return int(float(price_string) * 1e7)
        except ValueError:
            print(f"Could not convert price: {price_string}")
            return None

    elif any(term in price_string for term in ["lakh", "lac", "lakh.", "lac.", "lakhs", "lacs"]):
        price_string = re.sub(r"lakh|lac|lakhs|lacs|lakh\.|lac\.", "", price_string).strip()
        try:
            return int(float(price_string) * 1e5)
        except ValueError:
            print(f"Could not convert price: {price_string}")
            return None

    # Handle cases for "rupees" or "rs" or "rs."
    elif any(term in price_string for term in ["rs.", "rs", "rupees", "rup", "₹"]):
        price_string = re.sub(r"rs\.|rs|rupees|rup|₹", "", price_string).strip()
        try:
            return int(float(price_string))
        except ValueError:
            print(f"Could not convert price: {price_string}")
            return None

    else:
        try:
            return int(float(price_string))
        except ValueError:
            print(f"Could not convert price: {price_string}")
            return None

if __name__ == '__main__':
    with open('formatted_car_data.json', 'r') as f:
        raw_data = json.load(f)

    json_data = clean_json(raw_data)

    # Create constraints
    create_constraints(graph)

    for car in json_data:
        create_brand_and_model_nodes(graph, car)
        create_variant_nodes(graph, car)