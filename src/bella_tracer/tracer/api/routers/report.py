from fastapi import APIRouter

from bella_tracer.tracer import services


report_router = APIRouter()


@report_router.get("/retrieve-rag-result")
async def retrieve_rag_result(question: str):
    return await services.rag.retrieve_rag_result(question=question)
