import os
import hashlib
from typing import Any

from bella_tracer.tracer import interfaces


async def ensure_neo4j_indexes():
    neo4j_driver = await interfaces.neo4j.retrieve_neo4j_driver()
    vector_dim = os.getenv("VECTOR_DIM", 1536)
    with neo4j_driver.session(database="neo4j") as session:
        session.run("""
        CREATE CONSTRAINT trace_id_unique IF NOT EXISTS
        FOR (t:Trace) REQUIRE t.id IS UNIQUE
        """)
        session.run("""
        CREATE CONSTRAINT service_name_unique IF NOT EXISTS
        FOR (s:Service) REQUIRE s.name IS UNIQUE
        """)
        session.run("""
        CREATE CONSTRAINT order_id_unique IF NOT EXISTS
        FOR (o:Order) REQUIRE o.id IS UNIQUE
        """)
        session.run(f"""
        CREATE VECTOR INDEX log_embedding_index IF NOT EXISTS
        FOR (l:Log) ON (l.embedding)
        OPTIONS {{
          indexConfig: {{
            `vector.dimensions`: {vector_dim},
            `vector.similarity_function`: 'cosine'
          }}
        }}
        """)


def make_log_id(log_json: dict[str, Any]) -> str:
    key = "|".join(
        [
            str(log_json.get("service", "")),
            str(log_json.get("timestamp", "")),
            str(log_json.get("level", "")),
            str(log_json.get("funcName", "")),
            str(log_json.get("trace_id", "")),
            (log_json.get("message") or "")[:200],
        ]
    )
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def compose_rag_text(log_json: dict[str, Any], analysis: dict[str, Any]) -> str:
    parts = [
        f"service={log_json.get('service')}",
        f"level={log_json.get('level')}",
        f"func={log_json.get('funcName')}",
        f"trace_id={log_json.get('trace_id')}",
        f"message={log_json.get('message')}",
    ]
    if log_json.get("exc_info"):
        parts.append(f"exc_info={log_json['exc_info']}")

    ent = (analysis or {}).get("entities") or {}
    if ent.get("order_id"):
        parts.append(f"order_id={ent['order_id']}")

    err = (analysis or {}).get("error_summary") or {}
    if err.get("type"):
        parts.append(f"error_type={err['type']}")
    if err.get("message"):
        parts.append(f"error_msg={err['message']}")

    text = " | ".join([p for p in parts if p])
    text = text[:4000]
    return text


def upsert_log_embedding_with_service(
    session,
    log_json: dict[str, Any],
    log_id: str,
    rag_text: str,
    embedding: list[float],
) -> int:
    vector_model = os.getenv("VECTOR_MODEL", "text-embedding-3-small")
    result = session.run(
        """
    MATCH (s:Service {name:$service})-[:PRODUCES_LOG]->(l:Log {
      timestamp:$timestamp, level:$level, funcName:$funcName
    })
    WHERE l.message = $message
    SET l.log_id = $log_id,
        l.embedding = $embedding,
        l.vector_model = $vector_model,
        l.rag_text = $rag_text
    RETURN id(l) AS lid
    """,
        service=log_json.get("service"),
        timestamp=log_json.get("timestamp"),
        level=log_json.get("level"),
        funcName=log_json.get("funcName"),
        message=log_json.get("message"),
        log_id=log_id,
        embedding=embedding,
        vector_model=vector_model,
        rag_text=rag_text,
    )
    rec = result.single()
    return rec["lid"] if rec else -1


def upsert_log_embedding_with_trace(
    session,
    log_json: dict[str, Any],
    log_id: str,
    rag_text: str,
    embedding: list[float],
) -> int:
    vector_model = os.getenv("VECTOR_MODEL", "text-embedding-3-small")

    result = session.run(
        """
    MATCH (t:Trace {id:$trace_id})<-[:PART_OF_TRACE]-(l:Log)
    WHERE l.message = $message AND l.funcName = $funcName
    SET l.log_id = $log_id,
        l.embedding = $embedding,
        l.vector_model = $vector_model,
        l.rag_text = $rag_text
    RETURN id(l) AS lid
    """,
        trace_id=log_json.get("trace_id"),
        message=log_json.get("message"),
        funcName=log_json.get("funcName"),
        log_id=log_id,
        embedding=embedding,
        vector_model=vector_model,
        rag_text=rag_text,
    )
    rec = result.single()
    return rec["lid"] if rec else -1


def upsert_log_embedding(
    session,
    log_data: dict[str, Any],
    log_id: str,
    rag_text: str,
    embedding: list[float],
):
    vector_model = os.getenv("VECTOR_MODEL", "text-embedding-3-small")

    session.run(
        """
    MATCH (l:Log {timestamp:$timestamp, funcName:$funcName})
    WHERE l.message = $message
    SET l.log_id = $log_id,
        l.embedding = $embedding,
        l.vector_model = $vector_model,
        l.rag_text = $rag_text
    RETURN id(l) AS lid
    """,
        timestamp=log_data.get("timestamp"),
        funcName=log_data.get("funcName"),
        message=log_data.get("message"),
        log_id=log_id,
        embedding=embedding,
        vector_model=vector_model,
        rag_text=rag_text,
    ).single()
