import asyncio
import logging
import httpx
from hypercorn.asyncio import serve
from hypercorn.config import Config

import random
from fastapi import FastAPI, HTTPException, Request
from logging_config import setup_logging, UnifiedLoggingMiddleware, trace_id_var

SERVICE_NAME = "order-service"
setup_logging(service_name=SERVICE_NAME)
log = logging.getLogger(SERVICE_NAME)
app = FastAPI()
app.add_middleware(middleware_class=UnifiedLoggingMiddleware, service_name=SERVICE_NAME)
http_client = httpx.AsyncClient(timeout=900.0)


@app.post("/order")
async def create_order(request: Request):
    data = await request.json()
    user_id = data.get("user_id", "unknown_user")
    item_count = data.get("item_count", 0)
    order_id = f"ORD-{random.randint(1000, 9999)}"

    log.info(
        f"New order {order_id} created for user {user_id} with {item_count} items."
    )

    trace_id = trace_id_var.get()
    headers = {"X-Trace-ID": trace_id}

    await asyncio.sleep(random.randint(0, 15))

    try:
        log.debug("Calling payment-service...")
        payment_data = {"order_id": order_id, "amount": item_count * 100}
        response = await http_client.post(
            "http://localhost:8002/pay", headers=headers, json=payment_data
        )
        response.raise_for_status()
    except Exception:
        log.error(
            f"Payment failed for order {order_id}. Cancelling order.",
            exc_info=True,
        )
        raise HTTPException(status_code=400, detail="Payment failed")

    log.info(f"Order {order_id} confirmed successfully.")
    return {"status": "Order received", "order_id": order_id}


def run():
    config = Config()
    config.bind = [f"0.0.0.0:8001"]
    config.workers = 1
    config.accesslog = "-"  # Enable access logging to stdout.

    asyncio.run(serve(app, config))
