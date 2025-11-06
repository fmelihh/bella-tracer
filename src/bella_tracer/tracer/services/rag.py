import os
from typing import Any
from bella_tracer.tracer import interfaces


async def knn_logs(query_embedding: list[float], k: int = 10) -> list[dict[str, Any]]:
    neo4j_driver = await interfaces.neo4j.retrieve_neo4j_driver()

    with neo4j_driver.session(database="neo4j") as s:
        rs = s.run(
            """
        CALL db.index.vector.queryNodes('log_embedding_index', $k, $embedding) YIELD node, score
        WITH node, score
        OPTIONAL MATCH (node)-[:PART_OF_TRACE]->(t:Trace)
        OPTIONAL MATCH (node)-[:PRODUCED_ERROR]->(e:Error)
        OPTIONAL MATCH (node)<-[:PRODUCES_LOG]-(svc:Service)
        OPTIONAL MATCH (node)-[:REPORTS_METRIC]->(dm:Metric {type:'duration_ms'})
        OPTIONAL MATCH (node)-[:HAS_EVENT]->(o:Order)
        OPTIONAL MATCH (node)-[:FAILS_TO_CALL]->(dst:Service)
        RETURN id(node) AS log_node_id,
               node.log_id        AS log_id,
               svc.name           AS service,
               node.timestamp     AS ts,
               node.level         AS level,
               node.funcName      AS func,
               node.rag_text      AS context,
               node.message       AS message,
               t.id               AS trace_id,
               e.type             AS error_type,
               e.message          AS error_msg,
               dm.value           AS duration_ms,
               o.id               AS order_id,
               dst.name           AS failed_service,
               score
        ORDER BY score DESC
        LIMIT $k
        """,
            embedding=query_embedding,
            k=k,
        )
        data = [r.data() for r in rs]

    return data


async def trace_timeline(
    trace_id: str, limit_per_trace: int = 25
) -> list[dict[str, Any]]:
    if not trace_id:
        return []

    neo4j_driver = await interfaces.neo4j.retrieve_neo4j_driver()
    with neo4j_driver.session(database="neo4j") as s:
        rs = s.run(
            """
        MATCH (t:Trace {id:$trace_id})<-[:PART_OF_TRACE]-(l:Log)<-[:PRODUCES_LOG]-(svc:Service)
        OPTIONAL MATCH (l)-[:PRODUCED_ERROR]->(e:Error)
        OPTIONAL MATCH (l)-[:FAILS_TO_CALL]->(dst:Service)
        OPTIONAL MATCH (l)-[:REPORTS_METRIC]->(dm:Metric {type:'duration_ms'})
        RETURN svc.name AS service, l.level AS level, l.timestamp AS ts, l.funcName AS func,
               e.type AS error_type, dst.name AS fails_to, dm.value AS duration_ms, l.message AS msg
        ORDER BY ts ASC
        LIMIT $lim
        """,
            trace_id=trace_id,
            lim=limit_per_trace,
        )
        return [r.data() for r in rs]


async def summarize(
    question: str,
    hits: list[dict[str, Any]],
    timelines: dict[str, list[dict[str, Any]]],
) -> str:
    bullets = []

    for i, h in enumerate(hits[:10], 1):
        bullets.append(
            f"{i}. score={round(h['score'], 4)} ts={h.get('ts')} "
            f"service={h.get('service')} level={h.get('level')} "
            f"trace={h.get('trace_id')} func={h.get('func')} "
            f"failed_service={h.get('failed_service')} "
            f"error={h.get('error_type') or ''} "
            f"msg={(h.get('message') or '')[:180].replace('\\n', ' ')}"
        )

    tl_chunks = []
    for t_id, rows in timelines.items():
        chain = " -> ".join(
            f"{r.get('service')}("
            f"{r.get('level')}"
            f"{'⚠' if r.get('error_type') else ''}"
            f"{'⇢' + r.get('fails_to') if r.get('fails_to') else ''}"
            f")"
            for r in rows[:12]
        )
        tl_chunks.append(f"trace={t_id}: {chain}")

    prompt = (
        f"""You are a helpful SRE assistant. Answer in concise.

            Question:
            {question}
            
            Most relevant logs by vector similarity (top 10):
            - """
        + "\n- ".join(bullets)
        + """
            
            Related trace timelines:
            - """
        + "\n- ".join(tl_chunks)
        + """
            
            Task:
            1) Summarize the probable root cause in 2-4 bullet points (cite the trace_id and involved services as evidence).
            2) List the affected component(s) and likely trigger(s).
            3) Propose quick actions (1-2 steps).
            Keep the answer brief.
        """
    )

    openai_client = await interfaces.openai.retrieve_openai_client()
    resp = await openai_client.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return resp.choices[0].message.content


async def retrieve_rag_result(question: str):
    q_emb = await embed_text(text=question)
    hits = await knn_logs(q_emb, k=10)

    traces = {h["trace_id"] for h in hits if h.get("trace_id")}
    timelines = {t_id: await trace_timeline(trace_id=t_id) for t_id in list(traces)[:3]}

    summary = await summarize(question=question, hits=hits, timelines=timelines)

    return {
        "question": question,
        "hits": hits,
        "traces_expanded": list(timelines.keys()),
        "answer": summary,
    }


async def embed_text(text: str) -> list[float]:
    openai_client = await interfaces.openai.retrieve_openai_client()

    vector_model = os.getenv("VECTOR_MODEL", "text-embedding-3-small")
    resp = await openai_client.embeddings.create(model=vector_model, input=text)
    return resp.data[0].embedding
