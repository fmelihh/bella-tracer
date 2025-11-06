import os
import json
from prefect import flow, task
from aiokafka import AIOKafkaConsumer
from neo4j import GraphDatabase
from openai import AsyncOpenAI
from typing import Dict, Any

from tracer import prompts

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your_neo4j_password")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
KAFKA_TOPIC = "logs"

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)


# @task(name="Analyze Log (Detective)")
async def analyze_log_message(raw_message: str) -> Dict[str, Any]:
    if not raw_message:
        return {}

    prompt = prompts.DETECTIVE_PROMPT_TEMPLATE.format(message=raw_message.strip())
    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    analysis_content = response.choices[0].message.content
    return json.loads(analysis_content)


# @task(name="Build Cypher (Architect)")
async def build_cypher_queries(log_input_json: Dict, analysis: Dict) -> str:
    prompt = prompts.ARCHITECT_PROMPT_TEMPLATE.format(
        log_input_json=json.dumps(log_input_json),
        analysis_result_json=json.dumps(analysis),
    )
    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18", messages=[{"role": "user", "content": prompt}]
    )
    cypher_queries = response.choices[0].message.content
    cypher_queries = cypher_queries.replace("```cypher", "").replace("```", "").strip()
    return cypher_queries


# @task(name="Write to Neo4j")
async def execute_cypher_queries(cypher_query: str):
    if not cypher_query:
        return

    with GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)) as driver:
        with driver.session(database="neo4j") as session:
            queries = [q.strip() for q in cypher_query.split(";") if q.strip()]

            with session.begin_transaction() as tx:
                for i, query in enumerate(queries):
                    try:
                        tx.run(query)
                    except Exception as e:
                        print(e)
                        tx.rollback()
                        return


@flow(name="knowledge_graph_parser", log_prints=True)
async def knowledge_graph_parser():
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset="earliest",
        group_id="kg_etl_group-99",
    )

    await consumer.start()
    try:
        cnt = 0
        async for msg in consumer:
            try:
                print(
                    f"[KafkaConsumer] Processing log {cnt}",
                    end="\r",
                    flush=True,
                )
                log_data = json.loads(msg.value.decode("utf-8"))
                raw_message = log_data.get("message", "")
                if log_data.get("exc_info"):
                    raw_message += "\n" + log_data.get("exc_info")

                analysis_result = await analyze_log_message(raw_message=raw_message)
                if "error" in analysis_result:
                    continue

                cypher_queries = await build_cypher_queries(
                    log_input_json=log_data, analysis=analysis_result
                )
                await execute_cypher_queries(cypher_query=cypher_queries)
                cnt += 1
            except Exception as e:
                print(e)
                raise e
    finally:
        await consumer.stop()


if __name__ == "__main__":
    import asyncio

    asyncio.run(knowledge_graph_parser.fn())
