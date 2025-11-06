import click
import asyncio
from datetime import timedelta

from bella_tracer import tracer

from dotenv import load_dotenv

from prefect.client.schemas.schedules import IntervalSchedule

load_dotenv()


@click.group()
def cli():
    """A CLI to run the Bella Tracer interfaces."""
    pass


@cli.command()
def api_gateway():
    """Runs the API Gateway service."""
    click.echo("Starting API Gateway...")
    tracer.example_api_setup.step_1_api_gateway.run()


@cli.command()
def order():
    """Runs the Order service."""
    click.echo("Starting Order service...")
    tracer.example_api_setup.step_2_order.run()


@cli.command()
def payment():
    """Runs the Payment service."""
    click.echo("Starting Payment service...")
    tracer.example_api_setup.step_3_payment.run()


@cli.command()
def fraud():
    """Runs the Fraud service."""
    click.echo("Starting Fraud service...")
    tracer.example_api_setup.step_4_fraud.run()


@cli.command()
def run_prefect_flows():
    """Runs the Prefect Flows service."""
    click.echo("Starting Prefect Flows service...")
    tracer.workflows.knowledge_graph_parser.serve(
        schedule=IntervalSchedule(interval=timedelta(minutes=2)),
    )


@cli.command()
def run_neo4j_migrations():
    """Runs the Neo4J Migration service."""

    asyncio.run(tracer.services.knowledge_graph.ensure_neo4j_indexes())


if __name__ == "__main__":
    cli()
