from prefect import flow


@flow(name="knowledge_graph_parser")
async def knowledge_graph_parser():
    print("knowledge_graph_parser")
