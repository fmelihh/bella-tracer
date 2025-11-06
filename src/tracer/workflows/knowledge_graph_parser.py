import json
import asyncio
from typing import Any

from prefect import flow
from dotenv import load_dotenv

from tracer import prompts, interfaces, services

load_dotenv()


async def analyze_log_message(raw_message: str) -> dict[str, Any]:
    if not raw_message:
        return {}
    prompt = prompts.DETECTIVE_PROMPT_TEMPLATE.format(message=raw_message.strip())
    openai_client = await interfaces.openai.retrieve_openai_client()

    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    analysis_content = response.choices[0].message.content
    return json.loads(analysis_content)


async def build_cypher_queries(log_input_json: dict, analysis: dict) -> str:
    prompt = prompts.ARCHITECT_PROMPT_TEMPLATE.format(
        log_input_json=json.dumps(log_input_json),
        analysis_result_json=json.dumps(analysis),
    )
    openai_client = await interfaces.openai.retrieve_openai_client()

    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=[{"role": "user", "content": prompt}],
    )
    cypher_queries = response.choices[0].message.content
    cypher_queries = cypher_queries.replace("```cypher", "").replace("```", "").strip()
    if not cypher_queries.endswith(";"):
        cypher_queries += ";"
    return cypher_queries


async def execute_cypher_queries(cypher_query: str):
    if not cypher_query:
        return

    neo4j_driver = await interfaces.neo4j.retrieve_neo4j_driver()
    with neo4j_driver.session(database="neo4j") as session:
        session.run(cypher_query)


async def write_embedding_for_log(log_data: dict[str, Any], analysis: dict[str, Any]):
    rag_text = services.knowledge_graph.compose_rag_text(log_data, analysis)
    if not rag_text:
        return

    embedding = await services.knowledge_graph.embed_text(rag_text)
    log_id = services.knowledge_graph.make_log_id(log_data)

    neo4j_driver = await interfaces.neo4j.retrieve_neo4j_driver()
    with neo4j_driver.session(database="neo4j") as session:
        lid = services.knowledge_graph.upsert_log_embedding_with_service(
            session, log_data, log_id, rag_text, embedding
        )
        if lid == -1:
            lid = services.knowledge_graph.upsert_log_embedding_with_trace(
                session, log_data, log_id, rag_text, embedding
            )
        if lid == -1:
            services.knowledge_graph.upsert_log_embedding(
                session, log_data, log_id, rag_text, embedding
            )


@flow(name="knowledge-graph-parser", log_prints=True)
async def knowledge_graph_parser():
    consumer = await interfaces.kafka.retrieve_aio_kafka_consumer(
        topic="logs", consumer_group="g1"
    )
    await consumer.start()
    try:
        cnt = 0
        async for msg in consumer:
            try:
                print(f"[KafkaConsumer] Processing log {cnt}")
                log_data = json.loads(msg.value.decode("utf-8"))

                raw_message = log_data.get("message", "") or ""
                if log_data.get("exc_info"):
                    raw_message += "\n" + log_data.get("exc_info")

                analysis_result = await analyze_log_message(raw_message=raw_message)
                if "error" in analysis_result:
                    cnt += 1
                    continue

                cypher_queries = await build_cypher_queries(
                    log_input_json=log_data, analysis=analysis_result
                )
                await execute_cypher_queries(cypher_query=cypher_queries)

                await write_embedding_for_log(log_data, analysis_result)

                cnt += 1
            except Exception as e:
                print("[KG-ETL] Error:", e)
                continue
    finally:
        await consumer.stop()


if __name__ == "__main__":
    import asyncio

    asyncio.run(knowledge_graph_parser.fn())
