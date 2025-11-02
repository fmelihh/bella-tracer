import logging
import uvicorn
import random
import asyncio
from fastapi import FastAPI, Request
from logging_config import setup_logging, UnifiedLoggingMiddleware
from faker import Faker

SERVICE_NAME = "fraud-service"
setup_logging(service_name=SERVICE_NAME)
log = logging.getLogger(__name__)
app = FastAPI()
app.add_middleware(UnifiedLoggingMiddleware)
fake = Faker()


@app.post("/check")
async def check_fraud(request: Request):
    data = await request.json()
    order_id = data.get("order_id")
    user_email = fake.email()  # Sahte bir email

    await asyncio.sleep(random.uniform(0.05, 0.5))
    risk_score = random.uniform(0.1, 100.0)

    decision = "LOW_RISK"
    log_level = log.info
    if risk_score > 90:
        decision = "HIGH_RISK"
        log_level = log.warning

    log_level(
        f"Fraud analysis complete. For order {order_id}, user {user_email} "
        f"risk score was calculated as {risk_score:.2f}. "
        f"Decision: {decision}."
    )

    return {"risk_level": "HIGH" if decision == "HIGH_RISK" else "LOW"}


def run():
    uvicorn.run(app, host="0.0.0.0", port=8003)
