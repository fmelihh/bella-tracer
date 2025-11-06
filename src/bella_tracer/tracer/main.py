import asyncio
from hypercorn.asyncio import Config, serve
from datetime import timedelta

from bella_tracer import tracer

from dotenv import load_dotenv

from prefect.client.schemas.schedules import IntervalSchedule

from bella_tracer.tracer.api import app


load_dotenv()


def api_gateway():
    """Runs the API Gateway service."""
    print("Starting API Gateway...")
    tracer.example_api_setup.step_1_api_gateway.run()


def order():
    """Runs the Order service."""
    print("Starting Order service...")
    tracer.example_api_setup.step_2_order.run()


def payment():
    """Runs the Payment service."""
    print("Starting Payment service...")
    tracer.example_api_setup.step_3_payment.run()


def fraud():
    """Runs the Fraud service."""
    print("Starting Fraud service...")
    tracer.example_api_setup.step_4_fraud.run()


def run_prefect_flows():
    """Runs the Prefect Flows service."""
    print("Starting Prefect Flows service...")
    tracer.workflows.knowledge_graph_parser.serve(
        schedule=IntervalSchedule(interval=timedelta(minutes=2)),
    )


def run_neo4j_migrations():
    """Runs the Neo4J Migration service."""

    asyncio.run(tracer.services.knowledge_graph.ensure_neo4j_indexes())


def run_bella_tracer():
    """Runs the Bella Tracer service."""
    config = Config()
    config.bind = ["0.0.0.0:8004"]
    config.workers = 1
    config.accesslog = "-"

    asyncio.run(serve(app, config))
