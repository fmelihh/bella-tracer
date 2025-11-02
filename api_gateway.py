import logging
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from logging_config import setup_logging, UnifiedLoggingMiddleware, trace_id_var

SERVICE_NAME = "api-gateway"
setup_logging(service_name=SERVICE_NAME)
log = logging.getLogger(SERVICE_NAME)
app = FastAPI()
app.add_middleware(middleware_class=UnifiedLoggingMiddleware, service_name=SERVICE_NAME)
http_client = httpx.AsyncClient()


@app.post("/order")
async def create_order_gateway(request: Request):
    auth_header = request.headers.get("Authorization")
    log.debug(f"Authorization Header received: {auth_header}")

    trace_id = trace_id_var.get()
    headers = {"X-Trace-ID": trace_id}

    try:
        response = await http_client.post(
            "http://localhost:8001/order",
            headers=headers,
            json={"user_id": "user-456", "item_count": 3},
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        log.error(
            f"Received {e.response.status_code} from order-service.", exc_info=False
        )
        raise HTTPException(
            status_code=e.response.status_code, detail="Order service error"
        )
    except httpx.RequestError as e:
        log.critical(
            f"Cannot connect to order-service: {e.__class__.__name__}. Service is down!",
            exc_info=True,
        )
        raise HTTPException(
            status_code=503, detail="Order service is currently unavailable"
        )

    log.info("Request successfully forwarded to order-service.")
    return response.json()


def run():
    uvicorn.run("api_gateway:app", host="0.0.0.0", port=8000, reload=True)
