import os
from neo4j import GraphDatabase, Driver


async def retrieve_neo4j_driver() -> Driver:
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "your_neo4j_password")

    neo4j_driver = GraphDatabase.driver(uri, auth=(user, password))
    return neo4j_driver


__all__ = ["retrieve_neo4j_driver"]
