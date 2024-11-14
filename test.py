from neo4j import GraphDatabase
import json


# Neo4j Connector
class Neo4jConnector:
    def __init__(self, uri, username, password):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))

    def close(self):
        if self.driver:
            self.driver.close()

    def query(self, query, parameters=None):
        with self.driver.session() as session:
            return session.run(query, parameters)


# Create constraints to avoid duplicate nodes
def create_constraints(connector):
    try:
        connector.query('CREATE CONSTRAINT IF NOT EXISTS FOR (b:Brand) REQUIRE b.name IS UNIQUE')
        connector.query('CREATE CONSTRAINT IF NOT EXISTS FOR (m:Model) REQUIRE m.name IS UNIQUE')
        print("Constraints created successfully.")
    except Exception as e:
        print(f"Error while creating constraints: {e}")


# Create Brand nodes
def create_brand_nodes(connector, json_data):
    try:
        print(f"Creating a Brand node for {json_data['brand']['name']}.")
        query = """
        MERGE (b:Brand {name: $name, origin: $origin})
        """
        parameters = {
            "name": json_data['brand']['name'],
            "origin": json_data['brand']['origin']
        }
        connector.query(query, parameters=parameters)
    except Exception as e:
        print(f"Error while creating Brand node: {e}")


# Create Model nodes
def create_model_nodes(connector, json_data):
    try:
        print(f"Creating a Model node for {json_data['model']['name']}.")
        query = """
        MERGE (m:Model {name: $name, type: $type, launched: $launched})
        """
        parameters = {
            "name": json_data['model']['name'],
            "type": json_data['model']['type'],
            "launched": json_data['model']['launched']
        }
        connector.query(query, parameters=parameters)
    except Exception as e:
        print(f"Error while creating Model node: {e}")


# Create Feature nodes
def create_feature_nodes(connector, json_data):
    print("Creating a Feature node.")
    try:
        query = "MERGE (f:Feature {"
        parameters = {}
        for key, value in json_data.get('features', {}).items():
            query += f"{key}: ${key}, "
            parameters[key] = value
        query = query.rstrip(", ") + "})"
        connector.query(query, parameters=parameters)
    except Exception as e:
        print(f"Error while creating Feature node: {e}")


# Create relationships between Brand and Model
def create_relation_brand_model(connector, json_data):
    try:
        print(f"Creating a relation between Brand {json_data['brand']['name']} and Model {json_data['model']['name']}.")
        query = """
        MATCH (b:Brand {name: $brand_name})
        MATCH (m:Model {name: $model_name})
        MERGE (b)-[:HAS_MODEL]->(m)
        """
        parameters = {
            "brand_name": json_data['brand']['name'],
            "model_name": json_data['model']['name']
        }
        connector.query(query, parameters=parameters)
    except Exception as e:
        print(f"Error while creating relationship: {e}")


if __name__ == '__main__':
    # Connect to Neo4j with provided credentials
    connector = Neo4jConnector(
        uri="bolt://165b338b.databases.neo4j.io:7687",
        username="neo4j",
        password="hDXIVCazyWlH9WyFiUvIIN71m_U7BKwmYxYpLwWCqw"
    )

    try:
        # Load JSON data
        with open("formatted_car_data.json", "r") as f:
            json_data = json.load(f)

        # Create constraints
        create_constraints(connector)

        # Process each JSON entry
        for json_single in json_data:
            # Create nodes
            create_brand_nodes(connector, json_single)
            create_model_nodes(connector, json_single)
            create_feature_nodes(connector, json_single)

            # Create relationships
            create_relation_brand_model(connector, json_single)

    finally:
        # Close the Neo4j connection
        connector.close()