import logging
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from logging_config import setup_logging, UnifiedLoggingMiddleware, trace_id_var

SERVICE_NAME = "payment-service"
setup_logging(service_name=SERVICE_NAME)
log = logging.getLogger(SERVICE_NAME)
app = FastAPI()
app.add_middleware(middleware_class=UnifiedLoggingMiddleware, service_name=SERVICE_NAME)
http_client = httpx.AsyncClient()


@app.post("/pay")
async def process_payment(request: Request):
    data = await request.json()
    order_id = data.get("order_id")
    log.info(f"Payment request received [Order: {order_id}]")
    trace_id = trace_id_var.get()
    headers = {"X-Trace-ID": trace_id}

    try:
        log.debug("Calling fraud-service...")
        response = await http_client.post(
            "http://localhost:8003/check", headers=headers, json={"order_id": order_id}
        )
        response.raise_for_status()
        if response.json().get("risk_level") == "HIGH":
            log.warning(
                f"Payment rejected for order {order_id} due to high fraud risk."
            )
            raise HTTPException(status_code=400, detail="High fraud risk")

    except httpx.ConnectError:
        error_trace = (
            f"Could not connect to fraud-service. Service appears to be down. [Order: {order_id}]\n"
            f"Traceback (most recent call last):\n"
            f'  File "payment_service.py", line 35, in process_payment\n'
            f"    response = await http_client.post(...)\n"
            f"httpx.ConnectError: [Errno 111] Connection refused"
        )

        log.error(error_trace)
        raise HTTPException(status_code=503, detail="Fraud service error")

    log.info(f"Bank approval received for order {order_id}.")
    return {"status": "Payment successful"}


def run():
    uvicorn.run("payment:app", host="0.0.0.0", port=8002, reload=True)
