import click
from datetime import timedelta
from api_gateway import run as api_gateway_run
from order import run as order_run
from payment import run as payment_run
from fraud import run as fraud_run

from src.bella_tracer import workflows

from dotenv import load_dotenv

from prefect.client.schemas.schedules import IntervalSchedule

load_dotenv()


@click.group()
def cli():
    """A CLI to run the Bella Tracer services."""
    pass


@cli.command()
def api_gateway():
    """Runs the API Gateway service."""
    click.echo("Starting API Gateway...")
    api_gateway_run()


@cli.command()
def order():
    """Runs the Order service."""
    click.echo("Starting Order service...")
    order_run()


@cli.command()
def payment():
    """Runs the Payment service."""
    click.echo("Starting Payment service...")
    payment_run()


@cli.command()
def fraud():
    """Runs the Fraud service."""
    click.echo("Starting Fraud service...")
    fraud_run()


@cli.command()
def run_prefect_flows():
    """Runs the Prefect Flows service."""
    click.echo("Starting Prefect Flows service...")
    workflows.knowledge_graph_parser.serve(
        schedule=IntervalSchedule(interval=timedelta(minutes=2)),
    )


if __name__ == "__main__":
    cli()
