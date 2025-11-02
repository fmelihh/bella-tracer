import logging
import httpx
import uvicorn
import random
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from logging_config import setup_logging, UnifiedLoggingMiddleware, trace_id_var

SERVICE_NAME = "order-service"
setup_logging(service_name=SERVICE_NAME)
log = logging.getLogger(__name__)
app = FastAPI()
app.add_middleware(UnifiedLoggingMiddleware)
http_client = httpx.AsyncClient()


async def call_shipping_service(order_id: str, trace_id: str, user_id: str):
    trace_id_var.set(trace_id)
    log.info(f"Dropping message on shipping-queue: Order {order_id} will be shipped.")


@app.post("/order")
async def create_order(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    user_id = data.get("user_id", "unknown_user")
    item_count = data.get("item_count", 0)
    order_id = f"ORD-{random.randint(1000, 9999)}"

    log.info(
        f"New order {order_id} created for user {user_id} with {item_count} items."
    )

    trace_id = trace_id_var.get()
    headers = {"X-Trace-ID": trace_id}

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

    background_tasks.add_task(call_shipping_service, order_id, trace_id, user_id)

    log.info(f"Order {order_id} confirmed successfully.")
    return {"status": "Order received", "order_id": order_id}


def run():
    uvicorn.run(app, host="0.0.0.0", port=8001)
