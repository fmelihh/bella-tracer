import click
from api_gateway import run as api_gateway_run
from order import run as order_run
from payment import run as payment_run
from fraud import run as fraud_run


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


if __name__ == "__main__":
    cli()
