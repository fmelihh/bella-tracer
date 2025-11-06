from fastapi import FastAPI
from contextlib import asynccontextmanager
from bella_tracer.tracer.api.routers import report
from bella_tracer.tracer.services import knowledge_graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    await knowledge_graph.ensure_neo4j_indexes()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(
    report.report_router,
    prefix="/report",
    tags=["report"],
)
